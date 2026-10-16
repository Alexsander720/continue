"""Installer integration checks: no real task, process, registry or Steam calls.

Every script invocation uses an explicit profile marker below pytest's tmp_path.
PowerShell's fixture wrappers store actions in that profile instead of performing
OS operations. The fake Python files are intentionally not runnable.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import hashlib
import zipfile
import sys

import pytest


PC = (Path(__file__).resolve().parents[2] / 'pc')
sys.path.insert(0,str(PC))
PS = shutil.which("powershell.exe") or shutil.which("pwsh")
pytestmark = pytest.mark.skipif(not PS, reason="PowerShell is required")


@pytest.fixture
def layout(tmp_path):
    profile = tmp_path / "profile with spaces"
    steam = profile / "fake Steam"
    steam.mkdir(parents=True)
    (steam / "steam.exe").write_bytes(b"fake Steam, never executed")
    (profile / ".continue-fixture-profile").write_text(
        json.dumps({"fixture": True, "profile": str(profile), "steam": str(steam)}),
        encoding="utf-8",
    )
    fake_python = profile / "fake Python"
    fake_python.mkdir()
    for name in ("python.exe", "pythonw.exe"):
        (fake_python / name).write_bytes(b"fixture, never executed")
    package = tmp_path / "package"
    (package / "pc").mkdir(parents=True)
    (package / "plugin" / "GameHubDeck" / "dist").mkdir(parents=True)
    (package / "RELEASE.json").write_text(
        json.dumps({"version": "0.1.0", "platform": "windows", "channel": "public"}),
        encoding="utf-8",
    )
    (package / "pc" / "gamehub_bp.py").write_text(
        "raise SystemExit('fixture must not execute this')\n", encoding="utf-8"
    )
    (package / "plugin" / "GameHubDeck" / "dist" / "index.js").write_text(
        "fixture\n", encoding="utf-8"
    )
    for name in ("setup.cmd", "install.ps1", "uninstall.ps1", "status.ps1", "windows_common.ps1", "python_runtime.json", "public_bootstrap.py", "recover-install.ps1", "public_update.py"):
        if (PC / name).exists():
            shutil.copy2(PC / name, package / "pc" / name)
    return dict(profile=profile, steam=steam, python=fake_python / "pythonw.exe", package=package,
                root=profile / "LocalAppData" / "Continue")


def run_script(layout, name="install.ps1", *args, installed=False):
    script = layout["root"] / "app" / "pc" / name if installed else layout["package"] / "pc" / name
    cmd = [PS, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script),
           "-FixtureProfile", str(layout["profile"]), "-FixtureSteam", str(layout["steam"]),
           "-FixturePython", str(layout["python"]), "-NonInteractive", *args]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def common_snippet(layout, expression):
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"
    code = ". " + quote(PC / "windows_common.ps1") + "; "
    code += "$ctx=Initialize-ContinueContext " + " ".join(
        quote(layout[k]) for k in ("profile", "steam", "python")
    ) + "; " + expression
    return subprocess.run([PS, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", code],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)


def install(layout):
    result = run_script(layout, "install.ps1", "-AcceptDebugPort")
    assert result.returncode == 0, result.stdout + result.stderr
    return read_json(layout["root"] / "install.json")


@pytest.mark.parametrize('recover_with', ['install', 'repair', 'uninstall', 'RemoveData', 'bootstrap'])
@pytest.mark.parametrize('legacy', [False, True])
def test_first_install_stage_to_app_recovery(layout, recover_with, legacy):
    script = layout['package'] / 'pc/install.ps1'
    original = script.read_text(encoding='utf-8')
    anchor = 'Move-Item -LiteralPath $stage -Destination $context.App'
    assert original.count(anchor) == 1
    script.write_text(original.replace(anchor, anchor + '\n        [Environment]::Exit(86)'), encoding='utf-8')
    result = run_script(layout, 'install.ps1', '-AcceptDebugPort')
    assert result.returncode == 86, result.stdout + result.stderr
    assert (layout['root'] / 'app').is_dir()
    assert not (layout['root'] / 'install.json').exists()
    if legacy:
        journal = layout['root'] / 'install-transaction.json'
        data = read_json(journal)
        data.pop('next'); data.pop('flag_stage', None)
        journal.write_text(json.dumps(data), encoding='utf-8')
    script.write_text(original, encoding='utf-8')
    if recover_with in ('install', 'repair'):
        result = run_script(layout, 'install.ps1', '-AcceptDebugPort')
        assert result.returncode == 0, result.stdout + result.stderr
        assert (layout['root'] / 'install.json').is_file()
    elif recover_with == 'bootstrap':
        result = common_snippet(layout, '$lock=Enter-ContinueLifecycleLock; try { Restore-ContinueInstallTransaction -FromBootstrap } finally { Exit-ContinueLifecycleLock $lock }')
        assert result.returncode == 0, result.stdout + result.stderr
        assert not (layout['root'] / 'app').exists()
    else:
        result = run_script(layout, 'uninstall.ps1', '-KeepData' if recover_with == 'uninstall' else '-RemoveData')
        assert result.returncode == 0, result.stdout + result.stderr
        assert not (layout['root'] / 'app').exists()
    assert not (layout['root'] / 'install-transaction.json').exists()
    assert not list(layout['root'].glob('app-stage-*'))
    assert not list(layout['root'].glob('app-backup-*'))


@pytest.mark.parametrize('flag_state', ['owned', 'preexisting', 'changed', 'replaced_empty', 'shared'])
def test_first_install_flag_creation_crash_recovery_then_purge(layout, flag_state):
    flag = layout['steam'] / '.cef-enable-remote-debugging'
    if flag_state == 'preexisting':
        flag.write_bytes(b'')
    script = layout['package'] / 'pc/install.ps1'
    original = script.read_text(encoding='utf-8')
    anchor = '        $ownedFlag = '
    assert original.count(anchor) == 1
    script.write_text(original.replace(anchor, '        [Environment]::Exit(85)\n' + anchor), encoding='utf-8')
    result = run_script(layout, 'install.ps1', '-AcceptDebugPort')
    assert result.returncode == 85, result.stdout + result.stderr
    assert flag.is_file() and not (layout['root'] / 'install.json').exists()
    if flag_state == 'changed':
        flag.write_bytes(b'changed by another consumer')
    elif flag_state == 'replaced_empty':
        flag.unlink(); flag.write_bytes(b'')
        os.utime(flag, (1000000000, 1000000000))
    elif flag_state == 'shared':
        owner = layout['profile'] / 'owner/gamehub_bp.py'
        owner.parent.mkdir(); owner.write_text('fixture only')
        (layout['profile'] / 'fixture_state.json').write_text(json.dumps({
            'task': None, 'operations': [], 'gamehub_task': {'name': 'GameHubBigPicture', 'state': 'Running',
            'execute': str(layout['python']), 'arguments': f'"{owner}" run'}}), encoding='utf-8')
    script.write_text(original, encoding='utf-8')
    result = common_snippet(layout, '$lock=Enter-ContinueLifecycleLock; try { Restore-ContinueInstallTransaction } finally { Exit-ContinueLifecycleLock $lock }')
    assert result.returncode == 0, result.stdout + result.stderr
    assert flag.exists() is (flag_state != 'owned')
    install(layout)
    result = run_script(layout, 'uninstall.ps1', '-RemoveData')
    assert result.returncode == 0, result.stdout + result.stderr
    assert flag.exists() is (flag_state != 'owned')


@pytest.mark.parametrize('operation', ['install.ps1', 'uninstall.ps1'])
@pytest.mark.parametrize('tamper', ['invalid_stage', 'foreign_task'])
def test_first_install_recovery_refuses_invalid_journal_or_foreign_task(layout, operation, tamper):
    script = layout['package'] / 'pc/install.ps1'
    original = script.read_text(encoding='utf-8')
    anchor = 'Move-Item -LiteralPath $stage -Destination $context.App'
    script.write_text(original.replace(anchor, anchor + '\n        [Environment]::Exit(86)'), encoding='utf-8')
    assert run_script(layout, 'install.ps1', '-AcceptDebugPort').returncode == 86
    script.write_text(original, encoding='utf-8')
    journal = layout['root'] / 'install-transaction.json'
    if tamper == 'invalid_stage':
        data = read_json(journal); data['stage'] = '../foreign'
        journal.write_text(json.dumps(data), encoding='utf-8')
    else:
        (layout['profile'] / 'fixture_state.json').write_text(json.dumps({
            'task': {'name': 'ContinueBigPicture', 'execute': 'foreign.exe', 'arguments': 'foreign'},
            'operations': []}), encoding='utf-8')
    before = journal.read_bytes()
    app_before = (layout['root'] / 'app/pc/gamehub_bp.py').read_bytes()
    result = run_script(layout, operation, '-AcceptDebugPort' if operation == 'install.ps1' else '-RemoveData')
    assert result.returncode == 1
    assert journal.read_bytes() == before
    assert (layout['root'] / 'app/pc/gamehub_bp.py').read_bytes() == app_before


@pytest.mark.parametrize('boundary', ['before_move', 'concurrent_flag'])
def test_debug_flag_intent_handles_crash_and_concurrent_creation(layout, boundary):
    script = layout['package'] / 'pc/install.ps1'
    original = script.read_text(encoding='utf-8')
    anchor = '            try { [IO.File]::Move($candidate, $flag); $flagCreatedNow = $true }'
    assert original.count(anchor) == 1
    injection = ('            [Environment]::Exit(84)\n' if boundary == 'before_move'
                 else '            [IO.File]::WriteAllBytes($flag, [byte[]]@())\n')
    script.write_text(original.replace(anchor, injection + anchor), encoding='utf-8')
    result = run_script(layout, 'install.ps1', '-AcceptDebugPort')
    assert result.returncode == (84 if boundary == 'before_move' else 0), result.stdout + result.stderr
    script.write_text(original, encoding='utf-8')
    if boundary == 'before_move':
        result = common_snippet(layout, '$lock=Enter-ContinueLifecycleLock; try { Restore-ContinueInstallTransaction } finally { Exit-ContinueLifecycleLock $lock }')
        assert result.returncode == 0, result.stdout + result.stderr
        install(layout)
    else:
        assert not read_json(layout['root'] / 'install.json')['debug_flag_created']
    assert not list(layout['steam'].glob('.continue-debug-*.tmp'))
    result = run_script(layout, 'uninstall.ps1', '-RemoveData')
    assert result.returncode == 0, result.stdout + result.stderr
    assert (layout['steam'] / '.cef-enable-remote-debugging').exists() is (boundary == 'concurrent_flag')


@pytest.mark.parametrize('failure', ['abrupt', 'registration'])
def test_repair_recreated_flag_rolls_back_its_new_identity(layout, failure):
    previous = install(layout)
    flag = layout['steam'] / '.cef-enable-remote-debugging'
    flag.unlink()
    script = layout['package'] / 'pc/install.ps1'
    original = script.read_text(encoding='utf-8')
    if failure == 'abrupt':
        anchor = '        $ownedFlag = '
        script.write_text(original.replace(anchor, '        [Environment]::Exit(83)\n' + anchor), encoding='utf-8')
    else:
        state_path = layout['profile'] / 'fixture_state.json'
        state = read_json(state_path); state['fail_register'] = True
        state_path.write_text(json.dumps(state), encoding='utf-8')
    result = run_script(layout, 'install.ps1', '-AcceptDebugPort')
    assert result.returncode == (83 if failure == 'abrupt' else 1), result.stdout + result.stderr
    script.write_text(original, encoding='utf-8')
    if failure == 'abrupt':
        result = common_snippet(layout, '$lock=Enter-ContinueLifecycleLock; try { Restore-ContinueInstallTransaction } finally { Exit-ContinueLifecycleLock $lock }')
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        state = read_json(state_path); state['fail_register'] = False
        state_path.write_text(json.dumps(state), encoding='utf-8')
    assert read_json(layout['root'] / 'install.json')['install_id'] == previous['install_id']
    assert not flag.exists(), 'rollback must not leave a newly created flag with the previous receipt'
    install(layout)
    result = run_script(layout, 'uninstall.ps1', '-RemoveData')
    assert result.returncode == 0, result.stdout + result.stderr
    assert not flag.exists()


@pytest.mark.parametrize('recover_with',['install','uninstall','bootstrap'])
def test_abrupt_exit_after_backup_recovers_without_orphans(layout,recover_with):
    install(layout)
    original=(layout['package']/'pc/install.ps1').read_text(encoding='utf-8')
    crash=original.replace('Move-Item -LiteralPath $context.App -Destination $backup',
                           'Move-Item -LiteralPath $context.App -Destination $backup\n            [Environment]::Exit(88)')
    (layout['package']/'pc/install.ps1').write_text(crash,encoding='utf-8')
    result=run_script(layout,'install.ps1','-AcceptDebugPort')
    assert result.returncode==88,result.stdout+result.stderr
    assert not (layout['root']/'app').exists()
    assert (layout['root']/'install-transaction.json').exists()
    (layout['package']/'pc/install.ps1').write_text(original,encoding='utf-8')
    if recover_with=='install':install(layout)
    elif recover_with=='uninstall':
        result=run_script(layout,'uninstall.ps1','-RemoveData')
        assert result.returncode==0,result.stdout+result.stderr
    else:
        before=len(read_json(layout['profile']/'fixture_state.json')['operations'])
        result=common_snippet(layout,'$lock=Enter-ContinueLifecycleLock; try { Restore-ContinueInstallTransaction -FromBootstrap } finally { Exit-ContinueLifecycleLock $lock }')
        assert result.returncode==0,result.stdout+result.stderr
        assert (layout['root']/'app/pc/gamehub_bp.py').is_file()
        operations=read_json(layout['profile']/'fixture_state.json')['operations'][before:]
        assert not any(op['operation'] in ('stop_task','stop_service') for op in operations)
    assert not list(layout['root'].glob('app-stage-*'))
    assert not list(layout['root'].glob('app-backup-*'))
    assert not (layout['root']/'install-transaction.json').exists()


@pytest.mark.parametrize('anchor',['$manifestWritten = $true','Register-ContinueTask ([pscustomobject]$manifest)'])
def test_abrupt_exit_after_new_manifest_or_task_restores_previous_release(layout,anchor):
    install(layout)
    script=layout['package']/'pc/install.ps1'
    original=script.read_text(encoding='utf-8')
    script.write_text(original.replace(anchor,anchor+'\n        [Environment]::Exit(87)',1),encoding='utf-8')
    marker=layout['package']/'RELEASE.json'
    data=read_json(marker);data['version']='0.1.2';marker.write_text(json.dumps(data))
    result=run_script(layout,'install.ps1','-AcceptDebugPort')
    assert result.returncode==87,result.stdout+result.stderr
    assert read_json(layout['root']/'install.json')['version']=='0.1.2'
    result=common_snippet(layout,'$lock=Enter-ContinueLifecycleLock; try { Restore-ContinueInstallTransaction } finally { Exit-ContinueLifecycleLock $lock }')
    assert result.returncode==0,result.stdout+result.stderr
    assert read_json(layout['root']/'install.json')['version']=='0.1.0'
    assert not list(layout['root'].glob('app-backup-*'))


def test_real_stable_launcher_recovers_missing_app_then_runs_restored_entry(layout):
    (layout['package']/'pc/gamehub_bp.py').write_text(
        "from pathlib import Path\n(Path(__file__).resolve().parents[2]/'fixture-started.txt').write_text('restored')\n",encoding='utf-8')
    install(layout)
    script=layout['package']/'pc/install.ps1'
    original=script.read_text(encoding='utf-8')
    script.write_text(original.replace('Move-Item -LiteralPath $context.App -Destination $backup',
        'Move-Item -LiteralPath $context.App -Destination $backup\n            [Environment]::Exit(88)'),encoding='utf-8')
    assert run_script(layout,'install.ps1','-AcceptDebugPort').returncode==88
    assert not (layout['root']/'app').exists()
    # Only the profile-discovery adapter is replaced. Production bootstrap,
    # journal recovery, lock, file swap and runpy execute as real processes.
    def quote(path):return "'"+str(path).replace("'","''")+"'"
    adapter=". (Join-Path $PSScriptRoot 'windows_common.ps1')\n"
    adapter+="$ctx=Initialize-ContinueContext "+' '.join(quote(layout[k]) for k in ('profile','steam','python'))+"\n"
    adapter+="$lock=Enter-ContinueLifecycleLock; try { Restore-ContinueInstallTransaction -FromBootstrap } finally { Exit-ContinueLifecycleLock $lock }\n"
    (layout['root']/'recover-install.ps1').write_text(adapter,encoding='utf-8')
    result=subprocess.run([sys.executable,str(layout['root']/'bootstrap.py'),'run'],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    assert (layout['root']/'fixture-started.txt').read_text()=='restored'
    assert not (layout['root']/'install-transaction.json').exists()
    assert not list(layout['root'].glob('app-backup-*'))


def test_install_requires_explicit_debug_consent_without_side_effects(layout):
    result = run_script(layout)
    assert result.returncode != 0
    assert "consent" in (result.stdout + result.stderr).lower()
    assert not (layout["steam"] / ".cef-enable-remote-debugging").exists()
    assert not (layout["root"] / "app").exists()


def test_install_records_owned_flag_task_and_pythonw_paths(layout):
    manifest = install(layout)
    assert manifest["version"] == "0.1.0"
    assert Path(manifest["app"]) == layout["root"] / "app"
    assert Path(manifest["pythonw"]) == layout["python"]
    assert manifest["debug_flag_created"] is True
    assert manifest["task_created"] is True
    assert (layout["steam"] / ".cef-enable-remote-debugging").read_bytes() == b""
    task = read_json(layout["profile"] / "fixture_state.json")["task"]
    assert task["name"] == "ContinueBigPicture"
    assert task["multiple_instances"] == "IgnoreNew"
    assert task["interval_minutes"] == 10
    assert task["execute"] == str(layout["python"])
    assert task["arguments"] == f'"{layout["root"] / "bootstrap.py"}" run'
    for subdir in ("data", "logs"):
        assert (layout["root"] / subdir).is_dir()
    assert (layout["root"] / "settings.json").exists()


def test_repeat_install_repairs_files_and_preserves_flag_ownership_settings_and_data(layout):
    original = install(layout)
    (layout["root"] / "app" / "plugin" / "GameHubDeck" / "dist" / "index.js").unlink()
    (layout["root"] / "settings.json").write_text('{"lang":"uk"}\n', encoding="utf-8")
    (layout["root"] / "data" / "saved.txt").write_text("keep\n", encoding="utf-8")
    updated = install(layout)
    assert updated["debug_flag_created"] is True
    assert updated["install_id"] == original["install_id"]
    assert (layout["root"] / "app" / "plugin" / "GameHubDeck" / "dist" / "index.js").exists()
    assert read_json(layout["root"] / "settings.json")["lang"] == "uk"
    assert (layout["root"] / "data" / "saved.txt").read_text() == "keep\n"
    actions = read_json(layout["profile"] / "fixture_state.json")["operations"]
    assert any(a["operation"] == "stop_service" for a in actions)
    assert all(a.get("task_name", "ContinueBigPicture") == "ContinueBigPicture" for a in actions)


@pytest.mark.parametrize("flag_preexists", [False, True])
def test_uninstall_restores_owned_flag_and_preserves_preexisting_flag(layout, flag_preexists):
    flag = layout["steam"] / ".cef-enable-remote-debugging"
    if flag_preexists:
        flag.write_text("original\n", encoding="utf-8")
    manifest = install(layout)
    assert manifest["debug_flag_created"] is (not flag_preexists)
    result = run_script(layout, "uninstall.ps1", "-RemoveData", installed=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (layout["root"] / "app").exists()
    assert not (layout["root"] / "data").exists()
    assert flag.exists() is flag_preexists
    if flag_preexists:
        assert flag.read_text() == "original\n"
    state = read_json(layout["profile"] / "fixture_state.json")
    assert state["task"] is None
    assert "restart Steam" in result.stdout


def test_uninstall_default_removes_cache_and_size_is_reported(layout):
    install(layout)
    (layout["root"] / "data" / "video.bin").write_bytes(b"x" * 1234)
    (layout["root"] / "downloads").mkdir()
    (layout["root"] / "downloads" / "continue-pc-0.2.0.zip").write_bytes(b"cached update")
    for name in ("update-helper.py", "update-result.json", "service_ready.json",
                 "injected.json", "service.lock", "update.lock", "update.json"):
        (layout["root"] / name).write_text("fixture\n", encoding="utf-8")
    result = run_script(layout, "uninstall.ps1", installed=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1234" in result.stdout
    assert not (layout["root"] / "data").exists()
    assert not (layout["root"] / "downloads").exists()
    assert not any((layout["root"] / name).exists() for name in (
        "update-helper.py", "update-result.json", "service_ready.json",
        "injected.json", "service.lock", "update.lock", "update.json"))


def test_uninstall_can_keep_settings_and_cache(layout):
    install(layout)
    (layout["root"] / "downloads").mkdir()
    (layout["root"] / "downloads" / "continue-pc-0.2.0.zip").write_bytes(b"cached update")
    (layout["root"] / "update-helper.py").write_text("fixture\n", encoding="utf-8")
    result = run_script(layout, "uninstall.ps1", "-KeepData", installed=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (layout["root"] / "data").is_dir()
    assert (layout["root"] / "settings.json").exists()
    assert (layout["root"] / "downloads").exists()
    assert not (layout["root"] / "update-helper.py").exists()
    assert not (layout["root"] / "app").exists()


def test_fixture_guard_rejects_unmarked_profile(layout):
    (layout["profile"] / ".continue-fixture-profile").unlink()
    result = run_script(layout, "install.ps1", "-AcceptDebugPort")
    assert result.returncode != 0
    assert "fixture" in (result.stdout + result.stderr).lower()
    assert not (layout["steam"] / ".cef-enable-remote-debugging").exists()


def test_fixture_guard_rejects_steam_outside_profile(layout, tmp_path):
    other = tmp_path / "not fixture Steam"
    other.mkdir()
    (other / "steam.exe").write_bytes(b"not real")
    layout["steam"] = other
    result = run_script(layout, "install.ps1", "-AcceptDebugPort")
    assert result.returncode != 0
    assert not (other / ".cef-enable-remote-debugging").exists()


def test_owner_source_without_release_marker_is_rejected(layout):
    (layout["package"] / "RELEASE.json").unlink()
    result = run_script(layout, "install.ps1", "-AcceptDebugPort")
    assert result.returncode != 0
    assert "RELEASE.json" in (result.stdout + result.stderr)
    assert not (layout["steam"] / ".cef-enable-remote-debugging").exists()


@pytest.mark.parametrize("patch", [
    {"channel": "development"},
    {"platform": "linux"},
    {"version": "0.1"},
])
def test_installer_rejects_non_public_or_non_windows_release(layout, patch):
    marker = read_json(layout["package"] / "RELEASE.json")
    marker.update(patch)
    (layout["package"] / "RELEASE.json").write_text(json.dumps(marker), encoding="utf-8")
    result = run_script(layout, "install.ps1", "-AcceptDebugPort")
    assert result.returncode != 0
    assert "public PC package" in (result.stdout + result.stderr)
    assert not (layout["steam"] / ".cef-enable-remote-debugging").exists()
    assert not (layout["root"] / "app").exists()


def test_installer_rejects_directory_at_debug_flag_path(layout):
    flag = layout["steam"] / ".cef-enable-remote-debugging"
    flag.mkdir()
    result = run_script(layout, "install.ps1", "-AcceptDebugPort")
    assert result.returncode != 0
    assert "not a file" in (result.stdout + result.stderr)
    assert flag.is_dir()
    assert not (layout["root"] / "app").exists()


def test_foreign_continue_task_is_not_overwritten_or_stopped(layout):
    (layout["profile"] / "fixture_state.json").write_text(json.dumps({
        "task": {"name": "ContinueBigPicture", "execute": "foreign.exe", "arguments": "foreign"},
        "operations": [], "steam_running": False, "cdp": "closed",
    }), encoding="utf-8")
    result = run_script(layout, "install.ps1", "-AcceptDebugPort")
    assert result.returncode != 0
    assert "another" in (result.stdout + result.stderr).lower()
    state = read_json(layout["profile"] / "fixture_state.json")
    assert state["task"]["execute"] == "foreign.exe"
    assert not any(a["operation"] == "stop_task" for a in state["operations"])
    assert not (layout["steam"] / ".cef-enable-remote-debugging").exists()


def test_status_reports_no_steam_and_does_not_contact_owner_ports(layout):
    install(layout)
    result = run_script(layout, "status.ps1", "-Json", installed=True)
    assert result.returncode == 0, result.stdout + result.stderr
    status = json.loads(result.stdout)
    assert status["version"] == "0.1.0"
    assert status["cdp"] == "closed"
    assert status["cache_bytes"] == 0
    assert "Steam is not running" in status["hint"]
    state = read_json(layout["profile"] / "fixture_state.json")
    assert not any(a["operation"] in {"network", "restart_steam"} for a in state["operations"])


@pytest.mark.parametrize("cdp,steam_running,hint", [
    ("closed", True, "restart Steam"),
    ("other", True, "another program"),
    ("steam", True, "Big Picture"),
])
def test_status_hints_for_steam_debug_port(layout, cdp, steam_running, hint):
    install(layout)
    state_path = layout["profile"] / "fixture_state.json"
    state = read_json(state_path)
    state.update(cdp=cdp, steam_running=steam_running)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    result = run_script(layout, "status.ps1", "-Json", installed=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert hint in json.loads(result.stdout)["hint"]


def test_installer_rejects_tampered_manifest_app_path_before_delete(layout, tmp_path):
    install(layout)
    outside = tmp_path / "must survive"
    outside.mkdir()
    protected = outside / "keep.txt"
    protected.write_text("keep\n", encoding="utf-8")
    path = layout["root"] / "install.json"
    manifest = read_json(path)
    manifest["app"] = str(outside)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    result = run_script(layout, "uninstall.ps1", "-RemoveData", installed=True)
    assert result.returncode != 0
    assert protected.read_text() == "keep\n"
    assert (layout["root"] / "app").exists()


def test_setup_uses_own_execution_policy_no_admin_and_lf_is_accepted():
    setup = PC / "setup.cmd"
    assert setup.exists(), "new double-click setup entrypoint is missing"
    text = setup.read_text(encoding="utf-8")
    assert "-ExecutionPolicy Bypass" in text
    assert "%~dp0install.ps1" in text
    assert "RunAs" not in text
    assert b"\r\n" not in setup.read_bytes()


def test_pinned_python_runtime_has_verified_official_hashes():
    runtime = PC / "python_runtime.json"
    assert runtime.exists(), "pinned Python runtime metadata is missing"
    data = read_json(runtime)
    assert data["version"] == "3.14.8"
    assert data["architectures"]["amd64"]["sha256"] == "a93abe456ab01bd96d7a085b3cdb6566b3063f4241360d114142fbdb07f0a310"
    assert data["architectures"]["arm64"]["sha256"] == "155be84ccb57c6331cf0e39001c78a1dfac3be62f403f3ff5f2e29b80dda7ebe"
    for artifact in data["architectures"].values():
        assert artifact["url"].startswith("https://www.python.org/ftp/python/3.14.8/")


def test_sha256_failure_cannot_use_downloaded_archive(layout):
    layout["root"].mkdir(parents=True)
    archive = layout["root"] / "runtime.zip"
    archive.write_bytes(b"untrusted runtime")
    result = common_snippet(layout, f"Assert-ContinueRuntimeHash '{archive}' ('0' * 64)")
    assert result.returncode != 0
    assert "SHA-256" in (result.stdout + result.stderr)
    result = common_snippet(layout, f"Assert-ContinueRuntimeHash '{archive}' '{hashlib.sha256(archive.read_bytes()).hexdigest()}'")
    assert result.returncode == 0, result.stdout + result.stderr


def test_assert_runtime_hash_fixtures_with_and_without_filehash(layout):
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"
    layout["root"].mkdir(parents=True)
    archive = layout["root"] / "runtime.zip"
    archive.write_bytes(b"fixture runtime archive body")
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    upper = sha.upper()
    mismatch = hashlib.sha256(b"tampered runtime archive body").hexdigest()
    block_hash = "function Get-FileHash { throw 'CommandNotFoundException: Get-FileHash' }"

    code = ". " + quote(PC / "windows_common.ps1") + "; " + block_hash + "; "
    code += "if (-not (Assert-ContinueRuntimeHash '" + str(archive) + "' '" + sha + "')) { throw 'valid hash rejected' }"
    result = subprocess.run([PS, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", code],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr

    code = ". " + quote(PC / "windows_common.ps1") + "; " + block_hash + "; "
    code += "if (-not (Assert-ContinueRuntimeHash '" + str(archive) + "' '" + upper + "')) { throw 'uppercase hash rejected' }"
    result = subprocess.run([PS, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", code],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr

    code = ". " + quote(PC / "windows_common.ps1") + "; " + block_hash + "; "
    code += "Assert-ContinueRuntimeHash '" + str(archive) + "' '" + mismatch + "'"
    result = subprocess.run([PS, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", code],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    assert result.returncode != 0
    assert "SHA-256" in (result.stdout + result.stderr)
    assert "will not be used" in (result.stdout + result.stderr)


@pytest.mark.parametrize("entry", ["../escaped.py", "C:/escaped.py", "/escaped.py", "sub/../../escaped.py"])
def test_embedded_runtime_archive_rejects_path_escape(layout, entry):
    layout["root"].mkdir(parents=True)
    archive = layout["root"] / "runtime.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(entry, "must not escape")
    stage = layout["root"] / "python-stage"
    stage.mkdir()
    result = common_snippet(layout, f"Expand-ContinueRuntime '{archive}' '{stage}'")
    assert result.returncode != 0
    assert "Unsafe" in (result.stdout + result.stderr)
    assert not (layout["root"] / "escaped.py").exists()


def test_repair_registration_failure_restores_previous_app_and_task(layout):
    original = install(layout)
    before = (layout["root"] / "app" / "plugin" / "GameHubDeck" / "dist" / "index.js").read_bytes()
    (layout["package"] / "plugin" / "GameHubDeck" / "dist" / "index.js").write_text("new version\n", encoding="utf-8")
    path = layout["profile"] / "fixture_state.json"
    state = read_json(path)
    old_task = state["task"]
    state["fail_register"] = True
    path.write_text(json.dumps(state), encoding="utf-8")
    result = run_script(layout, "install.ps1", "-AcceptDebugPort")
    assert result.returncode != 0
    assert "registration failed" in (result.stdout + result.stderr)
    assert read_json(layout["root"] / "install.json")["install_id"] == original["install_id"]
    assert (layout["root"] / "app" / "plugin" / "GameHubDeck" / "dist" / "index.js").read_bytes() == before
    after = read_json(path)
    assert after["task"] == old_task
    assert after["service_running"] is True
    assert (layout["steam"] / ".cef-enable-remote-debugging").exists()


def test_initial_registration_failure_removes_owned_flag_and_app(layout):
    path = layout["profile"] / "fixture_state.json"
    path.write_text(json.dumps({"task": None, "operations": [], "fail_register": True}), encoding="utf-8")
    result = run_script(layout, "install.ps1", "-AcceptDebugPort")
    assert result.returncode != 0
    assert not (layout["root"] / "app").exists()
    assert not (layout["root"] / "install.json").exists()
    assert not (layout["steam"] / ".cef-enable-remote-debugging").exists()
    assert read_json(path)["task"] is None


def test_status_reports_media_port_occupied_by_other_process(layout):
    install(layout)
    path = layout["profile"] / "fixture_state.json"
    state = read_json(path)
    state.update(steam_running=True, cdp="steam", media="other")
    path.write_text(json.dumps(state), encoding="utf-8")
    result = run_script(layout, "status.ps1", "-Json", installed=True)
    assert result.returncode == 0, result.stdout + result.stderr
    status = json.loads(result.stdout)
    assert status["media"] == "other"
    assert "8793" in status["hint"] and "another program" in status["hint"]


@pytest.mark.parametrize("architecture,wow64,expected", [
    ("AMD64", "", "amd64"), ("ARM64", "", "arm64"), ("x86", "AMD64", "amd64"),
])
def test_runtime_download_selects_native_architecture(layout, architecture, wow64, expected):
    result = common_snippet(layout, f"$env:PROCESSOR_ARCHITECTURE='{architecture}'; $env:PROCESSOR_ARCHITEW6432='{wow64}'; Get-ContinueArchitecture")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == expected


def test_unsupported_automatic_runtime_architecture_is_clear(layout):
    result = common_snippet(layout, "$env:PROCESSOR_ARCHITECTURE='x86'; $env:PROCESSOR_ARCHITEW6432=''; Get-ContinueArchitecture")
    assert result.returncode != 0
    assert "x64 and ARM64" in (result.stdout + result.stderr)


def test_owned_debug_flag_edited_after_install_is_preserved(layout):
    install(layout)
    flag = layout["steam"] / ".cef-enable-remote-debugging"
    flag.write_text("changed by another tool", encoding="utf-8")
    result = run_script(layout, "uninstall.ps1", "-RemoveData", installed=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert flag.read_text() == "changed by another tool"


def test_lf_setup_cmd_executes_fixture_install_without_elevation(layout):
    def quote(value):
        return '"' + str(value) + '"'
    # CALL is the same batch-to-batch-safe parsing used by the ZIP's root
    # setup.cmd.  Passing an already quoted command as one argv element makes
    # Python quote it a second time for CreateProcess and does not model a
    # Windows Explorer double click.
    command = ["cmd.exe", "/d", "/c", "call", str(layout["package"] / "pc" / "setup.cmd"),
               "-FixtureProfile", str(layout["profile"]), "-FixtureSteam", str(layout["steam"]),
               "-FixturePython", str(layout["python"]), "-AcceptDebugPort", "-NonInteractive"]
    result = subprocess.run(command, stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (layout["root"] / "install.json").exists()


def test_retained_data_can_later_be_explicitly_purged(layout):
    install(layout)
    payload = layout["root"] / "data" / "large-cache.bin"
    payload.write_bytes(b"retained media")
    kept = run_script(layout, "uninstall.ps1", "-KeepData", installed=True)
    assert kept.returncode == 0, kept.stdout + kept.stderr
    assert not (layout["root"] / "install.json").exists()
    assert payload.exists()
    purged = run_script(layout, "uninstall.ps1", "-RemoveData")
    assert purged.returncode == 0, purged.stdout + purged.stderr
    assert not payload.exists(), "explicit purge must remove previously retained owned data"
    assert not layout["root"].exists(), "verified empty owned root should be removed"


def test_unowned_continue_data_is_not_claimed_or_deleted(layout):
    (layout["root"] / "data").mkdir(parents=True)
    payload = layout["root"] / "data" / "foreign.bin"
    payload.write_bytes(b"unknown")
    result = run_script(layout, "uninstall.ps1", "-RemoveData")
    assert result.returncode != 0
    assert payload.read_bytes() == b"unknown"


def test_pending_startup_restore_survives_data_purge(layout):
    install(layout)
    previous = {"id": "123", "path": "/uioverrides/movies/owner.webm", "shuffle": True}
    (layout["root"] / "settings.json").write_text(json.dumps({
        "startup_movie_prev": previous, "private_unrelated": "must be purged"}), encoding="utf-8")
    movie = layout["steam"] / "config/uioverrides/movies/continue_no_startup.webm"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"changed foreign movie")
    record = {"created": True, "sha256": hashlib.sha256(b"original blank movie").hexdigest()}
    (layout["root"] / "startup_movie.json").write_text(json.dumps(record), encoding="utf-8")
    result = run_script(layout, "uninstall.ps1", "-RemoveData", installed=True)
    assert result.returncode == 2, result.stdout + result.stderr
    recovery = read_json(layout["root"] / "uninstall-recovery.json")
    assert recovery["startup_movie"]["previous"] == previous
    assert not (layout["root"] / "settings.json").exists()
    assert "private_unrelated" not in (layout["root"] / "uninstall-recovery.json").read_text()
    assert movie.read_bytes() == b"changed foreign movie"
    assert "not confirmed" in result.stdout
    assert "Steam Settings" in result.stdout
    assert "owner.webm" in result.stdout


@pytest.mark.parametrize("operation", ["install.ps1", "uninstall.ps1"])
def test_lifecycle_stops_before_changes_when_updater_holds_lock(layout, operation):
    from public_update import PublicUpdater
    install(layout)
    state_path = layout["profile"] / "fixture_state.json"
    state_before = state_path.read_bytes()
    app_before = (layout["root"] / "app/pc/gamehub_bp.py").read_bytes()
    with PublicUpdater(layout["root"])._lock():
        args = ["-AcceptDebugPort"] if operation == "install.ps1" else ["-RemoveData"]
        result = run_script(layout, operation, *args)
    assert result.returncode != 0, "lifecycle must respect the updater byte-range lock"
    assert state_path.read_bytes() == state_before
    assert (layout["root"] / "app/pc/gamehub_bp.py").read_bytes() == app_before
    assert "lock" in (result.stdout + result.stderr).lower()


def test_active_known_gamehub_consumer_keeps_shared_debug_flag(layout):
    install(layout)
    state_path = layout["profile"] / "fixture_state.json"
    state = read_json(state_path)
    owner = layout["profile"] / "owner GameHub" / "gamehub_bp.py"
    owner.parent.mkdir()
    owner.write_text("owner service, never executed", encoding="utf-8")
    state["gamehub_task"] = {"name": "GameHubBigPicture", "state": "Running",
        "execute": str(layout["python"]), "arguments": f'"{owner}" run'}
    state_path.write_text(json.dumps(state), encoding="utf-8")
    result = run_script(layout, "uninstall.ps1", "-RemoveData", installed=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (layout["steam"] / ".cef-enable-remote-debugging").exists()
    assert read_json(state_path)["gamehub_task"] == state["gamehub_task"]
    assert "GameHubBigPicture" in result.stdout


def test_mid_cleanup_failure_retains_recovery_and_retry_completes(layout):
    install(layout)
    state_path = layout["profile"] / "fixture_state.json"
    state = read_json(state_path)
    state["fail_remove"] = str(layout["root"] / "data")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (layout["root"] / "data/cache.bin").write_bytes(b"cached data")
    result = run_script(layout, "uninstall.ps1", "-RemoveData", installed=True)
    assert result.returncode == 1
    assert not (layout["root"] / "app").exists()
    assert (layout["root"] / "install.json").exists()
    assert read_json(layout["root"] / "uninstall-recovery.json")["state"] == "cleaning"
    state = read_json(state_path)
    state["fail_remove"] = None
    state_path.write_text(json.dumps(state), encoding="utf-8")
    result = run_script(layout, "uninstall.ps1", "-RemoveData")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not layout["root"].exists()


@pytest.mark.parametrize("operation", ["install.ps1", "uninstall.ps1"])
def test_pending_update_journal_and_rollback_bytes_are_preserved(layout, operation):
    install(layout)
    state_path = layout["profile"] / "fixture_state.json"
    state_before = state_path.read_bytes()
    journal = layout["root"] / "update-journal.json"
    journal.write_text('{"state":"backed_up","backup":"app.previous-' + '1' * 32 + '"}', encoding="utf-8")
    backup = layout["root"] / ("app.previous-" + "1" * 32)
    backup.mkdir()
    (backup / "keep.bin").write_bytes(b"rollback app")
    result = run_script(layout, operation, *(["-AcceptDebugPort"] if operation == "install.ps1" else ["-RemoveData"]))
    assert result.returncode == 1
    assert "journal" in (result.stdout + result.stderr).lower()
    assert state_path.read_bytes() == state_before
    assert journal.exists() and (backup / "keep.bin").read_bytes() == b"rollback app"
    assert (layout["root"] / "app").exists()


def test_owned_purge_preserves_unknown_root_objects_and_reports_them(layout):
    install(layout)
    foreign = layout["root"] / "unrelated.txt"
    foreign.write_bytes(b"unowned root file")
    result = run_script(layout, "uninstall.ps1", "-RemoveData", installed=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert foreign.read_bytes() == b"unowned root file"
    assert "unrelated.txt" in result.stdout
    assert not (layout["root"] / "data").exists()


def test_foreign_task_prevents_uninstall_before_any_mutation(layout):
    install(layout)
    state_path = layout["profile"] / "fixture_state.json"
    state = read_json(state_path)
    state["task"] = {"name": "ContinueBigPicture", "execute": "foreign.exe", "arguments": "foreign"}
    state_path.write_text(json.dumps(state), encoding="utf-8")
    before = state_path.read_bytes()
    result = run_script(layout, "uninstall.ps1", "-RemoveData", installed=True)
    assert result.returncode == 1
    assert state_path.read_bytes() == before
    assert not (layout["root"] / "uninstall-recovery.json").exists()
    assert (layout["root"] / "app").exists()


def test_reinstall_recovers_only_previous_movie_choice_after_pending_purge(layout):
    install(layout)
    previous = {"id": "42", "path": "/uioverrides/movies/prior.webm", "shuffle": False}
    (layout["root"] / "settings.json").write_text(json.dumps({"startup_movie_prev": previous}), encoding="utf-8")
    (layout["root"] / "startup_movie.json").write_text(json.dumps({"created": True, "sha256": "a" * 64}), encoding="utf-8")
    result = run_script(layout, "uninstall.ps1", "-RemoveData", installed=True)
    assert result.returncode == 2, result.stdout + result.stderr
    manifest = install(layout)
    assert read_json(layout["root"] / "settings.json") == {"startup_movie_prev": previous}
    assert read_json(layout["root"] / "uninstall-recovery.json")["owner"]["install_id"] == manifest["install_id"]


def test_retained_recovery_does_not_authorize_tampered_paths(layout, tmp_path):
    install(layout)
    result = run_script(layout, "uninstall.ps1", "-KeepData", installed=True)
    assert result.returncode == 0
    path = layout["root"] / "uninstall-recovery.json"
    recovery = read_json(path)
    outside = tmp_path / "not Continue"
    outside.mkdir()
    (outside / "keep.txt").write_bytes(b"foreign")
    recovery["owner"]["app"] = str(outside)
    path.write_text(json.dumps(recovery), encoding="utf-8")
    result = run_script(layout, "uninstall.ps1", "-RemoveData")
    assert result.returncode == 1
    assert (outside / "keep.txt").read_bytes() == b"foreign"
    assert (layout["root"] / "data").exists()


def test_retained_recovery_rejects_reparse_data_without_touching_target(layout, tmp_path):
    install(layout)
    assert run_script(layout, "uninstall.ps1", "-KeepData", installed=True).returncode == 0
    (layout["root"] / "data").rmdir()
    target = tmp_path / "junction target"
    target.mkdir()
    protected = target / "keep.bin"
    protected.write_bytes(b"foreign target")
    linked = layout["root"] / "data"
    result = common_snippet(layout, f"New-Item -ItemType Junction -Path '{linked}' -Target '{target}' | Out-Null")
    assert result.returncode == 0, result.stdout + result.stderr
    result = run_script(layout, "uninstall.ps1", "-RemoveData")
    assert result.returncode == 1
    assert "Linked" in (result.stdout + result.stderr)
    assert protected.read_bytes() == b"foreign target"
