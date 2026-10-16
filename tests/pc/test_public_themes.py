"""Public standalone theme engine tests: isolated fixtures only, never owner Steam."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'pc'
MODNAME = "continue_public_themes"


def load_mod():
    assert (SOURCE / "public_themes.py").exists(), "public_themes.py missing"
    sys.path.insert(0, str(SOURCE))
    spec = importlib.util.spec_from_file_location(MODNAME, SOURCE / "public_themes.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def make_assets(base: Path):
    """Minimal public package: two themes + translations table."""
    assets = base / "assets"
    (assets / "ThemeA").mkdir(parents=True)
    (assets / "ThemeA" / "theme.json").write_text(json.dumps({
        "name": "ThemeA",
        "inject": {"shared.css": ["SP"]},
        "patches": {
            "Mode": {"default": "Off", "type": "checkbox",
                     "values": {"No": {}, "Yes": {"extra.css": ["SP"]}}},
            "Level": {"default": "0", "type": "slider",
                      "values": {"0": {"--x-lift": ["0", "SP"]},
                                 "1": {"--x-lift": ["10px", "SP"]}}},
            "Tint": {"default": "Solid", "type": "dropdown",
                     "values": {"Solid": {}, "Grad": {"grad.css": ["SP"]}},
                     "components": [{"name": "Color", "type": "color-picker",
                                     "on": "Solid", "default": "#112233",
                                     "css_variable": "--x-tint", "tabs": ["SP"]}]},
            "Section": {"type": "none", "values": {"_": {}}},
        },
    }), encoding="utf-8")
    (assets / "ThemeA" / "shared.css").write_text(
        ".OldClass { color: red; height: calc(100vh - 80px - 14px); }", encoding="utf-8")
    (assets / "ThemeA" / "extra.css").write_text(".OldClass { color: blue; }", encoding="utf-8")
    (assets / "ThemeA" / "grad.css").write_text(":root { --x: 1; }", encoding="utf-8")
    (assets / "ThemeB").mkdir(parents=True)
    (assets / "ThemeB" / "theme.json").write_text(json.dumps({
        "name": "ThemeB",
        "dependencies": {"ThemeA": {}},
        "inject": {"b.css": ["MainMenu"]},
    }), encoding="utf-8")
    (assets / "ThemeB" / "b.css").write_text(".MenuCls { color: green; }", encoding="utf-8")
    (assets / "css_translations.json").write_text(json.dumps({
        "row": ["OldClass", "MidClass", "NewClass"],
    }), encoding="utf-8")
    return assets


def test_import_and_construction_have_no_side_effects(tmp_path):
    mod = load_mod()
    assets = tmp_path / "a"
    assets.mkdir()
    root = tmp_path / "r"
    root.mkdir()
    mod.PublicThemes(assets, root)
    assert list(root.iterdir()) == []
    assert list(assets.iterdir()) == []


def test_no_owner_path_leakage(tmp_path):
    mod = load_mod()
    src = (SOURCE / "public_themes.py").read_text(encoding="utf-8")
    for banned in ("E:" + "/Scripts", "E:" + r"\Scripts", "deck@", "192.168", "config_USER",
                   "subprocess", "scp", "Deck API"):
        assert banned not in src, banned
    assets = tmp_path / "assets"
    assets.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(assets, root)
    assert pt.call("themes_list", []) == []
    assert pt.call("themes_css", []) == {"bp": "", "menu": "", "qam": ""}


def test_themes_list_full_contract(tmp_path):
    mod = load_mod()
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(make_assets(tmp_path), root)
    lst = pt.call("themes_list", [])
    assert {t["name"] for t in lst} == {"ThemeA", "ThemeB"}
    for t in lst:
        assert set(t) == {"name", "active", "required_by", "pc_note", "patches"}
        assert isinstance(t["name"], str) and isinstance(t["active"], bool)
        assert isinstance(t["required_by"], list) and isinstance(t["pc_note"], str)
        assert isinstance(t["patches"], list)
        for p in t["patches"]:
            assert set(p) == {"name", "type", "values", "value"}
            assert p["type"] in ("dropdown", "checkbox", "slider")
            assert isinstance(p["values"], list) and p["value"] in p["values"]
    # type=none section header is not a setting
    a = next(t for t in lst if t["name"] == "ThemeA")
    assert "Section" not in [p["name"] for p in a["patches"]]
    assert a["active"] is False
    # dependency shows up as required_by
    b = next(t for t in lst if t["name"] == "ThemeB")
    assert b["required_by"] == []
    assert a["required_by"] == []


def test_themes_set_toggle_and_validation(tmp_path):
    mod = load_mod()
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(make_assets(tmp_path), root)
    with pytest.raises(ValueError):
        pt.call("themes_set", ["Nope", None, True])
    with pytest.raises(ValueError):
        pt.call("themes_set", ["ThemeA", "Nope", "Yes"])
    with pytest.raises(ValueError):
        pt.call("themes_set", ["ThemeA", "Mode", "Maybe"])
    with pytest.raises(ValueError):
        pt.call("themes_set", ["ThemeA", None, "yes"])
    updated = pt.call("themes_set", ["ThemeA", None, True])
    assert next(t for t in updated if t["name"] == "ThemeA")["active"] is True
    updated = pt.call("themes_set", ["ThemeA", "Mode", "Yes"])
    assert next(t for t in updated if t["name"] == "ThemeA")["patches"][0]["value"] == "Yes"


def test_atomic_write_and_unrelated_state_preserved(tmp_path):
    mod = load_mod()
    root = tmp_path / "root"
    root.mkdir()
    assets = make_assets(tmp_path)
    (root / "themes.json").write_text(json.dumps({"_unrelated": {"x": 1}}), encoding="utf-8")
    pt = mod.PublicThemes(assets, root)
    pt.call("themes_set", ["ThemeA", None, True])
    assert list(root.glob("*.tmp")) == []
    st = json.loads((root / "themes.json").read_text(encoding="utf-8"))
    assert st["_unrelated"] == {"x": 1}
    assert st["ThemeA"]["active"] is True


def test_dependency_css_included(tmp_path):
    mod = load_mod()
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(make_assets(tmp_path), root)
    assert pt.call("themes_css", []) == {"bp": "", "menu": "", "qam": ""}
    pt.call("themes_set", ["ThemeB", None, True])
    css = pt.call("themes_css", [])
    # ThemeB (menu) pulls dependency ThemeA (bp)
    assert "MenuCls" in css["menu"]
    assert "OldClass" in css["bp"] or "MidClass" in css["bp"] or "NewClass" in css["bp"]
    lst = pt.call("themes_list", [])
    assert next(t for t in lst if t["name"] == "ThemeA")["required_by"] == ["ThemeB"]


def test_class_translation_newest_existing(tmp_path):
    mod = load_mod()
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(make_assets(tmp_path), root)
    pt.call("themes_set", ["ThemeA", None, True])
    css = pt.call("themes_css", [])
    assert ".NewClass" in css["bp"] and ".OldClass" not in css["bp"]
    css2 = pt.call("themes_css", [["MidClass"]])
    assert ".MidClass" in css2["bp"] and ".NewClass" not in css2["bp"]
    # PC fix applied like owner engine
    assert "calc(100vh - 40px - 14px" in css["bp"]


def test_tab_cycle_terminates(tmp_path):
    mod = load_mod()
    assets = tmp_path / "assets"
    (assets / "Loop").mkdir(parents=True)
    (assets / "Loop" / "theme.json").write_text(json.dumps({
        "name": "Loop", "tabs": {"a": ["b"], "b": ["a"]},
        "inject": {"l.css": ["a"]},
    }), encoding="utf-8")
    (assets / "Loop" / "l.css").write_text(".x{}", encoding="utf-8")
    (assets / "css_translations.json").write_text("{}", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(assets, root)
    pt.call("themes_set", ["Loop", None, True])
    assert pt.call("themes_css", []) == {"bp": "", "menu": "", "qam": ""}


def test_malformed_and_missing_json(tmp_path):
    mod = load_mod()
    assets = tmp_path / "assets"
    (assets / "Broken").mkdir(parents=True)
    (assets / "Broken" / "theme.json").write_text("{bad", encoding="utf-8")
    (assets / "Plain").mkdir(parents=True)
    (assets / "Plain" / "theme.css").write_text(".p{color:red}", encoding="utf-8")
    (assets / "Missing").mkdir(parents=True)
    (assets / "Missing" / "theme.json").write_text(json.dumps({
        "name": "Missing", "inject": {"ghost.css": ["SP"]}}), encoding="utf-8")
    (assets / "css_translations.json").write_text("{}", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(assets, root)
    names = [t["name"] for t in pt.call("themes_list", [])]
    assert "Broken" not in names
    assert "Plain" in names
    pt.call("themes_set", ["Missing", None, True])
    assert pt.call("themes_css", []) == {"bp": "", "menu": "", "qam": ""}


def test_path_traversal_rejected(tmp_path):
    mod = load_mod()
    assets = tmp_path / "assets"
    (assets / "Evil").mkdir(parents=True)
    (assets / "Evil" / "theme.json").write_text(json.dumps({
        "name": "Evil",
        "inject": {"../outside.css": ["SP"], "sub/../../x.css": ["SP"],
                   "file:///etc/passwd": ["SP"], "https://evil/x.css": ["SP"],
                   "/abs.css": ["SP"], "": ["SP"]},
    }), encoding="utf-8")
    (assets / "outside.css").write_text("EVIL-MARKER", encoding="utf-8")
    (assets / "css_translations.json").write_text("{}", encoding="utf-8")
    outside = tmp_path / "sneaky.css"
    outside.write_text("EVIL-MARKER", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(assets, root)
    pt.call("themes_set", ["Evil", None, True])
    css = pt.call("themes_css", [])
    assert "EVIL-MARKER" not in css["bp"]


def test_symlink_escape_rejected(tmp_path):
    mod = load_mod()
    assets = tmp_path / "assets"
    (assets / "Link").mkdir(parents=True)
    secret = tmp_path / "secret.css"
    secret.write_text("SECRET-MARKER", encoding="utf-8")
    try:
        (assets / "Link" / "evil.css").symlink_to(secret)
    except OSError:
        pytest.skip("symlink privilege unavailable")
    (assets / "Link" / "theme.json").write_text(json.dumps({
        "name": "Link", "inject": {"evil.css": ["SP"]}}), encoding="utf-8")
    (assets / "css_translations.json").write_text("{}", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(assets, root)
    pt.call("themes_set", ["Link", None, True])
    assert "SECRET-MARKER" not in pt.call("themes_css", [])["bp"]


def test_css_variables_and_color_components(tmp_path):
    mod = load_mod()
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(make_assets(tmp_path), root)
    pt.call("themes_set", ["ThemeA", None, True])
    pt.call("themes_set", ["ThemeA", "Level", "1"])
    css = pt.call("themes_css", [])
    assert "--x-lift" in css["bp"] and "10px" in css["bp"]
    css2 = pt.call("themes_css", [])
    assert "--x-tint" in css2["bp"] and "#112233" in css2["bp"]
    assert "_r:" in css2["bp"] and "_rgb:" in css2["bp"]


def test_checkbox_without_yes_no_becomes_dropdown(tmp_path):
    mod = load_mod()
    assets = tmp_path / "assets"
    (assets / "Odd").mkdir(parents=True)
    (assets / "Odd" / "theme.json").write_text(json.dumps({
        "name": "Odd",
        "patches": {"Pick": {"type": "checkbox", "default": "A",
                             "values": {"A": {}, "B": {}}}}}), encoding="utf-8")
    (assets / "css_translations.json").write_text("{}", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    lst = mod.PublicThemes(assets, root).call("themes_list", [])
    assert next(t for t in lst if t["name"] == "Odd")["patches"][0]["type"] == "dropdown"


def test_pc_off_defaults_and_note(tmp_path):
    mod = load_mod()
    assets = tmp_path / "assets"
    for name in ("Clean Gameview", "No What's New", "Round"):
        (assets / name).mkdir(parents=True)
        (assets / name / "theme.json").write_text(json.dumps({"name": name}), encoding="utf-8")
    (assets / "css_translations.json").write_text("{}", encoding="utf-8")
    (assets / "defaults.json").write_text(json.dumps({
        "Clean Gameview": {"active": True},
        "No What's New": {"active": True},
        "Round": {"active": True}}), encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    lst = mod.PublicThemes(assets, root).call("themes_list", [])
    by = {t["name"]: t for t in lst}
    assert by["Clean Gameview"]["active"] is False
    assert by["No What's New"]["active"] is False
    assert by["Clean Gameview"]["pc_note"] != ""
    assert by["Round"]["active"] is True


def test_defaults_json_sanitized(tmp_path):
    mod = load_mod()
    assets = make_assets(tmp_path)
    (assets / "defaults.json").write_text(json.dumps({
        "ThemeA": {"Mode": "Yes", "Nope": "x", "Level": "HACK"},
        "Ghost": {"active": True},
        "__proto__": {"x": 1}}), encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    lst = mod.PublicThemes(assets, root).call("themes_list", [])
    a = next(t for t in lst if t["name"] == "ThemeA")
    assert next(p for p in a["patches"] if p["name"] == "Mode")["value"] == "Yes"
    assert next(p for p in a["patches"] if p["name"] == "Level")["value"] == "0"


def test_strict_validation(tmp_path):
    mod = load_mod()
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(make_assets(tmp_path), root)
    with pytest.raises(ValueError):
        pt.call("themes_set", ["ThemeA", None, True, "extra", "x", "y", "z", "w", "v"])
    with pytest.raises(ValueError):
        pt.call("themes_set", ["x" * 500, None, True])
    with pytest.raises(ValueError):
        pt.call("themes_set", [123, None, True])
    with pytest.raises(ValueError):
        pt.call("themes_css", [["x" * 500]])
    with pytest.raises(ValueError):
        pt.call("nope", [])
    with pytest.raises(ValueError):
        pt.call("themes_list", "x")
    assert mod.PublicThemes.METHODS == {"themes_list", "themes_set", "themes_css"}


def test_no_shell_network_imports():
    src = (SOURCE / "public_themes.py").read_text(encoding="utf-8")
    for banned in ("subprocess", "socket", "urllib", "http.client", "os.system",
                   "os.popen", "scp", "deck@", "192.168"):
        assert banned not in src, banned


def test_patch_value_preserves_components_dict(tmp_path):
    mod = load_mod()
    root = tmp_path / "root"
    root.mkdir()
    pt = mod.PublicThemes(make_assets(tmp_path), root)
    pt.call("themes_set", ["ThemeA", "Tint", "Grad"])
    st = json.loads((root / "themes.json").read_text(encoding="utf-8"))
    assert st["ThemeA"]["Tint"] == "Grad"
