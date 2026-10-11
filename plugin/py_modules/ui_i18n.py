"""Authored Continue? interface text shared by the Deck and PC backends.

Game-written titles and objectives are deliberately not translated here.  The
selected language is read on every call because Decky can change it without
reloading the Python process.
"""
from __future__ import annotations

import copy
import re

from ddsaves._common import labels as common_labels, lang, select, ui as common_ui


I18N = {
    "ru": {
        "months": ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"),
        "where_left_off": "Где вы остановились",
        "last_known_place": "Последнее известное место",
        "your_result": "Твой результат",
        "where_stopped": "На чём остановились",
        "has_save": "Есть сохранение",
        "saved_on": "Сохранение от {date}",
        "minutes": "{m} мин",
        "hours_minutes": "{h} ч {m} мин",
        "story_stage": "этап {n} из {total}",
        "gear_level": "ур. {value}",
        "cards": "{n} карт",
        "completed_count": "{n} пройдено",
        "stamina_wheels": "{n} круг{suffix}",
        "level_value": "Уровень {value}",
        "label_progress": "Прогресс",
        "label_story": "Сюжет",
        "label_active_play": "Чистой игры",
        "label_collectibles": "Находки",
        "label_ravens": "Вороны Одина",
        "label_cleanup": "Зачистка",
        "label_acts_completed": "Актов пройдено",
        "label_act": "Акт",
        "label_chapter": "Глава",
        "label_seals": "Печати Солов",
        "label_moons": "Луны",
        "label_skills": "Навыки",
        "label_level": "Уровень",
        "label_gear": "Снаряжение",
        "label_deck": "Колода",
        "label_silver": "Серебро",
        "label_geo": "Гео",
        "label_studs": "Детали",
        "label_rupees": "Рупии",
        "label_gold": "Золото",
        "label_hearts": "Сердца",
        "label_masks": "Маски",
        "label_lives": "Жизни",
        "label_stamina": "Выносливость",
        "label_shrines": "Святилища",
        "label_beasts": "Чудища",
        "label_koroks": "Короки",
        "label_nail_damage": "Урон гвоздя",
        "label_levels": "Уровней",
        "label_jumps": "Прыжки",
        "label_jades": "Нефриты",
        "label_green_stars": "Зелёные звёзды",
        "label_gems": "Камни",
        "label_crystals": "Кристаллы",
        "label_checkpoint": "Чекпоинт",
        "label_milestones": "Вехи",
        "label_last_achievement": "Последнее достижение",
    },
    "en": {
        "months": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
        "where_left_off": "Where you left off",
        "last_known_place": "Last known location",
        "your_result": "Your result",
        "where_stopped": "Where you left off",
        "has_save": "Save found",
        "saved_on": "Saved on {date}",
        "minutes": "{m} min",
        "hours_minutes": "{h} h {m} min",
        "story_stage": "stage {n} of {total}",
        "gear_level": "Lv. {value}",
        "cards": "{n} cards",
        "completed_count": "{n} completed",
        "stamina_wheels": "{n} wheel{suffix}",
        "level_value": "Level {value}",
        "label_progress": "Progress",
        "label_story": "Story",
        "label_active_play": "Active play",
        "label_collectibles": "Collectibles",
        "label_ravens": "Odin's ravens",
        "label_cleanup": "Completion",
        "label_acts_completed": "Acts completed",
        "label_act": "Act",
        "label_chapter": "Chapter",
        "label_seals": "Sol seals",
        "label_moons": "Moons",
        "label_skills": "Skills",
        "label_level": "Level",
        "label_gear": "Gear",
        "label_deck": "Deck",
        "label_silver": "Silver",
        "label_geo": "Geo",
        "label_studs": "Studs",
        "label_rupees": "Rupees",
        "label_gold": "Gold",
        "label_hearts": "Hearts",
        "label_masks": "Masks",
        "label_lives": "Lives",
        "label_stamina": "Stamina",
        "label_shrines": "Shrines",
        "label_beasts": "Divine beasts",
        "label_koroks": "Koroks",
        "label_nail_damage": "Nail damage",
        "label_levels": "Levels",
        "label_jumps": "Jumps",
        "label_jades": "Jades",
        "label_green_stars": "Green stars",
        "label_gems": "Gems",
        "label_crystals": "Crystals",
        "label_checkpoint": "Checkpoint",
        "label_milestones": "Milestones",
        "label_last_achievement": "Latest achievement",
    },
    "uk": {
        "months": ("січня", "лютого", "березня", "квітня", "травня", "червня", "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"),
        "where_left_off": "Де ви зупинилися",
        "last_known_place": "Останнє відоме місце",
        "your_result": "Ваш результат",
        "where_stopped": "На чому зупинилися",
        "has_save": "Є збереження",
        "saved_on": "Збереження від {date}",
        "minutes": "{m} хв",
        "hours_minutes": "{h} год {m} хв",
        "story_stage": "етап {n} із {total}",
        "gear_level": "рів. {value}",
        "cards": "{n} карт",
        "completed_count": "{n} пройдено",
        "stamina_wheels": "{n} кол{suffix}",
        "level_value": "Рівень {value}",
        "label_progress": "Прогрес",
        "label_story": "Сюжет",
        "label_active_play": "Активної гри",
        "label_collectibles": "Знахідки",
        "label_ravens": "Ворони Одіна",
        "label_cleanup": "Проходження",
        "label_acts_completed": "Актів пройдено",
        "label_act": "Акт",
        "label_chapter": "Розділ",
        "label_seals": "Печатки Солів",
        "label_moons": "Місяці",
        "label_skills": "Навички",
        "label_level": "Рівень",
        "label_gear": "Спорядження",
        "label_deck": "Колода",
        "label_silver": "Срібло",
        "label_geo": "Гео",
        "label_studs": "Деталі",
        "label_rupees": "Рупії",
        "label_gold": "Золото",
        "label_hearts": "Серця",
        "label_masks": "Маски",
        "label_lives": "Життя",
        "label_stamina": "Витривалість",
        "label_shrines": "Святилища",
        "label_beasts": "Чудовиська",
        "label_koroks": "Короки",
        "label_nail_damage": "Шкода цвяха",
        "label_levels": "Рівнів",
        "label_jumps": "Стрибки",
        "label_jades": "Нефрити",
        "label_green_stars": "Зелені зірки",
        "label_gems": "Камені",
        "label_crystals": "Кристали",
        "label_checkpoint": "Контрольна точка",
        "label_milestones": "Віхи",
        "label_last_achievement": "Останнє досягнення",
    },
}


