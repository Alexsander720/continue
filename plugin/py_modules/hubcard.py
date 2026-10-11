"""Логика карточки «Где остановился» — перенос главного блока и ряда фактов из web/home.js
Game Hub (saveMain / stateMain / SAVE_FACTS). Общий модуль: им пользуются и deck_sync.py на ПК
(карточки хаба), и бэкенд плагина на Деке (сейвы, разобранные на самом Деке)."""
import re

from ddsaves._common import lang
from ui_i18n import authored_label, stamina_value, t

STATE_PLACEHOLDERS = {"настройки", "settings", "options", "параметры", "опции", "главное меню", "меню", "main menu",
                      "menu", "в меню", "пауза", "pause", "pause menu", "загрузка", "loading", "магазин", "store", "shop"}
SAVE_SLOT_PLACE = re.compile(r"^\s*(?:слот сохранения|saveslot_)", re.I)
INTERNAL_NAME = re.compile(r"^[A-Za-z0-9]*(?:_[A-Za-z0-9]+|[a-z][A-Z])[A-Za-z0-9_]*$")


def clean(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v not in (None, "") else ""


def state_text(v):
    t = clean(v)
    k = re.sub(r"[ .,!?:;]+$", "", t.lower())
    return "" if (not k or k in STATE_PLACEHOLDERS or k.startswith("меню ")) else t


def split_place(text):
    """«Ванахейм - Джунгли - Отправиться в Муспельхейм» -> («Ванахейм - Джунгли», «Отправиться в Муспельхейм»):
    режем по последнему тире, как сама игра подписывает сохранения."""
    m = re.match(r"^(.*\S)\s+[-—–·]\s+(\S.*)$", str(text or ""))
    return (m.group(1), m.group(2)) if m else (text, "")


def block_from_save(save, state=None, last_known=None):
    s = save or {}
    if not s.get("place") or SAVE_SLOT_PLACE.match(s["place"]):
        return None
    if "place" in (s.get("unproven") or ()):  # недоказанное место — не заголовок (как в хабе, задача 238)
        return None
    mine = float(s.get("observed_at") or 0)
    prior = float((last_known or {}).get("observed_at") or 0)
    if mine and prior and mine < prior:
        return None
    title, sub = split_place(s["place"])
    detail = clean((s.get("progress") or {}).get("objective_desc")) or clean((state or {}).get("objective_detail"))
    return {"kicker": t("where_left_off"), "title": title, "sub": sub, "detail": detail,
            "observed_at": mine or None, "source": "save"}


def main_block(c):
    """Главный блок карточки хаба (порядок как в mainBlock web/home.js)."""
    b = block_from_save(c.get("save"), c.get("state"), c.get("last_known_context"))
    if b:
        return b
    lkc = c.get("last_known_context") or {}
    if lkc.get("objective"):
        title, sub = split_place(lkc["objective"])
        return {"kicker": t("last_known_place"), "title": title, "sub": sub, "detail": "",
                "observed_at": lkc.get("observed_at"), "source": "recording"}
    st = c.get("state") or {}
    obj, loc, act = state_text(st.get("objective")), state_text(st.get("location")), state_text(st.get("activity"))
    if obj:
        return {"kicker": t("where_left_off"), "title": obj, "sub": loc,
                "detail": clean(st.get("objective_detail")) or act, "observed_at": None, "source": "screen"}
    if state_text(st.get("rank")):
        sub = " · ".join(x for x in (state_text(st.get("character")), state_text(st.get("mode")), loc) if x)
        return {"kicker": t("your_result"), "title": state_text(st["rank"]), "sub": sub, "detail": act,
                "observed_at": None, "source": "screen"}
    if act or loc:
        return {"kicker": t("where_stopped"), "title": act or loc, "sub": loc if act else "", "detail": "",
                "observed_at": None, "source": "screen"}
    return None


def fmt_num(v):
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.1f}" if lang() == "en" else f"{v:,.1f}".replace(",", " ").replace(".", ",")
    return f"{int(v):,}" if lang() == "en" else f"{int(v):,}".replace(",", " ")


def _ravens(v):
    if isinstance(v, dict):
        c = v.get("collected", v.get("count", 0)) or 0
        return f"{c} / {v.get('total') or 48}" if c else ""
    try:
        return f"{int(v)} / 48"
    except (TypeError, ValueError):
        return ""


