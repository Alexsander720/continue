"""Tests for standalone PublicPreferences card display backend.

Covers: global/per-game inheritance/reset, validation, Until Dawn
totems/clues/alive_count independent hide, synthetic toggles,
immutability, unrelated preservation, shared lock, malformed fail-safe,
bounded I/O, symlink guard, no I/O at construction.
"""
import copy
import json
import threading
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parents[2] / "pc"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from public_preferences import (
    PublicPreferences,
    filter_card,
    card_fields,
    effective_preferences,
    DEFAULTS,
    BOOL_KEYS,
)

import pytest


@pytest.fixture
def root(tmp_path):
    r = tmp_path / "continue_root"
    r.mkdir()
    return r


@pytest.fixture
def prefs(root):
    return PublicPreferences(root)


def test_no_io_at_construction(tmp_path):
    r = tmp_path / "noroot"
    # must not create dirs or files at construction
    p = PublicPreferences(r)
    assert not r.exists()
    assert not Path(str(r) + ".tmp").exists()
    p2 = PublicPreferences(r, settings_lock=threading.RLock())
    assert not r.exists()


def test_methods_and_call_rejection(root):
    p = PublicPreferences(root)
    assert {"get_card_preferences", "set_card_preference", "reset_card_preferences"} <= set(p.METHODS)
    assert p.call("get_card_preferences", [])["effective"]["story"] is True
    with pytest.raises(ValueError):
        p.call("nope", [])
    with pytest.raises(ValueError):
        p.call("get_card_preferences", "notalist")


def test_global_defaults_and_set(root):
    p = PublicPreferences(root)
    got = p.call("get_card_preferences", [])
    assert got["global"] == dict(DEFAULTS)
    assert got["game"] == {}
    assert got["effective"] == dict(DEFAULTS)
    out = p.call("set_card_preference", [None, "story", False])
    assert out["global"]["story"] is False
    assert out["effective"]["story"] is False
    # sparse persisted
    raw = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert raw["card_display"]["story"] is False


def test_pergame_inherit_and_override(root):
    p = PublicPreferences(root)
    p.call("set_card_preference", [None, "facts", False])
    got = p.call("get_card_preferences", [400])
    assert got["effective"]["facts"] is False
    assert got["game"] == {}
    p.call("set_card_preference", [400, "facts", True])
    got2 = p.call("get_card_preferences", [400])
    assert got2["game"] == {"facts": True}
    assert got2["effective"]["facts"] is True
    # other app unaffected
    got3 = p.call("get_card_preferences", [500])
    assert got3["effective"]["facts"] is False
    assert got3["game"] == {}


def test_null_clears_game_override_reject_global(root):
    p = PublicPreferences(root)
    p.call("set_card_preference", [400, "story", False])
    out = p.call("set_card_preference", [400, "story", None])
    assert "story" not in out["game"]
    assert out["effective"]["story"] is True
    with pytest.raises(ValueError):
        p.call("set_card_preference", [None, "story", None])


def test_reset_global_and_pergame(root):
    p = PublicPreferences(root)
    p.call("set_card_preference", [None, "story", False])
    p.call("set_card_preference", [400, "facts", False])
    p.call("set_card_preference", [500, "playtime", False])
    p.call("reset_card_preferences", [400])
    assert p.call("get_card_preferences", [400])["effective"]["facts"] is True  # reset clears override -> inherits global default True
    # per-game entry removed, other app kept
    raw = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert "400" not in (raw.get("card_display_games") or {})
    assert (raw.get("card_display_games") or {}).get("500") == {"playtime": False}
    p.call("reset_card_preferences", [None])
    got = p.call("get_card_preferences", [])
    assert got["global"] == dict(DEFAULTS)


def test_invalid_keys_types_ranges(root):
    p = PublicPreferences(root)
    with pytest.raises(ValueError):
        p.call("set_card_preference", [None, "nope", True])
    with pytest.raises(ValueError):
        p.call("set_card_preference", [None, "../settings", True])
    with pytest.raises(ValueError):
        p.call("set_card_preference", [None, "story", 1])  # strict bool, int rejected
    with pytest.raises(ValueError):
        p.call("set_card_preference", [None, "story", "false"])
    with pytest.raises(ValueError):
        p.call("set_card_preference", [None, "hidden_fact_ids", "x"])
    with pytest.raises(ValueError):
        p.call("set_card_preference", [None, "hidden_fact_ids", ["BAD UPPER"]])
    with pytest.raises(ValueError):
        p.call("set_card_preference", [None, "hidden_fact_ids", ["x" * 81]])
    with pytest.raises(ValueError):
        p.call("set_card_preference", [None, "hidden_fact_ids", ["a"] * 129])
    for bad_appid in [True, False, 0, -1, 2 ** 32, 400.5, "abc", "", [400], {"x": 1}]:
        with pytest.raises(ValueError):
            p.call("get_card_preferences", [bad_appid])
        with pytest.raises(ValueError):
            p.call("set_card_preference", [bad_appid, "story", True])
    # None appid means global and is valid
    assert p.call("get_card_preferences", [None])["game"] == {}
    # str appid ok
    assert p.call("get_card_preferences", ["400"])["game"] == {}


