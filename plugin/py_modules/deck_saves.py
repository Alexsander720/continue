"""«Где остановился» по сейвам, лежащим на самом Деке. Всё офлайн, только чтение.

Каждый читатель возвращает «сейв-подобный» словарь в формате хаба
({place, observed_at, progress{...}}) плюс свои готовые факты; дальше его рисует та же
логика hubcard.block_from_save / save_facts, что и карточки хаба. Поле считается
фактом, только если оно прочитано из файла, а не выведено догадкой.
"""
import base64, glob, json, os, shutil, struct, subprocess, time, zlib

from ui_i18n import date_text, t

HOME = "/home/deck"
STEAM = f"{HOME}/.local/share/Steam"
PFX = f"{STEAM}/steamapps/compatdata/{{appid}}/pfx/drive_c/users/steamuser"


def _mtime(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return None


def _date_ru(ts):
    return date_text(ts)

# ───────────── Inscryption (разбор из хаба, saves.parse_inscryption) ─────────────

def inscryption(data_dir):
    # 05.10: разбор Codex (ddsaves.inscryption); «Акт 2»/колода/зубы/жизни старого regex были из сюжетного забега
    out = _dd("inscryption")
    if out:
        out.pop("_r", None)   # место/этап забега не доказаны — place пустой (Мод Кейси/«сюжет пройден» владельцу не нужны)
    return out

# ───────────── Разборы ddsaves (приёмка deep_dig 02.10.2026) ─────────────
# Та же копия, что в хабе (GameHub/ddsaves → py_modules/ddsaves, копирует deck_sync.py). Названия — только из данных
# игр; прежние таблицы по памяти (царства Odyssey вперемешку, «Плато Начала», «Деревня персиковых цветов») удалены.

def _dd(slug, sub=""):
    import importlib
    try:
        mod = importlib.import_module(f"ddsaves.{slug}")
    except ModuleNotFoundError as e:   # публичная сборка: недоказанных разборов в ней нет
        if e.name == f"ddsaves.{slug}":
            return None
        raise
    r = mod.read(None)
    if not r.get("source_path"):
        return None
    observed = r.get("observed_at")
    prog = dict(r.get("progress") or {})
    if r.get("objective"):
        prog.setdefault("objective_desc", r["objective"])
    return {"save": {"place": r.get("place"), "observed_at": observed, "progress": prog,
                     "unproven": r.get("unproven") or []},
            "facts": r.get("facts") or [], "sub": sub(r) if callable(sub) else sub,
            "detail": t("saved_on", date=_date_ru(observed)) if observed else "", "shot": None, "_r": r}


def _plain(slug, sub=""):
    def reader(data_dir):
        out = _dd(slug, sub)
        if out:
            out.pop("_r", None)
        return out
    return reader


hollow_knight = _plain("hollow_knight")
lego_harry_potter = _plain("lego_harry_potter", lambda r: (r.get("progress") or {}).get("part", ""))
enslaved = _plain("enslaved")  # сложность — в фактах, второй раз подзаголовком не дублируем
nine_sols = _plain("nine_sols")
# Приняты 03.10.2026 из deep_dig/codex (проверены на пошаговых чужих сейвах): прежний undertale брал «Руины»
# по диапазону номеров комнат (по памяти) — теперь комната из data.win игры.
undertale = _plain("undertale")
slay_the_spire = _plain("slay_the_spire")
little_nightmares = _plain("little_nightmares")
little_nightmares_2 = _plain("little_nightmares_2")
# 03.10.2026 вечер: ПК-игры (Big Picture на ПК берёт тот же READERS) и круги 3–4 Антигравити
spider_man_2 = _plain("spider_man_2")
reanimal = _plain("reanimal")
alan_wake = _plain("alan_wake", lambda r: r.get("chapter") or "")
nier_automata = _plain("nier_automata")
life_is_strange_2 = _plain("life_is_strange_2")
horizon_forbidden_west = _plain("horizon_forbidden_west")
expedition_33 = _plain("expedition_33")
until_dawn = _plain("until_dawn")
silent_hill_2 = _plain("silent_hill_2")
# круг 5 (04.10): новые игры на ПК (Hogwarts требует ooz — есть только в Python ПК; на Деке игры нет)
bleach_rebirth_of_souls = _plain("bleach_rebirth_of_souls")
it_takes_two = _plain("it_takes_two")
hogwarts_legacy = _plain("hogwarts_legacy")
life_is_strange_double_exposure = _plain("life_is_strange_double_exposure")
# 08.10: GoW Ragnarök из GameHub/gowsave.py — только доказанное (место/задание из заголовка, вороны, серебро, время)
god_of_war_ragnarok = _plain("god_of_war_ragnarok")
the_last_of_us_part_ii = _plain("the_last_of_us_part_ii")
def uncharted_lot(data_dir):
    out = _dd("uncharted_lot")
    if out:
        result = out.pop("_r")
        # Legacy card transport calls its presentation title "place". The
        # canonical reader proves a chapter, and does not claim a location.
        out["save"]["place"] = result.get("chapter")
    return out

from ddsaves import hollow_knight as _dd_hk  # noqa: E402
HK_ZONES = _dd_hk.ZONES  # для _hk_tables_test: таблица Деки == данные игры


READERS = {
    367520: hollow_knight,
    2950340: lego_harry_potter,
    245280: enslaved,
    1809540: nine_sols,
    1092790: inscryption,
    391540: undertale,
    646570: slay_the_spire,
    424840: little_nightmares,
    2149010: little_nightmares,
    860510: little_nightmares_2,
    2651280: spider_man_2,
    2129530: reanimal,
    108710: alan_wake,
    524220: nier_automata,
    532210: life_is_strange_2,
    2420110: horizon_forbidden_west,
    1903340: expedition_33,
    2172010: until_dawn,
    2124490: silent_hill_2,
    1689620: bleach_rebirth_of_souls,
    1426210: it_takes_two,
    990080: hogwarts_legacy,
    1874000: life_is_strange_double_exposure,
    2322010: god_of_war_ragnarok,
    2531310: the_last_of_us_part_ii,
    1659420: uncharted_lot,
}


# Личные разборы владельца (не публикуются): лежат рядом, в публичной сборке файла нет.
try:
    from deck_saves_private import READERS as _PRIVATE  # noqa: E402
    READERS.update(_PRIVATE)
except ImportError:
    pass


def read(appid, data_dir):
    fn = READERS.get(int(appid))
    if not fn:
        return None
    try:
        return fn(data_dir)
    except Exception as e:  # битый сейв не должен ронять страницу игры
        return {"error": f"{type(e).__name__}: {e}"}
