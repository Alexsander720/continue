"""REANIMAL (appid 2129530) card parser.

Save: Unreal Engine 5.4 GVAS SaveSystem format (UserMetaData.sav + Default_<N>.sav).
Names come from antigravity/dumps/reanimal/ (generator antigravity/tools/reanimal_dump.py:
Everholm/Content/Localization/Game/{ru,en}/Game.locres decrypted with AES key).

Fields:
  chapter / place: "Глава {num}: {RU title}" from chapters.json
  chapter_num: 1..9 from chapter row in DT_ChapterSelect / chapters.json
  collected: total collectibles (masks + posters)
  masks: total masks found
  posters: total posters found
  active_gameplay_seconds: TotalPlayTime from Default_<N>.sav
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from _card import Facts, empty, finish
from ddsaves import gvas
from ddsaves._common import localize, select, ui, dur, newest, proton_user

APPID = 2129530
DUMPS = HERE / "data" / "reanimal"
SUB = "AppData/Local/REANIMAL/Saved/SaveGames"

_DATA = None


def get_data() -> dict:
    global _DATA
    if _DATA is None:
        ch = json.loads((DUMPS / "chapters.json").read_text(encoding="utf-8"))["data"]
        it = json.loads((DUMPS / "items.json").read_text(encoding="utf-8"))["data"]
        _DATA = {
            "chapters": ch["chapters"],
            "chapter_by_row": {c["row"]: c for c in ch["chapters"]},
            "masks": it.get("masks", {}),
            "total_masks": it.get("total_masks", 21),
            "total_posters": it.get("total_posters", 20),
            "total_collectibles": it.get("total_collectibles", 41),
        }
    return localize(_DATA)


def default_dirs() -> List[Path]:
    roots = []
    if os.environ.get("LOCALAPPDATA"):
        roots.append(Path(os.environ["LOCALAPPDATA"]) / "REANIMAL/Saved/SaveGames")
    roots += [u / SUB for u in proton_user(APPID)]
    return [d for r in roots if r.is_dir() for d in r.iterdir() if (d / "UserMetaData.sav").is_file()]


def find(path_or_dir: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """Finds directory containing UserMetaData.sav."""
    if path_or_dir is not None:
        p = Path(path_or_dir)
        if p.is_file():
            p = p.parent
        if (p / "UserMetaData.sav").is_file():
            return p
        hit = newest(p.rglob("UserMetaData.sav")) if p.is_dir() else None
        return hit.parent if hit else None
    hit = newest(d / "UserMetaData.sav" for d in default_dirs())
    return hit.parent if hit else None


def read(path_or_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    d = find(path_or_dir)
    if not d:
        return {**empty("Сохранение REANIMAL (UserMetaData.sav) не найдено"), "proven": [], "fact_sources": {}}

    meta_file = d / "UserMetaData.sav"
    try:
        meta = gvas.unwrap(gvas.records(meta_file.read_bytes()))
    except Exception as e:
        return finish({**empty(f"Ошибка чтения UserMetaData.sav ({type(e).__name__})"),
                       "proven": [], "fact_sources": {}}, meta_file)

    data = get_data()
    prof = meta.get("PlayerProfile") or {}
    slot = prof.get("LastSaveSlot") or 0
    slot_meta = dict(prof.get("SaveSlotToMetadata") or []).get(slot) or {}
    chapter_row = slot_meta.get("CurrentChapterRowName")
    unlocked = prof.get("UnlockedChapterRowNames") or []
    found = prof.get("CollectibleRowNames") or []
    posters = [x for x in found if str(x).startswith("Poster_")]
    masks = [x for x in found if not str(x).startswith("Poster_")]

    boy_mask_row = prof.get("BoyEquippedMaskName")
    girl_mask_row = prof.get("GirlEquippedMaskName")
    boy_mask_name = (data["masks"].get(boy_mask_row) or {}).get("ru") if boy_mask_row else None
    girl_mask_name = (data["masks"].get(girl_mask_row) or {}).get("ru") if girl_mask_row else None

    play = None
    game_file = d / f"Default_{slot}.sav"
    source_file = meta_file
    if game_file.is_file():
        try:
            st = gvas.unwrap(gvas.records(game_file.read_bytes())).get("AEverholmIngameGameState") or {}
            play = st.get("TotalPlayTime")
            source_file = newest([game_file, meta_file]) or meta_file
        except Exception:
            pass

    ch_info = data["chapter_by_row"].get(chapter_row)
    num = ch_info["num"] if ch_info else None
    title_ru = ch_info["ru"] if ch_info else None

    place = title_ru
    chapter = place

    progress = {
        "chapter_num": num,
        "chapters_total": len(data["chapters"]),
        "chapters_unlocked": len(unlocked),
        "chapter_row": chapter_row,
        "collected": len(found),
        "posters": len(posters),
        "masks": len(masks),
        "total_masks": data["total_masks"],
        "total_posters": data["total_posters"],
        "total_collectibles": data["total_collectibles"],
        "active_gameplay_seconds": play,
        "boy_equipped_mask": boy_mask_name or boy_mask_row,
        "girl_equipped_mask": girl_mask_name or girl_mask_row,
    }

    F = Facts()
    if num:
        F.sfact("chapter_num", "flag", "Глава", f"{num}/{len(data['chapters'])}")
    if found:
        F.sfact("collected", "gem", "Находки", f"{len(found)}/{data['total_collectibles']}")
        F.sfact("masks", "mask", "Маски", f"{len(masks)}/{data['total_masks']}")
        F.sfact("posters", "scroll", "Плакаты", f"{len(posters)}/{data['total_posters']}")
    if play and play >= 60:
        F.sfact("active_gameplay_seconds", "clock", "В этом сейве", dur(play))

    proven = ["place", "chapter", "chapter_num", "collected", "masks", "posters", "active_gameplay_seconds"]
    unproven = ["chapters_unlocked", "boy_equipped_mask", "girl_equipped_mask"]

    return finish({
        "place": place,
        "chapter": chapter,
        "objective": None,
        "progress": progress,
        "facts": F.items,
        "fact_sources": F.sources,
        "proven": proven,
        "unproven": unproven,
        "play_seconds": play,
    }, source_file)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=1))