def _until_dawn_card():
    return {
        "appid": 1222140,
        "name": "Until Dawn",
        "block": {"kicker": "Where you left off", "title": "Chapter 4", "sub": "Cabin", "detail": "Find the totem"},
        "about": "About text derived",
        "standalone_about": "Standalone about override",
        "facts": [
            {"id": "totems", "label": "Totems", "value": "3 / 6"},
            {"id": "clues", "label": "Clues", "value": "12"},
            {"id": "alive_count", "label": "Alive", "value": "7 / 8", "has_characters": True},
            {"id": "playtime", "label": "Playtime", "value": "9.5h"},
            {"id": "achievements", "label": "Achievements", "value": "4 / 20"},
            {"id": "latest_achievement", "label": "Last achievement", "value": "Survivor"},
        ],
    }


def test_until_dawn_independent_hide(root):
    p = PublicPreferences(root)
    card = _until_dawn_card()
    # hide only totems
    p.call("set_card_preference", [None, "hidden_fact_ids", ["totems"]])
    eff = p.call("get_card_preferences", [])["effective"]
    out = filter_card(card, eff)
    ids = [f.get("id") for f in out["facts"]]
    assert "totems" not in ids
    assert "clues" in ids
    assert "alive_count" in ids
    # hide clues too, totems stay hidden independently
    p.call("set_card_preference", [None, "hidden_fact_ids", ["totems", "clues"]])
    eff2 = p.call("get_card_preferences", [])["effective"]
    out2 = filter_card(card, eff2)
    ids2 = [f.get("id") for f in out2["facts"]]
    assert "totems" not in ids2 and "clues" not in ids2 and "alive_count" in ids2


def test_synthetic_toggles(root):
    card = _until_dawn_card()
    p = PublicPreferences(root)
    p.call("set_card_preference", [None, "playtime", False])
    p.call("set_card_preference", [None, "achievements", False])
    p.call("set_card_preference", [None, "latest_achievement", False])
    eff = p.call("get_card_preferences", [])["effective"]
    out = filter_card(card, eff)
    ids = [f.get("id") for f in out["facts"]]
    assert "playtime" not in ids
    assert "achievements" not in ids
    assert "latest_achievement" not in ids
    # save facts kept
    assert "totems" in ids and "clues" in ids


def test_story_description_facts_characters(root):
    p = PublicPreferences(root)
    card = _until_dawn_card()
    eff = dict(DEFAULTS)
    eff.update({"story": False})
    out = filter_card(card, eff)
    assert out["block"] is None or all(k not in (out["block"] or {}) for k in ("kicker", "title", "sub", "objective"))
    # description false removes detail/about but keeps standalone_about
    eff2 = dict(DEFAULTS)
    eff2.update({"description": False})
    out2 = filter_card(card, eff2)
    assert (out2.get("block") or {}).get("detail") in (None, "")
    assert out2.get("about") in (None, "")
    assert out2.get("standalone_about") == "Standalone about override"
    # facts false clears all
    eff3 = dict(DEFAULTS)
    eff3.update({"facts": False})
    out3 = filter_card(card, eff3)
    assert out3["facts"] == []
    # characters false hides people rows only
    eff4 = dict(DEFAULTS)
    eff4.update({"characters": False})
    out4 = filter_card(card, eff4)
    ids4 = [f.get("id") for f in out4["facts"]]
    assert "alive_count" not in ids4
    assert "totems" in ids4


def test_hidden_exact_match_only(root):
    card = _until_dawn_card()
    eff = dict(DEFAULTS)
    eff.update({"hidden_fact_ids": ["totem"]})  # not exact "totems"
    out = filter_card(card, eff)
    assert "totems" in [f.get("id") for f in out["facts"]]


def test_immutability():
    card = _until_dawn_card()
    snapshot = copy.deepcopy(card)
    eff = dict(DEFAULTS)
    eff.update({"story": False, "facts": False, "hidden_fact_ids": ["totems"]})
    out = filter_card(card, eff)
    assert card == snapshot
    assert out is not card


def test_card_fields_no_fabrication():
    card = _until_dawn_card()
    fields = card_fields(card)
    # only actual source facts, no invented counts; synthetic excluded?
    # at least totems/clues/alive present, each has id/label/has_characters/visible
    by_id = {f["id"]: f for f in fields}
    assert "totems" in by_id and "clues" in by_id
    for f in fields:
        assert set(f.keys()) == {"id", "label", "has_characters", "visible"}
    # no invented counts: len equals source facts minus synthetic? allow <= len(card facts)
    assert len(fields) <= len(card["facts"])