def dur_hm(sec):
    try:
        s = float(sec)
    except (TypeError, ValueError):
        return ""
    if s < 60:
        return ""
    h, m = int(s // 3600), round((s % 3600) / 60)
    return t("hours_minutes", h=h, m=m) if h else t("minutes", m=m)


SAVE_FACTS = [  # (ключ, подпись, иконка, формат) — порядок = важность, как SAVE_FACTS в хабе
    ("story_percent", "Сюжет", "scroll", lambda v, p: f"{round(float(v))}%" + (f" ({p['chapter']})" if p.get("chapter") else "")),
    ("active_gameplay_seconds", "Чистой игры", "clock", lambda v, p: dur_hm(v)),
    ("collected", "Находки", "gem", lambda v, p: fmt_num(v)),
    ("odin_ravens", "Вороны Одина", "raven", lambda v, p: _ravens(v)),
    ("ravens", "Вороны Одина", "raven", lambda v, p: _ravens(v)),
    ("percent", "Зачистка", "pie", lambda v, p: f"{round(float(v))}%"),
    ("completed_acts_count", "Актов пройдено", "check", lambda v, p: fmt_num(v)),
    ("act", "Акт", "book", lambda v, p: str(v)),
    ("story_stage", "Сюжет", "scroll", lambda v, p: t("story_stage", n=v, total=p["story_stages_total"]) if p.get("story_stages_total") else ""),
    ("chapter_title", "Глава", "bookmark", lambda v, p: str(v)),
    ("seals_count", "Печати Солов", "sun", lambda v, p: f"{v} / {p['seals_total']}" if p.get("seals_total") else str(v)),
    ("moons", "Луны", "moon", lambda v, p: fmt_num(v)),
    ("skills_count", "Навыки", "bolt", lambda v, p: fmt_num(v)),
    ("character_level", "Уровень", "level", lambda v, p: fmt_num(v)),
    ("gear_level", "Снаряжение", "shield", lambda v, p: t("gear_level", value=v)),
    ("deck_size", "Колода", "cards", lambda v, p: t("cards", n=fmt_num(v))),
    ("hacksilver", "Серебро", "coins", lambda v, p: fmt_num(v)),
    ("geo", "Гео", "coins", lambda v, p: fmt_num(v)),
    ("studs", "Детали", "coins", lambda v, p: fmt_num(v)),
    ("rupees", "Рупии", "coins", lambda v, p: fmt_num(v)),
    ("gold", "Золото", "coins", lambda v, p: fmt_num(v)),
    ("hearts", "Сердца", "heart", lambda v, p: str(v)),
    ("max_health", "Маски", "heart", lambda v, p: fmt_num(v)),
    ("lives", "Жизни", "heart", lambda v, p: fmt_num(v)),
    ("stamina_wheels", "Выносливость", "bolt", lambda v, p: stamina_value(v)),
    ("shrines", "Святилища", "target", lambda v, p: f"{v} / {p['shrines_total']}" if p.get("shrines_total") else str(v)),
    ("divine_beasts", "Чудища", "shield", lambda v, p: f"{v} / {p['divine_beasts_total']}" if p.get("divine_beasts_total") else str(v)),
    ("koroks", "Короки", "bookmark", lambda v, p: f"{v} / {p['koroks_total']}" if p.get("koroks_total") else str(v)),
    ("nail_damage", "Урон гвоздя", "sword", lambda v, p: fmt_num(v)),
    ("finished_levels", "Уровней", "check", lambda v, p: t("completed_count", n=fmt_num(v))),
    ("jumps", "Прыжки", "trend", lambda v, p: fmt_num(v)),
    ("jades_count", "Нефриты", "gem", lambda v, p: f"{v} / {p['jades_total']}" if p.get("jades_total") else str(v)),
    ("green_stars", "Зелёные звёзды", "star", lambda v, p: fmt_num(v)),
    ("gems", "Камни", "gem", lambda v, p: fmt_num(v)),
    ("crystals", "Кристаллы", "gem", lambda v, p: fmt_num(v)),
    ("checkpoint", "Чекпоинт", "bookmark", lambda v, p: str(v)),
    ("level", "Уровень", "level", lambda v, p: fmt_num(v)),
    ("completion_percent", "Зачистка", "pie", lambda v, p: f"{round(float(v))}%"),
    ("milestones_count", "Вехи", "signpost", lambda v, p: fmt_num(v)),
]


def save_facts(save, state=None, limit=4):
    prog = (save or {}).get("progress") or {}
    place = str((save or {}).get("place") or "")
    out, seen = [], set()
    for key, label, icon, fmt in SAVE_FACTS:
        if label in seen:
            continue
        raw = prog.get(key)
        if raw in (None, "", False):
            continue
        if isinstance(raw, str) and INTERNAL_NAME.match(raw.strip()):
            continue
        if isinstance(raw, (int, float)) and not raw > 0:
            continue
        if isinstance(raw, dict) and ("collected" in raw or "count" in raw) and not ((raw.get("collected", raw.get("count")) or 0) > 0):
            continue
        try:
            shown = fmt(raw, prog)
        except Exception:
            shown = ""
        if not shown or (key == "act" and shown in place):
            continue
        seen.add(label)
        out.append({"icon": icon, "label": authored_label(label), "value": shown})
    # уровень персонажа из разбора экранов — третьим, как в ряду хаба («Прогресс: Уровень 6»)
    if "Уровень" not in seen:
        for st in ((state or {}).get("progression") or {}).get("stats") or []:
            if st.get("kind") == "level" and st.get("value"):
                out.insert(min(2, len(out)), {"icon": "level", "label": t("label_progress"),
                                             "value": t("level_value", value=st["value"])})
                break
    return out[:limit]
