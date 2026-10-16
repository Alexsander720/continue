"""Offline tests for GitHub release workflow guard using real temporary Git fixtures.

Tests extract the actual inline guard script from .github/workflows/release.yml
and execute it in temporary Git repositories without network or GitHub dependencies.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "release.yml"


def extract_guard_script(workflow_text: str) -> str:
    """Extract the inline Python guard script from the workflow YAML."""
    match = re.search(
        r"name:\s*Verify release tag and commit.*?run:\s*\|\s*\n\s*python -\s*<<'EOF'\n(.*?)\n\s*EOF",
        workflow_text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Could not find inline Python guard script in release.yml")
    import textwrap
    return textwrap.dedent(match.group(1))


class DraftReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not WORKFLOW_PATH.is_file():
            raise unittest.SkipTest(f"Missing {WORKFLOW_PATH}")
        cls.workflow_content = WORKFLOW_PATH.read_text(encoding="utf-8")

    def _extract_guard(self) -> str:
        return extract_guard_script(self.workflow_content)

    def _create_git_fixture(self, directory: Path, pkg_version: str = "0.1.2") -> Path:
        """Create a real temporary Git fixture with initialized repo and plugin/package.json."""
        def git(*args):
            res = subprocess.run(["git", *args], cwd=directory, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Git failed ({' '.join(args)}): {res.stderr}")
            return res.stdout.strip()

        git("init", "-b", "main")
        git("config", "user.email", "release-test@example.com")
        git("config", "user.name", "Release Test")
        git("config", "commit.gpgsign", "false")
        git("config", "tag.gpgsign", "false")

        pkg_dir = directory / "plugin"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "package.json").write_text(
            json.dumps({"name": "continue", "version": pkg_version}, indent=2),
            encoding="utf-8",
        )

        git("add", ".")
        git("commit", "-m", "Initial commit")
        return directory

    def _run_guard(self, repo_dir: Path, guard_script: str, tag: str) -> tuple[int, str, str, dict[str, str]]:
        output_file = repo_dir / "github_output.txt"
        env = {
            **os.environ,
            "CONTINUE_TAG": tag,
            "GITHUB_OUTPUT": str(output_file),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        res = subprocess.run(
            [sys.executable, "-c", guard_script],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        parsed_outputs = {}
        if output_file.is_file():
            for line in output_file.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    parsed_outputs[k.strip()] = v.strip()
        return res.returncode, res.stdout, res.stderr, parsed_outputs

    def test_workflow_has_explicit_tag_checkout_and_head_guard(self):
        """Workflow must checkout refs/tags/<input> and check HEAD before draft creation."""
        self.assertIn(
            "ref: refs/tags/${{ github.event.inputs.tag }}",
            self.workflow_content,
            "Workflow must explicitly checkout refs/tags/<tag>",
        )
        self.assertIn(
            "fetch-depth: 0",
            self.workflow_content,
            "Workflow checkout must fetch history/tags",
        )
        self.assertIn(
            "--verify-tag",
            self.workflow_content,
            "Workflow must retain --verify-tag",
        )
        self.assertIn(
            "--draft",
            self.workflow_content,
            "Workflow must retain --draft",
        )
        self.assertIn(
            'if [ "$current_head" != "$VERIFIED_COMMIT" ]',
            self.workflow_content,
            "Workflow must re-check HEAD against verified commit before draft creation",
        )

    def test_matching_lightweight_tag_passes(self):
        """Lightweight tag matching HEAD commit and package.json passes guard."""
        guard_script = self._extract_guard()
        with tempfile.TemporaryDirectory(prefix="test-guard-light-") as tmp:
            repo_dir = Path(tmp)
            self._create_git_fixture(repo_dir, pkg_version="0.1.2")
            subprocess.run(["git", "tag", "v0.1.2"], cwd=repo_dir, check=True)

            code, out, err, outputs = self._run_guard(repo_dir, guard_script, "v0.1.2")
            self.assertEqual(code, 0, f"Guard failed: {err}")
            self.assertEqual(outputs.get("tag"), "v0.1.2")
            self.assertEqual(outputs.get("version"), "0.1.2")
            head_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True, check=True
            ).stdout.strip()
            self.assertEqual(outputs.get("commit"), head_commit)

    def test_matching_annotated_tag_passes(self):
        """Annotated tag (which peels to target commit) passes guard."""
        guard_script = self._extract_guard()
        with tempfile.TemporaryDirectory(prefix="test-guard-annotated-") as tmp:
            repo_dir = Path(tmp)
            self._create_git_fixture(repo_dir, pkg_version="0.1.2")
            subprocess.run(
                ["git", "tag", "-a", "v0.1.2", "-m", "Release candidate 0.1.2"],
                cwd=repo_dir,
                check=True,
            )

            code, out, err, outputs = self._run_guard(repo_dir, guard_script, "v0.1.2")
            self.assertEqual(code, 0, f"Guard failed: {err}")
            self.assertEqual(outputs.get("tag"), "v0.1.2")
            self.assertEqual(outputs.get("version"), "0.1.2")
            head_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True, check=True
            ).stdout.strip()
            self.assertEqual(outputs.get("commit"), head_commit)

    def test_wrong_head_rejects(self):
        """Guard must fail if HEAD has moved past the tag commit."""
        guard_script = self._extract_guard()
        with tempfile.TemporaryDirectory(prefix="test-guard-wronghead-") as tmp:
            repo_dir = Path(tmp)
            self._create_git_fixture(repo_dir, pkg_version="0.1.2")
            subprocess.run(["git", "tag", "v0.1.2"], cwd=repo_dir, check=True)

            # Advance HEAD with another commit
            (repo_dir / "extra.txt").write_text("extra", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
            subprocess.run(["git", "commit", "-m", "advance"], cwd=repo_dir, check=True)

            code, out, err, outputs = self._run_guard(repo_dir, guard_script, "v0.1.2")
            self.assertNotEqual(code, 0)
            self.assertTrue(
                "does not match tag commit" in err or "does not match tag commit" in out,
                f"Expected mismatch message, got err={err}, out={out}",
            )

    def test_package_version_mismatch_rejects(self):
        """Guard must fail if plugin/package.json version does not match tag version."""
        guard_script = self._extract_guard()
        with tempfile.TemporaryDirectory(prefix="test-guard-pkgmismatch-") as tmp:
            repo_dir = Path(tmp)
            self._create_git_fixture(repo_dir, pkg_version="0.1.1")
            subprocess.run(["git", "tag", "v0.1.2"], cwd=repo_dir, check=True)

            code, out, err, outputs = self._run_guard(repo_dir, guard_script, "v0.1.2")
            self.assertNotEqual(code, 0)
            self.assertTrue(
                "version" in err.lower() or "version" in out.lower(),
                f"Expected version mismatch message, got err={err}, out={out}",
            )

    def test_invalid_tag_input_rejects(self):
        """Guard must reject malformed, non-semver, or branch-like tag names."""
        guard_script = self._extract_guard()
        with tempfile.TemporaryDirectory(prefix="test-guard-invalid-") as tmp:
            repo_dir = Path(tmp)
            self._create_git_fixture(repo_dir, pkg_version="0.1.2")

            invalid_inputs = ["0.1.2", "latest", "v0.1", "v1.2.3.4", "refs/heads/main", "v0.1.2-alpha"]
            for bad_tag in invalid_inputs:
                code, out, err, outputs = self._run_guard(repo_dir, guard_script, bad_tag)
                self.assertNotEqual(code, 0, f"Expected {bad_tag!r} to be rejected")


if __name__ == "__main__":
    unittest.main()