def test_preserve_unrelated_and_other_apps(root):
    (root / "settings.json").write_text(json.dumps({
        "music_choices": {"400": "none"},
        "theme_music_consent": True,
        "startup_movie_prev": {"id": "1"},
        "card_display": {"story": False},
        "card_display_games": {"400": {"facts": False}},
    }), encoding="utf-8")
    p = PublicPreferences(root)
    p.call("set_card_preference", [500, "playtime", False])
    raw = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert raw["music_choices"] == {"400": "none"}
    assert raw["theme_music_consent"] is True
    assert raw["card_display"] == {"story": False}
    assert raw["card_display_games"]["400"] == {"facts": False}
    assert raw["card_display_games"]["500"] == {"playtime": False}


def test_shared_lock_atomic(root):
    shared = threading.RLock()
    a = PublicPreferences(root, settings_lock=shared)
    b = PublicPreferences(root, settings_lock=shared)
    assert a._settings_lock is shared and b._settings_lock is shared
    errors = []

    def worker(n):
        try:
            for i in range(20):
                a.call("set_card_preference", [800 + (n % 4), "story", bool(i % 2)])
                a.call("get_card_preferences", [800 + (n % 4)])
        except Exception as e:  # noqa
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    raw = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert len(raw.get("card_display_games", {})) <= 4


def test_malformed_failsafe_no_delete(root):
    (root / "settings.json").write_text("{not json", encoding="utf-8")
    before = (root / "settings.json").read_bytes()
    p = PublicPreferences(root)
    got = p.call("get_card_preferences", [400])
    assert got["effective"] == dict(DEFAULTS)
    # get must not delete/truncate
    assert (root / "settings.json").read_bytes() == before
    # bad types fail safe
    (root / "settings.json").write_text(json.dumps({"card_display": "oops", "music_choices": {"1": "x"}}), encoding="utf-8")
    got2 = p.call("get_card_preferences", [])
    assert got2["effective"] == dict(DEFAULTS)
    out = p.call("set_card_preference", [None, "story", False])
    assert out["effective"]["story"] is False
    raw = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert raw["music_choices"] == {"1": "x"}


def test_symlink_guard(tmp_path):
    r = tmp_path / "rr"
    r.mkdir()
    target = tmp_path / "outside.json"
    target.write_text(json.dumps({"card_display": {"story": False}}), encoding="utf-8")
    link = r / "settings.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not permitted")
        return
    p = PublicPreferences(r)
    got = p.call("get_card_preferences", [])
    assert got["effective"] == dict(DEFAULTS)
    with pytest.raises(ValueError):
        p.call("set_card_preference", [None, "story", False])


def test_effective_helper():
    g = {"story": False}
    o = {"facts": False}
    eff = effective_preferences(g, o)
    assert eff["story"] is False and eff["facts"] is False and eff["description"] is True
    assert BOOL_KEYS


def test_symlink_guard_mocked(root, monkeypatch):
    import public_preferences as mod
    (root / "settings.json").write_text(json.dumps({"card_display": {"story": False}}), encoding="utf-8")
    monkeypatch.setattr(mod, "_is_symlink", lambda p: True)
    p = PublicPreferences(root)
    assert p.call("get_card_preferences", [])["effective"] == dict(DEFAULTS)
    with pytest.raises(ValueError):
        p.call("set_card_preference", [None, "story", False])


def test_max_apps_bound(root, monkeypatch):
    import public_preferences as mod
    monkeypatch.setattr(mod, "MAX_APPS", 2)
    p = PublicPreferences(root)
    p.call("set_card_preference", [1, "story", False])
    p.call("set_card_preference", [2, "story", False])
    with pytest.raises(ValueError):
        p.call("set_card_preference", [3, "story", False])


def test_stdlib_only_and_no_quota_io(root):
    import public_preferences as mod
    import ast
    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    allowed = {"copy", "json", "os", "re", "threading", "pathlib", "typing", "__future__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] in allowed, a.name
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in allowed, node.module
    assert "Steam" not in src and "registry" not in src.lower().replace("strict", "")


def test_no_credentials_leak(root):
    (root / "settings.json").write_text(json.dumps({
        "card_display": {"story": False},
        "secrets": {"x": 1},
        "music_choices": {"1": "y"},
    }), encoding="utf-8")
    p = PublicPreferences(root)
    got = p.call("get_card_preferences", [])
    blob = json.dumps(got)
    assert "secrets" not in blob and "music_choices" not in blob
    out = p.call("set_card_preference", [None, "facts", False])
    assert "secrets" not in json.dumps(out)