def t(key: str, **values) -> str:
    table = I18N.get(lang(), I18N["ru"])
    return table[key].format(**values)


def date_text(ts) -> str:
    import time
    value = time.localtime(ts)
    return f"{value.tm_mday} {I18N[lang()]['months'][value.tm_mon - 1]} {value.tm_year}"


_KICKERS = {
    "Где вы остановились": "where_left_off",
    "Последнее известное место": "last_known_place",
    "Твой результат": "your_result",
    "На чём остановились": "where_stopped",
    "Есть сохранение": "has_save",
}

_LABELS = {
    value: key
    for key, value in I18N["ru"].items()
    if key.startswith("label_")
}


def authored_label(value: str) -> str:
    """Translate only exact labels authored by Continue?, never game text."""
    key = _LABELS.get(value)
    if key:
        return t(key)
    data = common_labels()
    label_key = data["legacy"].get(value)
    return select(data["labels"].get(label_key)) or value if label_key else value


def stamina_value(value) -> str:
    if lang() == "ru":
        return f"{value} круг{'а' if value != 1 else ''}"
    if lang() == "en":
        return f"{value} wheel{'s' if value != 1 else ''}"
    n = int(value)
    m10, m100 = n % 10, n % 100
    word = "коло" if m10 == 1 and m100 != 11 else ("кола" if 2 <= m10 <= 4 and not 12 <= m100 <= 14 else "кіл")
    return f"{value} {word}"


def _translated_date(value: str) -> str:
    months = I18N["ru"]["months"]
    match = re.fullmatch(r"(\d{1,2}) (" + "|".join(months) + r")( \d{4})?", value)
    if not match or lang() == "ru":
        return value
    month = I18N[lang()]["months"][months.index(match.group(2))]
    return f"{match.group(1)} {month}{match.group(3) or ''}"


def authored_value(value):
    if not isinstance(value, str) or lang() == "ru":
        return value
    if value.startswith("Сохранение от "):
        return t("saved_on", date=_translated_date(value[len("Сохранение от "):]))
    if value == "Сюжет пройден":
        return common_ui("story_completed")
    substitutions = (
        (r"^Уровень (.+)$", "level_value", "value"),
        (r"^ур\. (.+)$", "gear_level", "value"),
        (r"^(\d[\d ]*) карт$", "cards", "n"),
        (r"^(\d[\d ]*) пройдено$", "completed_count", "n"),
    )
    for pattern, key, name in substitutions:
        match = re.fullmatch(pattern, value)
        if match:
            return t(key, **{name: match.group(1)})
    match = re.fullmatch(r"этап (.+) из (.+)", value)
    if match:
        return t("story_stage", n=match.group(1), total=match.group(2))
    match = re.fullmatch(r"(?:(\d+) ч )?(\d+) мин", value)
    if match:
        return t("hours_minutes", h=match.group(1), m=match.group(2)) if match.group(1) else t("minutes", m=match.group(2))
    return value


def translate_card(card):
    """Return a localized copy of cached hub data without touching game text."""
    result = copy.deepcopy(card)
    block = result.get("block") or {}
    if block.get("kicker") in _KICKERS:
        block["kicker"] = t(_KICKERS[block["kicker"]])
    if block.get("detail"):
        block["detail"] = authored_value(block["detail"])
    for fact in result.get("facts") or []:
        fact["label"] = authored_label(fact.get("label"))
        fact["value"] = authored_value(fact.get("value"))
    return result
