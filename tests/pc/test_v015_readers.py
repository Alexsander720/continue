"""Regression checks for v0.1.5 reader updates (GoW Ragnarök, SILENT HILL 2, Sally Face)."""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugin"
MODULES = PLUGIN / "py_modules"
if str(MODULES) not in sys.path:
    sys.path.insert(0, str(MODULES))
if str(ROOT / "pc") not in sys.path:
    sys.path.insert(0, str(ROOT / "pc"))


def test_sally_face_registered_and_assets_complete():
    import deck_saves
    from ddsaves import sally_face

    assert 541570 in deck_saves.READERS
    table = MODULES / "ddsaves" / "data" / "sally_face.json"
    doc = json.loads(table.read_text(encoding="utf-8"))
    assert len(doc["episodes"]) >= 5
    assert len(doc["items"]) >= 50
    assert len(doc["achievements"]) >= 25

    icons_dir = MODULES / "ddsaves" / "data" / "sally_face_icons"
    idx = json.loads((icons_dir / "index.json").read_text(encoding="utf-8"))
    assert len(idx["items"]) >= 50
    for entry in idx["items"].values():
        assert (icons_dir / entry["file"]).is_file()

    # Graceful empty result when save is absent
    res = sally_face.read(table.parent / "_nonexistent_sally_dir")
    assert res.get("source_path") is None


def test_sh2_and_gow_readers_and_icon_packs_complete():
    from ddsaves import god_of_war_ragnarok as gow
    from ddsaves import silent_hill_2 as sh2

    # GoW panel_row produces expected favor + nornir groups
    j = {"odin_ravens": {"done": 31, "total": 48}, "draugr_holes": {"done": 4, "total": 6}}
    n = {"chests": 12, "apples": 6, "horns": 6}
    row = gow.panel_row(j, n, "en")
    assert row and row["id"] == "gow_favors"
    assert len(row["groups"]) == 2
    assert row["groups"][0]["people"][0]["key"] == "nornir:chests"
    assert row["groups"][1]["people"][0]["key"] == "fav:odin_ravens"
    assert row["groups"][1]["people"][0]["value"] == "31/48"

    # SH2 icon pack completeness
    icons_dir = MODULES / "ddsaves" / "data" / "silent_hill_2_icons"
    idx = json.loads((icons_dir / "index.json").read_text(encoding="utf-8"))
    assert len(idx["items"]) >= 100
    assert (icons_dir / idx["ui"]["_health_cross"]).is_file()
    assert sh2._icon_rel("_health_cross") == "ddsaves/data/silent_hill_2_icons/_health_cross.png"


def test_apply_icons_resolves_groups_and_ddsaves_icon_rel_safely(tmp_path):
    from public_game_assets import seed_game_icons

    seed_game_icons(PLUGIN / "assets" / "game_icons", tmp_path)
    manifest = json.loads((tmp_path / "icons" / "manifest.json").read_text(encoding="utf-8"))
    tree = ast.parse((PLUGIN / "main.py").read_text(encoding="utf-8"))
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_apply_icons")
    ns = {"os": os, "DATA": str(tmp_path)}
    exec(compile(ast.Module(body=[method], type_ignores=[]), "main._apply_icons", "exec"), ns)
    plugin = types.SimpleNamespace(_icon_map=lambda: manifest, _plugin_dir=lambda: str(PLUGIN))

    # 1. GoW favor & nornir groups resolve from manifest
    gow_card = {
        "facts": [{
            "id": "gow_favors",
            "groups": [{
                "kind": "fav",
                "label": "Nine Realms favors",
                "people": [
                    {"key": "fav:odin_ravens", "name": "Odin's Ravens", "value": "31/48"},
                    {"key": "fav:draugr_holes", "name": "Draugr Holes", "value": "4/6"},
                    {"key": "nornir:chests", "name": "Nornir Chests", "value": "12"},
                ],
            }],
        }]
    }
    ns["_apply_icons"](plugin, gow_card, [2322010])
    people = gow_card["facts"][0]["groups"][0]["people"]
    assert all(p.get("icon", "").startswith("img:icons/2322010/") for p in people)

    # 2. SH2 & Sally Face icon_rel copy into DATA/icons/_ddsaves and reject traversal
    mixed_card = {
        "facts": [{
            "id": "items_panel",
            "groups": [{
                "kind": "items",
                "label": "Items",
                "people": [
                    {"key": "sh2:health", "name": "Health", "icon_rel": "ddsaves/data/silent_hill_2_icons/_health_cross.png"},
                    {"key": "sf:item:1", "name": "Item", "icon_rel": "ddsaves/data/sally_face_icons/item_1.png"},
                    {"key": "bad", "name": "Bad", "icon_rel": "ddsaves/data/../../main.py"},
                ],
            }],
        }]
    }
    ns["_apply_icons"](plugin, mixed_card, [2124490])
    items = mixed_card["facts"][0]["groups"][0]["people"]
    assert items[0]["icon"].startswith("img:icons/_ddsaves/silent_hill_2_icons/_health_cross.png?v=")
    assert (tmp_path / "icons/_ddsaves/silent_hill_2_icons/_health_cross.png").is_file()
    assert items[1]["icon"].startswith("img:icons/_ddsaves/sally_face_icons/item_1.png?v=")
    assert (tmp_path / "icons/_ddsaves/sally_face_icons/item_1.png").is_file()
    assert "icon" not in items[2]
    assert "icon_rel" not in items[0] and "icon_rel" not in items[2]
