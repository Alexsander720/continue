// Тексты EN/UK/RU, проверенные снимки сохранений для демо, донаты.
// Имя проекта и автор меняются в одном месте — BRAND / AUTHOR.
const BRAND = "Continue?";
const AUTHOR = { name: "Doctor_Nerd", steam: "https://steamcommunity.com/profiles/76561198038135489", github: "https://github.com/Alexsander720" };   // подпись — ник Steam (решение автора 08.10)

const DONATE = {
  mono: "https://send.monobank.ua/jar/3zsHTXdRbt",
  mono_card: "4874 1000 3320 3608",
  paypal: "apogulay@gmail.com",
  usdt_trc20: "TKhmtVEnuU5w73YMPT8adh7t3VZKJUUxmC",
  usdt_bep20: "0xDC0c682922bF3194693774743fBB3fd20E7754c3",
  discord: "",
  repo: "https://github.com/Alexsander720/continue",
};

const LANGS = ["en", "uk", "ru"];

// Демо: проверенные снимки сохранений автора и сообщества. Источник подписан у каждой новой игры. Значения — из разборов (ddsaves / gowsave), названия — из файлов самих игр.
// Если проверенного названия на языке сайта нет, сохраняем язык источника и подписываем его.
const GAMES = [
  {
    id: "2322010", name: "God of War Ragnarök", accent: "#e0a07a", bg: "rec",
    en: { kicker: "Where you left off", title: "Vanaheim — The Jungle", sub: "Go to Muspelheim",
          detail: "The animal from Freyr’s Camp, Helka, is tracking a scent. She seems to want us to follow." },
    ru: { kicker: "Где остановился", title: "Ванахейм — Джунгли", sub: "Отправиться в Муспельхейм",
          detail: "Хелька, зверюга из лагеря Фрейра, взяла какой-то след. Она хочет, чтобы мы по нему пошли." },
    uk: { kicker: "Де зупинився" },
    facts: [
      { icon: "ravens.png", l: { en: "Odin’s Ravens", uk: "Ворони Одіна", ru: "Вороны Одина" }, value: "28 / 48" },
      { glyph: "coins", l: { en: "Hacksilver", uk: "Срібло", ru: "Серебро" }, value: { en: "95,919", uk: "95 919", ru: "95 919" } },
      { icon: "progress.png", l: { en: "Progress", uk: "Прогрес", ru: "Прогресс" }, value: { en: "Level 6", uk: "Рівень 6", ru: "Уровень 6" } },
    ],
  },
  {
    id: "2172010", name: "Until Dawn", accent: "#d9b77a", bg: "trailer",
    en: { kicker: "Where you left off", title: "MEMENTO MORI" },
    ru: { kicker: "Где остановился", title: "ПОМНИ О СМЕРТИ" },
    uk: { kicker: "Де зупинився" },
    facts: [
      { icon: "totems.png", l: { en: "Totems", uk: "Тотеми", ru: "Тотемы" }, value: "1 / 36" },
      { icon: "clues.png", l: { en: "Clues", uk: "Докази", ru: "Улики" }, value: "0 / 79" },
      { icon: "butterfly.png", l: { en: "Butterfly effects", uk: "Ефекти метелика", ru: "Эффекты бабочки" }, value: "2 / 22" },
      { icon: "achievements.png", l: { en: "Achievements", uk: "Досягнення", ru: "Достижения" }, value: "1 / 29" },
    ],
    people: { l: { en: "Alive now", uk: "Живі зараз", ru: "Живы сейчас" }, value: "8 / 8", list: [
      ["chris", "Chris", "Крис"], ["ashley", "Ashley", "Эшли"], ["emily", "Emily", "Эмили"], ["matt", "Matt", "Мэтт"],
      ["mike", "Mike", "Майк"], ["jessica", "Jessica", "Джессика"], ["sam", "Sam", "Сэм"], ["josh", "Josh", "Джош"],
    ] },
  },
  {
    id: "367520", name: "Hollow Knight", accent: "#7adfe0", bg: "trailer",
    en: { kicker: "Where you left off", title: "Dirtmouth" },
    ru: { kicker: "Где остановился", title: "Грязьмут" },
    uk: { kicker: "Де зупинився" },
    facts: [
      { icon: "masks.png", l: { en: "Masks", uk: "Маски", ru: "Маски" }, value: "5" },
      { icon: "nail.png", l: { en: "Nail", uk: "Цвях", ru: "Гвоздь" }, value: { en: "Old Nail (5)", ru: "Старый гвоздь (5)" } },
      { icon: "geo.png", l: { en: "Geo", uk: "Гео", ru: "Гео" }, value: "46" },
      { icon: "time.png", l: { en: "In this save", uk: "У цьому збереженні", ru: "В этом сейве" }, value: { en: "9 min", uk: "9 хв", ru: "9 мин" } },
    ],
  },
  {
    id: "1092790", name: "Inscryption", accent: "#e0a25a", bg: "trailer",
    en: { kicker: "Has a save" }, uk: { kicker: "Є збереження" }, ru: { kicker: "Есть сохранение" },
    facts: [
      { icon: "achievements.png", l: { en: "Achievements", uk: "Досягнення", ru: "Достижения" }, value: "29 / 40 · 73%" },
      { icon: "deck.png", l: { en: "Deck", uk: "Колода", ru: "Колода" }, value: { en: "14 cards", uk: "14 карт", ru: "14 карт" } },
      { icon: "teeth.png", l: { en: "Teeth", uk: "Зуби", ru: "Зубы" }, value: "22" },
      { icon: "lives.png", l: { en: "Lives", uk: "Життя", ru: "Жизни" }, value: "2 / 2" },
      { icon: "maxdamage.png", l: { en: "Max damage in 1 turn", uk: "Макс. шкода за 1 хід", ru: "Макс. урон за 1 ход" }, value: "12" },
    ],
  },
  {
    id: "1809540", name: "Nine Sols", accent: "#e09a8c", bg: "trailer",
    en: { kicker: "Where you left off", title: "Peach Blossom Village" },
    uk: { kicker: "Де зупинився", title: "Персиковий Цвіт" },
    ru: { kicker: "Где остановился", title: "Персиковая Деревня" },
    facts: [
      { icon: "seals.png", l: { en: "Sol Seals", uk: "Печатки Солів", ru: "Печати Солов" }, value: "0 / 8" },
      { icon: "level.png", l: { en: "Level", uk: "Рівень", ru: "Уровень" }, value: "1" },
      { icon: "skills.png", l: { en: "Skills", uk: "Навички", ru: "Навыки" }, value: "6" },
      { icon: "encyclopedia.png", l: { en: "Encyclopedia", uk: "Енциклопедія", ru: "Энциклопедия" }, value: "5 / 104" },
      { icon: "time.png", l: { en: "In this save", uk: "У цьому збереженні", ru: "В этом сейве" }, value: { en: "2 min", uk: "2 хв", ru: "2 мин" } },
    ],
  },
  {
    id: "2129530", name: "REANIMAL", accent: "#88b9d2", bg: "trailer",
    en: { kicker: "Where you left off", title: "Dead in the Water" },
    ru: { kicker: "Где остановился", title: "Мертвый штиль" },
    uk: { kicker: "Де зупинився" },
    facts: [
      { icon: "chapter.png", l: { en: "Chapter", uk: "Розділ", ru: "Глава" }, value: "1 / 9" },
      { icon: "finds.png", l: { en: "Finds", uk: "Знахідки", ru: "Находки" }, value: "3 / 41" },
      { icon: "masks.png", l: { en: "Masks", uk: "Маски", ru: "Маски" }, value: "3 / 21" },
      { icon: "posters.png", l: { en: "Posters", uk: "Плакати", ru: "Плакаты" }, value: "0 / 20" },
      { icon: "time.png", l: { en: "In this save", uk: "У цьому збереженні", ru: "В этом сейве" }, value: { en: "12 min", uk: "12 хв", ru: "12 мин" } },
    ],
  },
  {
    id: "532210", name: "Life is Strange 2", accent: "#e0a088", bg: "trailer",
    en: { kicker: "Where you left off", title: "Wolves" },
    ru: { kicker: "Где остановился", title: "Волки" },
    uk: { kicker: "Де зупинився" },
    facts: [
      { icon: "episode.png", l: { en: "Episode", uk: "Епізод", ru: "Эпизод" }, value: "5 / 5" },
      { icon: "souvenirs.png", l: { en: "Souvenirs", uk: "Сувеніри", ru: "Сувениры" }, value: "10 / 30" },
      { icon: "journal.png", l: { en: "Journal pages", uk: "Сторінки щоденника", ru: "Страницы дневника" }, value: "98" },
      { icon: "brotherhood.png", l: { en: "Brotherhood", uk: "Братерство", ru: "Отношения братьев" }, value: "+31" },
      { icon: "morality.png", l: { en: "Daniel’s morality", uk: "Мораль Деніела", ru: "Мораль Даниэля" }, value: "−14" },
    ],
  },
  {
    "id": "2531310",
    "name": "The Last of Us Part II Remastered",
    "accent": "#a9b890",
    "bg": "publisher",
    "facts": [
      {
        "glyph": "finds",
        "l": {
          "en": "Collectibles",
          "uk": "Знахідки",
          "ru": "Находки"
        },
        "value": "80"
      },
      {
        "glyph": "time",
        "l": {
          "en": "In this save",
          "uk": "У цьому збереженні",
          "ru": "В этом сейве"
        },
        "value": "11:22"
      }
    ],
    "snapshot": {
      "kind": "owner",
      "date": "2026-09-22"
    },
    "en": {
      "kicker": "Where you left off"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился",
      "title": "Сиэтл, день 2 - Найденные струны"
    },
    "sourceLanguage": "ru"
  },
  {
    "id": "990080",
    "name": "Hogwarts Legacy",
    "accent": "#c7ad72",
    "bg": "publisher",
    "facts": [
      {
        "glyph": "level",
        "l": {
          "en": "Level",
          "uk": "Рівень",
          "ru": "Уровень"
        },
        "value": "5"
      },
      {
        "glyph": "finds",
        "l": {
          "en": "Merlin Trials",
          "uk": "Випробування Мерліна",
          "ru": "Испытания Мерлина"
        },
        "value": "0 / 95"
      },
      {
        "glyph": "book",
        "l": {
          "en": "Collections",
          "uk": "Колекції",
          "ru": "Коллекции"
        },
        "value": "45"
      },
      {
        "glyph": "coins",
        "l": {
          "en": "Gold",
          "uk": "Золото",
          "ru": "Золото"
        },
        "value": "548"
      }
    ],
    "snapshot": {
      "kind": "owner",
      "date": "2026-10-04"
    },
    "en": {
      "kicker": "Where you left off",
      "title": "Transfiguration Courtyard",
      "sub": "Gryffindor"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился",
      "title": "Двор трансфигурации",
      "sub": "Гриффиндор"
    }
  },
  {
    "id": "646570",
    "name": "Slay the Spire",
    "accent": "#c08e71",
    "bg": "trailer",
    "facts": [
      {
        "glyph": "level",
        "l": {
          "en": "Floor",
          "uk": "Поверх",
          "ru": "Этаж"
        },
        "value": "11"
      },
      {
        "glyph": "heart",
        "l": {
          "en": "HP",
          "uk": "HP",
          "ru": "HP"
        },
        "value": "36 / 80"
      },
      {
        "glyph": "cards",
        "l": {
          "en": "Deck",
          "uk": "Колода",
          "ru": "Колода"
        },
        "value": "15"
      },
      {
        "glyph": "relic",
        "l": {
          "en": "Relics",
          "uk": "Реліквії",
          "ru": "Реликвии"
        },
        "value": "3"
      },
      {
        "glyph": "coins",
        "l": {
          "en": "Gold",
          "uk": "Золото",
          "ru": "Золото"
        },
        "value": "120"
      }
    ],
    "snapshot": {
      "kind": "owner",
      "date": "2026-10-04"
    },
    "en": {
      "kicker": "Where you left off",
      "title": "Exordium",
      "sub": "The Ironclad"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился",
      "title": "Преддверие",
      "sub": "Латоносец"
    }
  },
  {
    "id": "2420110",
    "name": "Horizon Forbidden West",
    "accent": "#b19c83",
    "bg": "art",
    "facts": [
      {
        "glyph": "level",
        "l": {
          "en": "Level",
          "uk": "Рівень",
          "ru": "Уровень"
        },
        "value": "1"
      },
      {
        "glyph": "time",
        "l": {
          "en": "In this save",
          "uk": "У цьому збереженні",
          "ru": "В этом сейве"
        },
        "value": "00:15:18"
      }
    ],
    "snapshot": {
      "kind": "owner",
      "date": "2026-10-04"
    },
    "en": {
      "kicker": "Where you left off"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился",
      "title": "Дотянуться до звёзд"
    },
    "sourceLanguage": "ru"
  },
  {
    "id": "524220",
    "name": "NieR:Automata",
    "accent": "#c4beaa",
    "bg": "art",
    "facts": [],
    "snapshot": {
      "kind": "owner",
      "date": "2026-10-04"
    },
    "en": {
      "kicker": "Where you left off",
      "title": "Prologue"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился"
    }
  },
  {
    "id": "1874000",
    "name": "Life is Strange: Double Exposure",
    "accent": "#ceaa94",
    "bg": "art",
    "facts": [
      {
        "glyph": "book",
        "l": {
          "en": "Episode",
          "uk": "Епізод",
          "ru": "Эпизод"
        },
        "value": "1 / 5"
      },
      {
        "glyph": "camera",
        "l": {
          "en": "Album photos",
          "uk": "Фото в альбомі",
          "ru": "Фото в альбоме"
        },
        "value": "0"
      }
    ],
    "snapshot": {
      "kind": "owner",
      "date": "2026-10-04"
    },
    "en": {
      "kicker": "Where you left off",
      "title": "Still Life",
      "sub": "Out of the Gutter"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился",
      "title": "Натюрморт",
      "sub": "Нарушать — так вместе"
    }
  },
  {
    "id": "391540",
    "name": "UNDERTALE",
    "accent": "#b2b9c3",
    "bg": "trailer",
    "facts": [
      {
        "glyph": "level",
        "l": {
          "en": "LV",
          "uk": "LV",
          "ru": "LV"
        },
        "value": "1"
      },
      {
        "glyph": "heart",
        "l": {
          "en": "Max HP",
          "uk": "Макс. HP",
          "ru": "Макс. HP"
        },
        "value": "20"
      },
      {
        "glyph": "coins",
        "l": {
          "en": "G",
          "uk": "G",
          "ru": "G"
        },
        "value": "0"
      },
      {
        "glyph": "time",
        "l": {
          "en": "In this save",
          "uk": "У цьому збереженні",
          "ru": "В этом сейве"
        },
        "value": { "en": "2 min 44 sec", "uk": "2 хв 44 с", "ru": "2 мин 44 с" }
      }
    ],
    "snapshot": {
      "kind": "owner",
      "date": "2026-10-03"
    },
    "en": {
      "kicker": "Where you left off",
      "title": "Ruins - Entrance"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился"
    }
  },
  {
    "id": "2651280",
    "name": "Marvel's Spider-Man 2",
    "accent": "#d68070",
    "bg": "publisher",
    "facts": [
      {
        "glyph": "level",
        "l": {
          "en": "Level",
          "uk": "Рівень",
          "ru": "Уровень"
        },
        "value": "54"
      },
      {
        "glyph": "book",
        "l": {
          "en": "Story missions",
          "uk": "Сюжетні місії",
          "ru": "Сюжетные миссии"
        },
        "value": "27 / 36"
      },
      {
        "glyph": "finds",
        "l": {
          "en": "Spider-Bots",
          "uk": "Павукоботи",
          "ru": "Паукоботы"
        },
        "value": "42 / 42"
      }
    ],
    "snapshot": {
      "kind": "community",
      "date": "2026-10-03",
      "author": "MessyCelia",
      "url": "https://www.playground.ru/marvels_spiderman_2/cheat/marvels_spider_man_2_sohranenie_pered_missiej_s_venomom-1766985"
    },
    "en": {
      "kicker": "Where you left off"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился",
      "title": "Не пугайся"
    },
    "sourceLanguage": "ru"
  },
  {
    "id": "2124490",
    "name": "SILENT HILL 2",
    "accent": "#8f9e96",
    "bg": "publisher",
    "facts": [
      {
        "glyph": "book",
        "l": {
          "en": "Memos",
          "uk": "Записки",
          "ru": "Записки"
        },
        "value": "12"
      },
      {
        "glyph": "map",
        "l": {
          "en": "Maps",
          "uk": "Мапи",
          "ru": "Карты"
        },
        "value": "6"
      },
      {
        "glyph": "ammo",
        "l": {
          "en": "Handgun ammo · reserve",
          "uk": "Патрони пістолета · запас",
          "ru": "Патроны пистолета · запас"
        },
        "value": "6"
      }
    ],
    "snapshot": {
      "kind": "community",
      "date": "2026-10-02",
      "author": "FallenGhost",
      "url": "https://www.playground.ru/silent_hill_2/cheat/silent_hill_2_remake_poetapnye_sohraneniya_bez_smertej_tri_kontsovki-1728316"
    },
    "en": {
      "kicker": "Has a save"
    },
    "uk": {
      "kicker": "Є збереження"
    },
    "ru": {
      "kicker": "Есть сохранение"
    }
  },
  {
    "id": "1903340",
    "name": "Clair Obscur: Expedition 33",
    "accent": "#c8a582",
    "bg": "publisher",
    "facts": [
      {
        "glyph": "book",
        "l": {
          "en": "Story stage",
          "uk": "Етап сюжету",
          "ru": "Этап сюжета"
        },
        "value": "7 / 17"
      },
      {
        "glyph": "time",
        "l": {
          "en": "In this save",
          "uk": "У цьому збереженні",
          "ru": "В этом сейве"
        },
        "value": "09:36"
      }
    ],
    "snapshot": {
      "kind": "community",
      "date": "2026-10-03",
      "author": "platapoop",
      "url": "https://steamcommunity.com/app/1903340/discussions/0/592895838866379576/#c592895838866380326"
    },
    "en": {
      "kicker": "Where you left off"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился",
      "title": "Скрытая жестральская арена"
    },
    "sourceLanguage": "ru"
  },
  {
    "id": "424840",
    "name": "Little Nightmares",
    "accent": "#baaa79",
    "bg": "trailer",
    "facts": [
      {
        "glyph": "finds",
        "l": {
          "en": "Nomes",
          "uk": "Номи",
          "ru": "Номы"
        },
        "value": "13 / 13"
      },
      {
        "glyph": "relic",
        "l": {
          "en": "Statues",
          "uk": "Статуетки",
          "ru": "Статуэтки"
        },
        "value": "10 / 10"
      },
      {
        "glyph": "finds",
        "l": {
          "en": "DLC collectibles",
          "uk": "Предмети DLC",
          "ru": "Предметы DLC"
        },
        "value": "5 / 15"
      }
    ],
    "snapshot": {
      "kind": "community",
      "date": "2026-10-03",
      "author": "FANIS WEST",
      "url": "https://www.playground.ru/little_nightmares/cheat/little_nightmares_secrets_of_the_maw_chapter_1_sohranenie_savegame_sobrany_vse_kollektsionnye_predmety-825334"
    },
    "en": {
      "kicker": "Where you left off",
      "title": "The Depths"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился",
      "title": "Глубины"
    }
  },
  {
    "id": "860510",
    "name": "Little Nightmares II",
    "accent": "#9bafc1",
    "bg": "publisher",
    "facts": [
      {
        "glyph": "time",
        "l": {
          "en": "In this save",
          "uk": "У цьому збереженні",
          "ru": "В этом сейве"
        },
        "value": "11:10"
      }
    ],
    "snapshot": {
      "kind": "community",
      "date": "2026-10-03",
      "author": "Вячеслав Рачков",
      "url": "https://www.playground.ru/little_nightmares_2/cheat/little_nightmares_ii_poshagovye_sohraneniya_bez_dopolnenij-1876715"
    },
    "en": {
      "kicker": "Where you left off",
      "title": "School"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился",
      "title": "Школа"
    }
  },
  {
    "id": "1426210",
    "name": "It Takes Two",
    "accent": "#c5a978",
    "bg": "publisher",
    "facts": [
      {
        "glyph": "book",
        "l": {
          "en": "Chapter",
          "uk": "Розділ",
          "ru": "Глава"
        },
        "value": "3 / 7"
      },
      {
        "glyph": "cards",
        "l": {
          "en": "Minigames unlocked",
          "uk": "Відкриті мініігри",
          "ru": "Открытые мини-игры"
        },
        "value": "5 / 25"
      }
    ],
    "snapshot": {
      "kind": "community",
      "date": "2026-10-03",
      "author": "shurik-777_94",
      "url": "https://www.playground.ru/it_takes_two/cheat/it_takes_two_sohranenie_savegame_projdeno_3_glavy-1102742"
    },
    "en": {
      "kicker": "Where you left off",
      "title": "Spaced Out",
      "sub": "Rose's Room"
    },
    "uk": {
      "kicker": "Де зупинився"
    },
    "ru": {
      "kicker": "Где остановился",
      "title": "На млечном пути",
      "sub": "Комната Роуз"
    }
  }
];

// Название локации Nine Sols на 13 языках — прямо из I2 Localization игры (MinimapTitle/A0_S1_intro_morning)
const LOCALES = [
  ["EN", "Peach Blossom Village"], ["UK", "Персиковий Цвіт"], ["RU", "Персиковая Деревня"], ["DE", "Pfirsichblütendorf"],
  ["FR", "Village des Pêchers en Fleurs"], ["ES", "Flor de Melocotón"], ["IT", "Villaggio dei Fiori di pesco"],
  ["PL", "Wioska Kwiatu Brzoskwini"], ["PT-BR", "Vila Flor de Pêssego"], ["JA", "桃花村"], ["KO", "도화촌"], ["ZH", "桃花村"],
];

// Каталог публичной альфы 0.1.0. Поля соответствуют committed golden-эталонам.
const CATALOG = [
  { id: "108710", name: "Alan Wake", status: "proven", cover: false, f: ["place", "chapter", "facts"] },
  { id: "1903340", name: "Clair Obscur: Expedition 33", status: "proven", f: ["place", "chapter", "objective", "facts"] },
  { id: "2322010", name: "God of War Ragnarök", status: "proven", f: ["facts", "rec"] },
  { id: "990080", name: "Hogwarts Legacy", status: "pc", reason: "PC only: Oodle saves require native ooz, absent from Decky Python", f: ["deck_unavailable"] },
  { id: "367520", name: "Hollow Knight", status: "proven", f: ["place", "facts", "icons"] },
  { id: "2420110", name: "Horizon Forbidden West", status: "proven", f: ["place", "chapter", "facts"] },
  { id: "1092790", name: "Inscryption", status: "proven", f: ["facts", "icons"] },
  { id: "1426210", name: "It Takes Two", status: "proven", f: ["place", "chapter", "facts"] },
  { id: "532210", name: "Life is Strange 2", status: "proven", f: ["place", "facts", "icons"] },
  { id: "1874000", name: "Life is Strange: Double Exposure", status: "proven", f: ["place", "chapter", "facts"] },
  { id: "424840", name: "Little Nightmares", status: "proven", f: ["place", "chapter", "facts"] },
  { id: "860510", name: "Little Nightmares II", status: "proven", f: ["place", "chapter", "facts"] },
  { id: "2651280", name: "Marvel's Spider-Man 2", status: "proven", f: ["place", "chapter", "objective", "facts"] },
  { id: "524220", name: "NieR:Automata", status: "proven", f: ["place", "chapter", "facts"] },
  { id: "1809540", name: "Nine Sols", status: "proven", f: ["place", "facts", "icons", "uk"] },
  { id: "2129530", name: "REANIMAL", status: "proven", f: ["place", "chapter", "facts", "icons"] },
  { id: "2124490", name: "SILENT HILL 2", status: "proven", f: ["place", "facts"] },
  { id: "646570", name: "Slay the Spire", status: "proven", f: ["place", "facts", "icons"] },
  { id: "2531310", name: "The Last of Us Part II Remastered", status: "proven", f: ["facts"] },
  { id: "391540", name: "UNDERTALE", status: "proven", f: ["place", "facts"] },
  { id: "1659420", name: "Uncharted: Legacy of Thieves Collection", status: "proven", cover: false, f: ["chapter", "facts"] },
  { id: "2172010", name: "Until Dawn", status: "proven", f: ["place", "chapter", "facts", "icons", "people"] },
];

const PRESETS = {
  lite:     { video: "720p · CRF 25", disk: "1 / 2 / 4 / 8 GB", scope: { en: "per-game source", uk: "джерело для гри", ru: "источник для игры" }, power: { en: "game page on AC; Home off", uk: "сторінка від мережі; головна вимкнена", ru: "страница от сети; главная выключена" } },
  balanced: { video: "720p · CRF 23", disk: "1 / 2 / 4 / 8 GB", scope: { en: "per-game source", uk: "джерело для гри", ru: "источник для игры" }, power: { en: "on AC; still on battery", uk: "від мережі; кадр від батареї", ru: "от сети; кадр от батареи" } },
  max:      { video: "1080p · CRF 21", disk: "1 / 2 / 4 / 8 GB", scope: { en: "per-game source", uk: "джерело для гри", ru: "источник для игры" }, power: { en: "video everywhere", uk: "відео всюди", ru: "видео везде" } },
};

// Замер 06.10.2026 на Steam Deck OLED (release/deck_power_auto.py): вся Дека от батареи (ток × напряжение),
// среднее за 45 с после 8 с успокоения, яркость 13 %, Wi-Fi вкл. Часы — сколько продержится батарея 50 Вт·ч на этом экране.
const POWER = [
  { k: "pw.r1", w: 4.93 },
  { k: "pw.r2", w: 6.46, d: "+1.5" , bad: true },
  { k: "pw.r3", w: 7.69 },
  { k: "pw.r4", w: 8.07, d: "+0.4" },
];

const AGENTS = {
  claude: '$ claude "Read AGENTS.md and add Nine Sols to Continue?"',
  codex:  '$ codex "Follow AGENTS.md: add Nine Sols to Continue?"',
  gemini: '$ gemini -p "Use AGENTS.md to add Nine Sols to Continue?"',
};
const TERM = {
  en: [
    ["dim", "● Looking for the save…"], ["ok", "  found  steamapps/compatdata/1809540/…/Saves/save_1"],
    ["dim", "● Comparing 5 save stages…"], ["ok", "  level, seals, jades grow · deaths 0 → 201"],
    ["warn", "  fields that never change → unproven, not shown"],
    ["dim", "● Building name tables from the game's own files…"], ["ok", "  113 scenes · 48 teleport nodes · 30 jades · 8 seals"],
    ["dim", "● Running the gate…"], ["pass", "  PASS  every fact proven · 0 invented names"],
    ["done", "✓ games/nine_sols is ready — open a pull request"],
  ],
  uk: [
    ["dim", "● Шукаю збереження…"], ["ok", "  знайшов  steamapps/compatdata/1809540/…/Saves/save_1"],
    ["dim", "● Порівнюю 5 етапів сейву…"], ["ok", "  рівень, печатки, нефрити ростуть · смерті 0 → 201"],
    ["warn", "  поля, що не змінюються → не доведено, не показуємо"],
    ["dim", "● Будую таблиці назв із файлів самої гри…"], ["ok", "  113 сцен · 48 вузлів телепорту · 30 нефритів · 8 печаток"],
    ["dim", "● Запускаю перевірку (gate)…"], ["pass", "  PASS  кожен факт доведено · 0 вигаданих назв"],
    ["done", "✓ games/nine_sols готова — відкривай pull request"],
  ],
  ru: [
    ["dim", "● Ищу сохранение…"], ["ok", "  нашёл  steamapps/compatdata/1809540/…/Saves/save_1"],
    ["dim", "● Сравниваю 5 этапов сейва…"], ["ok", "  уровень, печати, нефриты растут · смерти 0 → 201"],
    ["warn", "  поля, которые не меняются → не доказано, не показываем"],
    ["dim", "● Строю таблицы названий из файлов самой игры…"], ["ok", "  113 сцен · 48 узлов телепорта · 30 нефритов · 8 печатей"],
    ["dim", "● Запускаю проверку (gate)…"], ["pass", "  PASS  каждый факт доказан · 0 выдуманных названий"],
    ["done", "✓ games/nine_sols готова — открывай pull request"],
  ],
};

const STR = {
  en: {
    "demo.source.owner": "Author’s save · demo snapshot",
    "demo.source.community": "Community save · demo snapshot",
    "demo.sourceLanguage": "Names remain in the verified source language ({lang}).",
    "demo.bg.publisher": "Background: a publisher trailer",
    "demo.bg.art": "Background: game artwork",
    "ft.chapter": "saved chapter / quest",
    "nav.open": "Open navigation",
    "nav.close": "Close navigation",
    "cat.search": "Find your game",
    "cat.clear": "Clear search",
    "cat.filter": "Filter games by proof status",
    "cat.all": "All games",
    "cat.results": "Showing {n} of {total} games",
    "cat.demo": "Explore demo",
    "cat.empty": "No matching games.",
    "cat.empty.p": "Try a shorter name or another filter. You can also request a game below.",
    "ag.example": "Example of the contribution workflow described in AGENTS.md.",
    "in.preview": "Public alpha 0.1.0 is available as a Decky ZIP for Steam Deck testers. PC and Big Picture support comes later.",
    "hero.preview": "Public Steam Deck alpha · 0.1.0",
    "demo.device": "Choose a device", "demo.previous": "Previous game", "demo.next": "Next game",
    "demo.expand": "Enlarge screen", "demo.dialog": "Explore the demo", "demo.close": "Close demo",
    "demo.pause": "Pause background", "demo.resume": "Play background",
    "demo.pan": "Swipe across the screen to see the details.",
    "hero.tour": "Watch the 40-second tour",
    "in.guide": "Full guide →", "in.guide2": "Full guide: what changes and how to remove →",
    "in.c1": "One empty file turns on Steam's own local debugging switch — nothing inside Steam is modified.",
    "in.c2": "A small helper starts at sign-in, without a window, and adds the interface in memory.",
    "in.c3": "Saves are only read. Games and their processes are never touched.",
    "pw.hours": "h",
    "nav.games": "Games",
    "cat.kicker": "Supported games", "cat.h2": "Games that already know where you stopped.",
    "cat.p": "The public alpha ships these 22 readers. Demo cards are fixed snapshots; reader fields are locked by EN/UK/RU golden tests whenever a research fixture is available.",
    "cat.pc": "PC only · unavailable on Deck", "ft.deck_unavailable": "Oodle saves require native ooz; Decky Python has no decoder", "cat.proven": "golden-checked", "cat.check": "fixture unavailable",
    "ft.place": "where you left off", "ft.objective": "current objective", "ft.facts": "facts", "ft.icons": "icons",
    "ft.people": "who is alive", "ft.rec": "your gameplay", "ft.uk": "Ukrainian names",
    "cat.more": "Want your game here? Ask for it or add it yourself.", "cat.req": "Request a game", "cat.add": "Add it with your AI agent",
    "nav.demo": "Demo", "nav.features": "Features", "nav.battery": "Battery", "nav.agents": "Add your game", "nav.install": "Install", "nav.support": "Support",
    "hero.tag": "public alpha for Steam Deck",
    "hero.h1": "Your games remember<br>where you left off.",
    "hero.lead": "Your chapter, current objective and collected items — from your real save, right inside Steam. With your own gameplay in the background.",
    "hero.cta1": "Try the demo", "hero.cta2": "Release details →", "hero.cta3": "Support",
    "hero.meta": "Free · open source · reads your saves offline",
    "hero.press": "PRESS START",
    "demo.h2": "These are real saves.",
    "demo.p": "{n} games with real save snapshots from the author and the community. Only verified fields are shown; names come from game files or the save itself.",
    "demo.keys": "← → · covers · gamepad",
    "demo.music.on": "Music on", "demo.music.off": "Music off",
    "demo.toast": "On your Deck this button launches the game.",
    "demo.proven": "Verified fields", "demo.proven.t": "The fields shown were checked against real save stages and game data. This is a demo snapshot, not live progress.",
    "demo.bg.rec": "Background: the author's own gameplay, recorded by Steam",
    "demo.bg.trailer": "Background: a gameplay cut from the store trailer",
    "demo.nolang": "This game has no Ukrainian, so names stay in English — exactly like in the game.",
    "s.play": "Play", "s.last": "Last played", "s.played": "Played", "s.story": "Story", "s.full": "100%", "s.h": "h",
    "rec.kicker": "Your gameplay", "rec.h2": "The background can be you.",
    "rec.p": "Steam already records your play in the background. Continue? cuts a clean piece of <b>your own</b> gameplay — no menus, no loading screens, no pause screen — and loops it behind the logo. God of War and TEKKEN here are the author's real sessions.",
    "rec.n1": "Picks moments with action, skips menus and loading screens automatically.",
    "rec.n2": "No recording yet? The best gameplay cut of the store trailer is used instead.",
    "rec.n3": "Per game you choose: a Steam trailer, a local recording, a consent-gated YouTube trailer, or artwork.",
    "rec.note": "Local gameplay needs Steam Game Recording in background mode and a suitable recording on this Deck.",
    "rec.you": "your gameplay",
    "feat.h2": "Made to make you want to play.",
    "feat.p": "Remember the title screens of childhood — music, motion, a promise of adventure? That feeling, for every game in your library.",
    "f1.t": "Where you left off", "f1.p": "Decoded straight from the save file, offline, on the Deck itself: chapter, location — and, when the game keeps it, the text of your current objective.",
    "f2.t": "Facts that matter", "f2.p": "Totems found, charms equipped, who's still alive. Every fact gets its own quiet white icon.",
    "f3.t": "A living home screen", "f3.p": "The selected game breathes on the Steam home screen too: its gameplay, its logo, its music.",
    "f4.t": "Deck alpha now, PC later", "f4.p": "Version 0.1.0 is a self-contained Decky plugin. A tested Windows and Big Picture package is later roadmap work.",
    "f5.t": "Three real presets", "f5.p": "Light and Balanced cap video at 720p; Maximum uses up to 1080p. Choose a separate 1, 2, 4, or 8 GB cache budget.",
    "f6.t": "In your language", "f6.p": "Names come from the game's own files, in the language your Steam speaks. This is a real Nine Sols string — it starts in your language:",
    "chips.h": "And the small things",
    "c1": "Story & 100% time (HowLongToBeat) in the Play row", "c2": "ProtonDB rating on covers and the game page",
    "c3": "Per-game background source", "c4": "Sanitized developer-report preview and ZIP",
    "c5": "Achievements X / Y read locally — no web API, no public profile", "c6": "Installed games first on the home screen",
    "c7": "SteamGridDB logos and 4K artwork", "c8": "Non-Steam shortcuts get trailers and art too",
    "c9": "Game description from the Steam store, in your language", "c10": "1 / 2 / 4 / 8 GB bounded cache",
    "c11": "Consent-gated theme music", "c12": "Everything switches on and off in the ⋯ menu", "c13": "Release ZIP updates require a matching SHA-256",
    "dev.deck": "Steam Deck alpha", "dev.pc": "PC mockup · later",
    "p.lite": "Lite", "p.balanced": "Balanced", "p.max": "Max",
    "p.video": "Live background", "p.disk": "Selectable cache", "p.scope": "Background choice", "p.power": "Playback policy",
    "pw.kicker": "Battery", "pw.h2": "Measured, not guessed.",
    "pw.p": "A handheld lives on its battery, so we measure. A real Steam Deck OLED on battery: the whole device (screen, Wi-Fi, sound), averaged over 45 seconds, brightness 13%. Hours = how long a full 50 Wh battery lasts on that screen.",
    "pw.r1": "Game page, still picture", "pw.r2": "Game page, live background 1080p + music",
    "pw.r3": "Steam home, without our video", "pw.r4": "Steam home, live background + music",
    "pw.why": "The measured difference is about 1.5 W on the game page — about two hours of a full battery when staying on that screen. The home video adds 0.4 W in this test, and music made no measurable difference. Alpha 0.1.0 therefore defaults to Light: still on battery and no Home video.",
    "pw.m.h": "Battery behavior in 0.1.0",
    "pw.m1": "<b>Light</b> — up to 720p, game-page video only on AC, no Home video, still frame on battery.",
    "pw.m2": "<b>Balanced</b> — up to 720p, game page and Home animate on AC, still frame on battery.",
    "pw.m3": "<b>Maximum</b> — up to 1080p and video everywhere, including on battery.",
    "pw.honest": "Measured on the author’s Steam Deck OLED on 6 Oct 2026 using an automatic test. The time estimates apply to the displayed screen under these test conditions.",
    "pw.unit": "W",
    "ag.kicker": "Community", "ag.h2": "Bring your favourite game — with your AI agent.",
    "ag.p": "Every game in Continue? is decoded by someone who loves it. Point Claude Code, Codex or Gemini at <code>AGENTS.md</code>: it finds the save, compares save stages, pulls names from the game files and runs the gate. You review, open a pull request — and everyone gets your game.",
    "ag.r1": "<b>Only proven facts.</b> A field counts only if it changes between save stages.",
    "ag.r2": "<b>Names only from the game's files.</b> Never from memory or a wiki.",
    "ag.r3": "<b>Golden regression tests exist now.</b> Baselines change only through an explicit update command.",
    "ag.r4": "<b>Icons by prompt.</b> Ready-made prompts for ChatGPT or Gemini — white, flat, by reference.",
    "ag.cta1": "Read the guide", "ag.cta2": "Discord — soon",
    "pr.h": "Proven or it doesn't ship.",
    "pr.p": "Even the author's own early readers had fields that looked right and never moved. The gate now rejects them automatically. Real cases:",
    "pr.ok": "Nine Sols — deaths 0 → 201; level, seals and jades grow across 5 saves", "pr.okv": "proven",
    "pr.no1": "A counter that read 0 in every save", "pr.nov1": "rejected: never changes",
    "pr.no2": "Chapter names typed from memory", "pr.nov2": "rejected: not in the game files",
    "pr.no3": "“Grubs x / 46” with the total from a wiki", "pr.nov3": "rejected: totals come from game data",
    "in.kicker": "Install", "in.h2": "Test the Deck alpha.", "in.soon": "alpha 0.1.0",
    "in.deck": "Steam Deck", "in.d1": "Install <b>Decky Loader</b>.", "in.d2": "Open <b>Decky → Settings → Developer → Install from URL/ZIP</b> and select the release ZIP.", "in.d3": "Confirm Continue? 0.1.0, then open a game.",
    "in.dopt": "Review the full install, failure-recovery, removal, and tester guides before reporting.",
    "in.pc": "PC · Big Picture", "in.p1": "Not included in 0.1.0.", "in.p2": "No Windows helper or tested setup is shipped.", "in.p3": "Follow the roadmap instead of old design notes.",
    "in.popt": "PC and Big Picture support comes later.",
    "up.t": "Checksum-gated Deck updates.", "up.p": "Continue? checks daily for a release ZIP plus matching SHA-256 and delegates installation to Decky. A failed check leaves the installed version working.",
    "cl.kicker": "What's new", "cl.preview": "public alpha",
    "cl.1v": "0.1.0 · October 2026", "cl.1": "<li>Installable self-contained Decky ZIP</li><li>22 public save readers with golden regression coverage</li><li>Live background on the game page and Steam Home</li>",
    "cl.2v": "Tester diagnostics", "cl.2": "<li>Review sanitized JSON before saving</li><li>Attach the generated ZIP to the alpha issue template</li>",
    "cl.3v": "Safe release flow", "cl.3": "<li>Updates require the release ZIP and matching SHA-256</li><li>Decky performs installation; the current build survives a failed check</li>",
    "faq.kicker": "Good to know", "faq.h2": "Notes and nuances.",
    "q1": "Where did Steam's button hints go?",
    "a1": "Continue? can hide Steam's bottom hint bar to give the game page more room. The buttons still do exactly what they did — only the reminders are gone. New to the Deck? Keep the hints on (one switch in the ⋯ menu) until the buttons are second nature.",
    "q2": "Can it break my saves?",
    "a2": "No. Saves are only ever read — copied, parsed, never written. Continue? doesn't touch game files or game processes either.",
    "q3": "Steam updated and something looks off.",
    "a3": "Continue? lives inside Steam's interface, and Valve changes it sometimes. The plugin re-attaches itself after an update; if a piece still goes missing, an update of Continue? follows. Every release lists the Steam version it was checked on.",
    "q4": "My game isn't supported. What do I get?",
    "a4": "Still a lot: live background, theme music, play time, achievements, HowLongToBeat and ProtonDB. “Where you left off” and the facts need a save reader — and you can add one with your AI agent.",
    "q5": "Does it need the internet?",
    "a5": "Reading saves is fully offline. Descriptions, trailers, HowLongToBeat and ProtonDB are fetched once and cached.",
    "q6": "Why isn't my language there?",
    "a6": "Game names come from the game itself: if a game ships your language, Continue? uses it; if not, it shows the game's English. The interface is translated by the community.",
    "sup.kicker": "Support", "sup.h2": "Free. Forever.",
    "sup.p": "Continue? costs nothing and never will. If it made you want to play again, you can help keep it going — every donation goes into development and the AI subscription that helps build it.",
    "sup.mono": "monobank jar", "sup.mono.p": "Cards from any country, Apple Pay, Google Pay.", "sup.mono.b": "Open the jar", "sup.card": "Jar card",
    "sup.pp": "PayPal", "sup.pp.p": "Send to this address — tap to copy.",
    "sup.cr": "Crypto · USDT", "sup.cr.p": "TRC20 (Tron) or BEP20 (BNB Smart Chain). Tap to copy, or scan.",
    "sup.soon": "coming soon", "sup.copied": "Copied", "sup.qr": "QR",
    "sup.deck": "Testing the alpha? Use Continue? → Collect a developer report, review it, then attach the ZIP to the alpha issue template.",
    "foot.made": "Made in Ukraine by", "foot.lic": "Code: GPL-3.0",
    "foot.legal": "Game names, logos, music and footage belong to their owners. Not affiliated with Valve.",
  },

  uk: {
    "demo.source.owner": "Сейв автора · знімок для демо",
    "demo.source.community": "Сейв спільноти · знімок для демо",
    "demo.sourceLanguage": "Назви залишаються мовою перевіреного джерела ({lang}).",
    "demo.bg.publisher": "Фон: трейлер видавця",
    "demo.bg.art": "Фон: ілюстрація гри",
    "ft.chapter": "розділ / завдання в сейві",
    "nav.open": "Відкрити меню",
    "nav.close": "Закрити меню",
    "cat.search": "Знайди свою гру",
    "cat.clear": "Очистити пошук",
    "cat.filter": "Фільтр ігор за статусом перевірки",
    "cat.all": "Усі ігри",
    "cat.results": "Показано {n} з {total} ігор",
    "cat.demo": "Роздивитися демо",
    "cat.empty": "Немає відповідних ігор.",
    "cat.empty.p": "Спробуй коротшу назву або інший фільтр. Свою гру можна попросити нижче.",
    "ag.example": "Приклад процесу додавання гри, описаного в AGENTS.md.",
    "in.preview": "Публічна альфа 0.1.0 доступна як Decky ZIP для тестування на Steam Deck. ПК і Big Picture — пізніше.",
    "hero.preview": "Публічна альфа для Steam Deck · 0.1.0",
    "demo.device": "Обери пристрій", "demo.previous": "Попередня гра", "demo.next": "Наступна гра",
    "demo.expand": "Збільшити екран", "demo.dialog": "Роздивись демо", "demo.close": "Закрити демо",
    "demo.pause": "Зупинити фон", "demo.resume": "Увімкнути фон",
    "demo.pan": "Проведи по екрану, щоб роздивитися деталі.",
    "hero.tour": "Дивитися тур на 40 секунд",
    "in.guide": "Детально →", "in.guide2": "Детально: що змінюється і як видалити →",
    "in.c1": "Один порожній файл вмикає власний локальний відлагоджувальний перемикач Steam — файли Steam не змінюються.",
    "in.c2": "Маленький помічник стартує під час входу, без вікна, і додає інтерфейс у пам'ять.",
    "in.c3": "Сейви лише читаються. Ігор і їхніх процесів не торкаємося.",
    "pw.hours": "год",
    "nav.games": "Ігри",
    "cat.kicker": "Підтримувані ігри", "cat.h2": "Ігри, які вже знають, де ти зупинився.",
    "cat.p": "Публічна альфа містить ці 22 читачі. Картки демо — фіксовані знімки; поля читачів закріплено EN/UK/RU golden-тестами, коли є дослідницька фікстура.",
    "cat.pc": "Лише ПК · недоступно на Deck", "ft.deck_unavailable": "Збереження Oodle потребують нативного ooz; у Python Decky немає декодера", "cat.proven": "перевірено golden", "cat.check": "немає фікстури",
    "ft.place": "де зупинився", "ft.objective": "поточна ціль", "ft.facts": "факти", "ft.icons": "значки",
    "ft.people": "хто живий", "ft.rec": "твій геймплей", "ft.uk": "назви українською",
    "cat.more": "Хочеш свою гру тут? Попроси або додай сам.", "cat.req": "Попросити гру", "cat.add": "Додати зі ШІ-агентом",
    "nav.demo": "Демо", "nav.features": "Можливості", "nav.battery": "Батарея", "nav.agents": "Своя гра", "nav.install": "Встановлення", "nav.support": "Підтримати",
    "hero.tag": "публічна альфа для Steam Deck",
    "hero.h1": "Твої ігри пам'ятають,<br>де ти зупинився.",
    "hero.lead": "Розділ, поточне завдання й зібрані речі — зі справжнього сейву, просто у Steam. А на фоні може бути твій геймплей.",
    "hero.cta1": "Спробувати демо", "hero.cta2": "Про реліз →", "hero.cta3": "Підтримати",
    "hero.meta": "Безкоштовно · відкритий код · сейви читаються без інтернету",
    "hero.press": "PRESS START",
    "demo.h2": "Це справжні сейви.",
    "demo.p": "{n} ігор зі справжніми знімками сейвів автора та спільноти. Показані лише перевірені поля; назви — з файлів гри або самого сейву.",
    "demo.keys": "← → · обкладинки · геймпад",
    "demo.music.on": "Музика увімк.", "demo.music.off": "Музика вимк.",
    "demo.toast": "На Деці ця кнопка запускає гру.",
    "demo.proven": "Поля перевірені", "demo.proven.t": "Показані поля перевірено на справжніх етапах сейвів і даних гри. Це знімок для демо, а не поточний прогрес.",
    "demo.bg.rec": "Фон: власний геймплей автора, записаний Steam",
    "demo.bg.trailer": "Фон: геймплейний фрагмент трейлера з магазину",
    "demo.nolang": "У цієї гри немає української, тому назви англійською — так само, як у самій грі.",
    "s.play": "Грати", "s.last": "Запуск", "s.played": "Зіграно", "s.story": "Сюжет", "s.full": "На 100%", "s.h": "год",
    "rec.kicker": "Твій геймплей", "rec.h2": "На фоні можеш бути ти.",
    "rec.p": "Steam і так записує твою гру у фоні. Continue? вирізає чистий шматок <b>твого</b> геймплею — без меню, завантажень і паузи — і крутить його за логотипом. God of War і TEKKEN тут — справжні сесії автора.",
    "rec.n1": "Сам обирає моменти з дією, пропускає меню й екрани завантаження.",
    "rec.n2": "Запису ще немає? Береться найкращий геймплейний фрагмент трейлера.",
    "rec.n3": "Для кожної гри можна обрати трейлер Steam, локальний запис, трейлер YouTube зі згодою або зображення.",
    "rec.note": "Для власного геймплею потрібні фоновий Steam Game Recording і придатний локальний запис на цьому Деку.",
    "rec.you": "твій геймплей",
    "feat.h2": "Щоб хотілося грати.",
    "feat.p": "Пам'ятаєш титульні екрани з дитинства — музика, рух, обіцянка пригоди? Це відчуття — для кожної гри в бібліотеці.",
    "f1.t": "Де зупинився", "f1.p": "Просто з файлу збереження, без інтернету, на самій Деці: розділ, локація — а якщо гра це зберігає, то й текст поточного завдання.",
    "f2.t": "Факти, які важливі", "f2.p": "Знайдені тотеми, вдягнені амулети, хто ще живий. У кожного факту свій тихий білий значок.",
    "f3.t": "Жива головна", "f3.p": "Обрана гра оживає й на головній Steam: її геймплей, логотип, музика.",
    "f4.t": "Альфа на Деку зараз, ПК пізніше", "f4.p": "Версія 0.1.0 — самодостатній плагін Decky. Перевірений пакет Windows і Big Picture лишається в дорожній карті.",
    "f5.t": "Три справжні пресети", "f5.p": "Легкий і Збалансований обмежують відео 720p; Максимум — 1080p. Кеш 1, 2, 4 або 8 ГБ обирається окремо.",
    "f6.t": "Твоєю мовою", "f6.p": "Назви беруться з файлів самої гри — мовою твого Steam. Це справжній рядок з Nine Sols — спершу твоєю мовою:",
    "chips.h": "І дрібниці",
    "c1": "Час сюжету і на 100% (HowLongToBeat) у рядку «Грати»", "c2": "Оцінка ProtonDB на обкладинках і сторінці гри",
    "c3": "Окреме джерело тла для гри", "c4": "Знеособлений попередній перегляд звіту та ZIP",
    "c5": "Досягнення X / Y читаються локально — без веб-API і публічного профілю", "c6": "Встановлені ігри першими на головній",
    "c7": "Логотипи SteamGridDB і 4K-арт", "c8": "Ярлики не зі Steam теж отримують трейлери й арт",
    "c9": "Опис гри з магазину Steam — твоєю мовою", "c10": "Обмежений кеш 1 / 2 / 4 / 8 ГБ",
    "c11": "Музика теми лише після згоди", "c12": "Усе вмикається й вимикається в меню ⋯", "c13": "Оновлення ZIP релізу потребує відповідного SHA-256",
    "dev.deck": "Альфа Steam Deck", "dev.pc": "Макет ПК · пізніше",
    "p.lite": "Легкий", "p.balanced": "Баланс", "p.max": "Максимум",
    "p.video": "Живе тло", "p.disk": "Ліміт кешу", "p.scope": "Вибір тла", "p.power": "Правило відтворення",
    "pw.kicker": "Батарея", "pw.h2": "Виміряно, а не вгадано.",
    "pw.p": "Портативка живе від батареї, тож ми міряємо. Справжній Steam Deck OLED від батареї: увесь пристрій (екран, Wi-Fi, звук), середнє за 45 секунд, яскравість 13 %. Години — скільки протримається повна батарея 50 Вт·год на цьому екрані.",
    "pw.r1": "Сторінка гри, нерухома картинка", "pw.r2": "Сторінка гри, живий фон 1080p + музика",
    "pw.r3": "Головна Steam без нашого відео", "pw.r4": "Головна Steam, живий фон + музика",
    "pw.why": "Різниця в замірі — близько 1,5 Вт на сторінці гри: приблизно дві години повної батареї, якщо залишатися на цьому екрані. Відео на головній додало 0,4 Вт, музика не дала помітної різниці. Тому альфа 0.1.0 типово використовує Легкий режим: кадр від батареї й без відео на головній.",
    "pw.m.h": "Поведінка батареї в 0.1.0",
    "pw.m1": "<b>Легкий</b> — до 720p, відео сторінки лише від мережі, без відео на головній, кадр від батареї.",
    "pw.m2": "<b>Збалансований</b> — до 720p, сторінка і головна рухаються від мережі, кадр від батареї.",
    "pw.m3": "<b>Максимум</b> — до 1080p і відео всюди, зокрема від батареї.",
    "pw.honest": "Виміряно на Steam Deck OLED автора 6 жовтня 2026 автоматичним сценарієм. Розрахунок часу стосується показаного екрана й умов цього заміру.",
    "pw.unit": "Вт",
    "ag.kicker": "Спільнота", "ag.h2": "Додай улюблену гру — разом зі своїм ШІ-агентом.",
    "ag.p": "Кожну гру в Continue? розбирає той, хто її любить. Спрямуй Claude Code, Codex або Gemini на <code>AGENTS.md</code>: він знайде сейв, порівняє етапи, візьме назви з файлів гри й запустить перевірку. Ти переглядаєш результат, відкриваєш pull request — і твоя гра з'являється в усіх.",
    "ag.r1": "<b>Лише доведене.</b> Поле вважається фактом, тільки якщо змінюється між етапами сейву.",
    "ag.r2": "<b>Назви — лише з файлів гри.</b> Не з пам'яті й не з вікі.",
    "ag.r3": "<b>Golden-регресійні тести вже є.</b> Еталони змінюються лише явною командою оновлення.",
    "ag.r4": "<b>Значки за промптами.</b> Готові промпти для ChatGPT чи Gemini — білі, пласкі, за референсом.",
    "ag.cta1": "Читати гайд", "ag.cta2": "Discord — скоро",
    "pr.h": "Доведено — або не потрапляє.",
    "pr.p": "Навіть у ранніх розборах самого автора траплялися поля, що виглядали правильно, але ніколи не змінювалися. Тепер перевірка відсіює їх сама. Справжні випадки:",
    "pr.ok": "Nine Sols — смерті 0 → 201; рівень, печатки й нефрити ростуть на 5 сейвах", "pr.okv": "доведено",
    "pr.no1": "Лічильник, що в кожному сейві дорівнював 0", "pr.nov1": "відхилено: не змінюється",
    "pr.no2": "Назви розділів, написані з пам'яті", "pr.nov2": "відхилено: немає у файлах гри",
    "pr.no3": "«Личинки x / 46» з підсумком із вікі", "pr.nov3": "відхилено: підсумки — з даних гри",
    "in.kicker": "Встановлення", "in.h2": "Перевір альфу на Деку.", "in.soon": "альфа 0.1.0",
    "in.deck": "Steam Deck", "in.d1": "Встанови <b>Decky Loader</b>.", "in.d2": "Відкрий <b>Decky → Налаштування → Розробник → Встановити з URL/ZIP</b> і вибери ZIP релізу.", "in.d3": "Перевір Continue? 0.1.0 і відкрий гру.",
    "in.dopt": "Перед звітом прочитай повні інструкції встановлення, відновлення, видалення та тестування.",
    "in.pc": "ПК · Big Picture", "in.p1": "Не входить до 0.1.0.", "in.p2": "Помічник Windows і перевірений setup не постачаються.", "in.p3": "Дивись дорожню карту, а не старі проєктні нотатки.",
    "in.popt": "Підтримка ПК і Big Picture з'явиться пізніше.",
    "up.t": "Оновлення Дека з контрольною сумою.", "up.p": "Continue? щодня шукає ZIP релізу з відповідним SHA-256 і передає встановлення Decky. Помилка перевірки не ламає встановлену версію.",
    "cl.kicker": "Що нового", "cl.preview": "публічна альфа",
    "cl.1v": "0.1.0 · жовтень 2026", "cl.1": "<li>Самодостатній Decky ZIP для встановлення</li><li>22 публічні читачі з golden-регресією</li><li>Живе тло на сторінці гри й головній Steam</li>",
    "cl.2v": "Діагностика тестувальника", "cl.2": "<li>Перегляд знеособленого JSON до збереження</li><li>ZIP додається до шаблону Issue для альфи</li>",
    "cl.3v": "Безпечний реліз", "cl.3": "<li>Для оновлення потрібні ZIP релізу й відповідний SHA-256</li><li>Встановлює Decky; помилка перевірки не ламає поточну версію</li>",
    "faq.kicker": "Варто знати", "faq.h2": "Примітки й нюанси.",
    "q1": "Куди зникли підказки кнопок Steam?",
    "a1": "Continue? вміє ховати нижню смугу підказок Steam, щоб сторінці гри було більше місця. Кнопки роблять те саме, що й раніше, — зникають лише нагадування. Вперше з Декою? Залиш підказки увімкненими (один перемикач у меню ⋯), доки не звикнеш до кнопок.",
    "q2": "Чи може він зламати мої сейви?",
    "a2": "Ні. Сейви лише читаються — копіюються й розбираються, ніколи не записуються. Файлів і процесів ігор Continue? теж не торкається.",
    "q3": "Steam оновився, і щось виглядає не так.",
    "a3": "Continue? живе всередині інтерфейсу Steam, а Valve іноді його змінює. Після оновлення плагін сам підключається знову; якщо щось усе ж зникло — вийде оновлення Continue?. У кожному релізі вказано версію Steam, на якій перевірено.",
    "q4": "Моєї гри немає. Що я отримаю?",
    "a4": "Усе одно багато: живий фон, музику теми, час у грі, досягнення, HowLongToBeat і ProtonDB. «Де зупинився» і факти потребують розбору сейву — і його можна додати разом зі своїм ШІ-агентом.",
    "q5": "Чи потрібен інтернет?",
    "a5": "Читання сейвів — повністю офлайн. Описи, трейлери, HowLongToBeat і ProtonDB завантажуються один раз і кешуються.",
    "q6": "Чому немає моєї мови?",
    "a6": "Назви беруться з самої гри: якщо гра має твою мову — Continue? її використає; якщо ні — покаже англійську гри. Інтерфейс перекладає спільнота.",
    "sup.kicker": "Підтримати", "sup.h2": "Безкоштовно. Назавжди.",
    "sup.p": "Continue? нічого не коштує і не коштуватиме. Якщо він повернув тобі бажання пограти — можна допомогти проєкту жити: кожен донат іде в розробку й у підписку на ШІ, з яким він будується.",
    "sup.mono": "Банка monobank", "sup.mono.p": "Картки будь-якої країни, Apple Pay, Google Pay.", "sup.mono.b": "Відкрити банку", "sup.card": "Картка банки",
    "sup.pp": "PayPal", "sup.pp.p": "Надсилай на цю адресу — натисни, щоб скопіювати.",
    "sup.cr": "Крипта · USDT", "sup.cr.p": "TRC20 (Tron) або BEP20 (BNB Smart Chain). Натисни, щоб скопіювати, або скануй.",
    "sup.soon": "скоро", "sup.copied": "Скопійовано", "sup.qr": "QR",
    "sup.deck": "Тестуєш альфу? Відкрий Continue? → «Зібрати звіт для розробника», перевір дані й додай ZIP до шаблону Issue.",
    "foot.made": "Зроблено в Україні, автор —", "foot.lic": "Код: GPL-3.0",
    "foot.legal": "Назви, логотипи, музика й відео ігор належать їхнім власникам. Проєкт не пов'язаний з Valve.",
  },

  ru: {
    "demo.source.owner": "Сейв автора · снимок для демо",
    "demo.source.community": "Сейв сообщества · снимок для демо",
    "demo.sourceLanguage": "Названия остаются на языке проверенного источника ({lang}).",
    "demo.bg.publisher": "Фон: трейлер издателя",
    "demo.bg.art": "Фон: иллюстрация игры",
    "ft.chapter": "глава / задание в сейве",
    "nav.open": "Открыть меню",
    "nav.close": "Закрыть меню",
    "cat.search": "Найди свою игру",
    "cat.clear": "Очистить поиск",
    "cat.filter": "Фильтр игр по статусу проверки",
    "cat.all": "Все игры",
    "cat.results": "Показано {n} из {total} игр",
    "cat.demo": "Рассмотреть демо",
    "cat.empty": "Подходящих игр нет.",
    "cat.empty.p": "Попробуй более короткое название или другой фильтр. Свою игру можно попросить ниже.",
    "ag.example": "Пример процесса добавления игры, описанного в AGENTS.md.",
    "in.preview": "Публичная альфа 0.1.0 доступна как Decky ZIP для тестирования на Steam Deck. ПК и Big Picture — позже.",
    "hero.preview": "Публичная альфа для Steam Deck · 0.1.0",
    "demo.device": "Выбери устройство", "demo.previous": "Предыдущая игра", "demo.next": "Следующая игра",
    "demo.expand": "Увеличить экран", "demo.dialog": "Рассмотри демо", "demo.close": "Закрыть демо",
    "demo.pause": "Остановить фон", "demo.resume": "Включить фон",
    "demo.pan": "Проведи по экрану, чтобы рассмотреть детали.",
    "hero.tour": "Смотреть тур на 40 секунд",
    "in.guide": "Подробно →", "in.guide2": "Подробно: что меняется и как удалить →",
    "in.c1": "Один пустой файл включает собственный локальный отладочный переключатель Steam — файлы Steam не меняются.",
    "in.c2": "Маленький помощник стартует при входе, без окна, и добавляет интерфейс в память.",
    "in.c3": "Сейвы только читаются. Игры и их процессы не трогаются.",
    "pw.hours": "ч",
    "nav.games": "Игры",
    "cat.kicker": "Поддерживаемые игры", "cat.h2": "Игры, которые уже знают, где ты остановился.",
    "cat.p": "Публичная альфа содержит эти 22 читателя. Карточки демо — фиксированные снимки; поля читателей закреплены EN/UK/RU golden-тестами, когда есть исследовательская фикстура.",
    "cat.pc": "Только ПК · недоступно на Deck", "ft.deck_unavailable": "Сейвы Oodle требуют нативного ooz; в Python Decky нет декодера", "cat.proven": "проверено golden", "cat.check": "нет фикстуры",
    "ft.place": "где остановился", "ft.objective": "текущая цель", "ft.facts": "факты", "ft.icons": "значки",
    "ft.people": "кто жив", "ft.rec": "твой геймплей", "ft.uk": "названия по-украински",
    "cat.more": "Хочешь свою игру здесь? Попроси или добавь сам.", "cat.req": "Попросить игру", "cat.add": "Добавить с ИИ-агентом",
    "nav.demo": "Демо", "nav.features": "Возможности", "nav.battery": "Батарея", "nav.agents": "Своя игра", "nav.install": "Установка", "nav.support": "Поддержать",
    "hero.tag": "публичная альфа для Steam Deck",
    "hero.h1": "Твои игры помнят,<br>где ты остановился.",
    "hero.lead": "Глава, текущая цель и собранные вещи — из настоящего сейва, прямо в Steam. А на фоне может быть твой геймплей.",
    "hero.cta1": "Попробовать демо", "hero.cta2": "О релизе →", "hero.cta3": "Поддержать",
    "hero.meta": "Бесплатно · открытый код · сейвы читаются без интернета",
    "hero.press": "PRESS START",
    "demo.h2": "Это настоящие сейвы.",
    "demo.p": "{n} игр с настоящими снимками сейвов автора и сообщества. Показаны только проверенные поля; названия — из файлов игры или самого сейва.",
    "demo.keys": "← → · обложки · геймпад",
    "demo.music.on": "Музыка вкл", "demo.music.off": "Музыка выкл",
    "demo.toast": "На Деке эта кнопка запускает игру.",
    "demo.proven": "Поля проверены", "demo.proven.t": "Показанные поля проверены на настоящих этапах сейвов и данных игры. Это снимок для демо, а не текущий прогресс.",
    "demo.bg.rec": "Фон: собственный геймплей автора, записанный Steam",
    "demo.bg.trailer": "Фон: геймплейный кусок трейлера из магазина",
    "demo.nolang": "У этой игры нет украинского, поэтому названия на английском — как в самой игре.",
    "s.play": "Играть", "s.last": "Запуск", "s.played": "Наиграно", "s.story": "Сюжет", "s.full": "На 100%", "s.h": "ч",
    "rec.kicker": "Твой геймплей", "rec.h2": "На фоне можешь быть ты.",
    "rec.p": "Steam и так записывает твою игру в фоне. Continue? вырезает чистый кусок <b>твоего</b> геймплея — без меню, загрузок и паузы — и крутит его за логотипом. God of War и TEKKEN здесь — настоящие сессии автора.",
    "rec.n1": "Сам выбирает моменты с действием, пропускает меню и экраны загрузки.",
    "rec.n2": "Записи ещё нет? Берётся лучший геймплейный кусок трейлера.",
    "rec.n3": "Для каждой игры можно выбрать трейлер Steam, локальную запись, трейлер YouTube с согласием или картинку.",
    "rec.note": "Для своего геймплея нужны фоновая Steam Game Recording и подходящая локальная запись на этой Деке.",
    "rec.you": "твой геймплей",
    "feat.h2": "Чтобы хотелось играть.",
    "feat.p": "Помнишь титульные экраны из детства — музыка, движение, обещание приключения? Это чувство — для каждой игры в библиотеке.",
    "f1.t": "Где остановился", "f1.p": "Прямо из файла сохранения, без интернета, на самой Деке: глава, локация — а если игра это хранит, то и текст текущего задания.",
    "f2.t": "Факты, которые важны", "f2.p": "Найденные тотемы, надетые амулеты, кто ещё жив. У каждого факта свой тихий белый значок.",
    "f3.t": "Живая главная", "f3.p": "Выбранная игра оживает и на главной Steam: её геймплей, логотип, музыка.",
    "f4.t": "Альфа на Деке сейчас, ПК позже", "f4.p": "Версия 0.1.0 — самодостаточный плагин Decky. Проверенная сборка Windows и Big Picture остаётся в дорожной карте.",
    "f5.t": "Три настоящих пресета", "f5.p": "Лёгкий и Сбалансированный ограничивают видео 720p; Максимум — 1080p. Кэш 1, 2, 4 или 8 ГБ выбирается отдельно.",
    "f6.t": "На твоём языке", "f6.p": "Названия берутся из файлов самой игры — на языке твоего Steam. Это настоящая строка из Nine Sols — сначала на твоём языке:",
    "chips.h": "И мелочи",
    "c1": "Время сюжета и на 100% (HowLongToBeat) в строке «Играть»", "c2": "Оценка ProtonDB на обложках и странице игры",
    "c3": "Отдельный источник фона для игры", "c4": "Обезличенный предпросмотр отчёта и ZIP",
    "c5": "Достижения X / Y читаются локально — без веб-API и публичного профиля", "c6": "Установленные игры первыми на главной",
    "c7": "Логотипы SteamGridDB и 4K-арт", "c8": "Ярлыки не из Steam тоже получают трейлеры и арт",
    "c9": "Описание игры из магазина Steam — на твоём языке", "c10": "Ограниченный кэш 1 / 2 / 4 / 8 ГБ",
    "c11": "Музыка темы только после согласия", "c12": "Всё включается и выключается в меню ⋯", "c13": "Обновление ZIP релиза требует совпадающий SHA-256",
    "dev.deck": "Альфа Steam Deck", "dev.pc": "Макет ПК · позже",
    "p.lite": "Лёгкий", "p.balanced": "Баланс", "p.max": "Максимум",
    "p.video": "Живой фон", "p.disk": "Лимит кэша", "p.scope": "Выбор фона", "p.power": "Правило воспроизведения",
    "pw.kicker": "Батарея", "pw.h2": "Измерено, а не угадано.",
    "pw.p": "Портативка живёт от батареи, поэтому мы меряем. Настоящий Steam Deck OLED от батареи: всё устройство (экран, Wi-Fi, звук), среднее за 45 секунд, яркость 13 %. Часы — сколько продержится полная батарея 50 Вт·ч на этом экране.",
    "pw.r1": "Страница игры, неподвижная картинка", "pw.r2": "Страница игры, живой фон 1080p + музыка",
    "pw.r3": "Главная Steam без нашего видео", "pw.r4": "Главная Steam, живой фон + музыка",
    "pw.why": "Разница в замере — около 1,5 Вт на странице игры: примерно два часа полной батареи, если оставаться на этом экране. Видео на главной добавило 0,4 Вт, музыка не дала заметной разницы. Поэтому альфа 0.1.0 по умолчанию использует Лёгкий режим: кадр от батареи и без видео на главной.",
    "pw.m.h": "Поведение батареи в 0.1.0",
    "pw.m1": "<b>Лёгкий</b> — до 720p, видео страницы только от сети, без видео на главной, кадр от батареи.",
    "pw.m2": "<b>Сбалансированный</b> — до 720p, страница и главная двигаются от сети, кадр от батареи.",
    "pw.m3": "<b>Максимум</b> — до 1080p и видео везде, включая работу от батареи.",
    "pw.honest": "Измерено на Steam Deck OLED автора 6 октября 2026 автоматическим сценарием. Расчёт времени относится к показанному экрану и условиям этого замера.",
    "pw.unit": "Вт",
    "ag.kicker": "Сообщество", "ag.h2": "Добавь любимую игру — вместе со своим ИИ-агентом.",
    "ag.p": "Каждую игру в Continue? разбирает тот, кто её любит. Направь Claude Code, Codex или Gemini на <code>AGENTS.md</code>: он найдёт сейв, сравнит этапы, возьмёт названия из файлов игры и прогонит проверку. Ты смотришь результат, открываешь pull request — и твоя игра появляется у всех.",
    "ag.r1": "<b>Только доказанное.</b> Поле считается фактом, только если меняется между этапами сейва.",
    "ag.r2": "<b>Названия — только из файлов игры.</b> Не по памяти и не с вики.",
    "ag.r3": "<b>Golden-регрессионные тесты уже есть.</b> Эталоны меняются только явной командой обновления.",
    "ag.r4": "<b>Значки по промптам.</b> Готовые промпты для ChatGPT или Gemini — белые, плоские, по референсу.",
    "ag.cta1": "Читать гайд", "ag.cta2": "Discord — скоро",
    "pr.h": "Доказано — или не попадает.",
    "pr.p": "Даже в ранних разборах самого автора бывали поля, которые выглядели правильно, но никогда не менялись. Теперь проверка отсеивает их сама. Настоящие случаи:",
    "pr.ok": "Nine Sols — смерти 0 → 201; уровень, печати и нефриты растут на 5 сейвах", "pr.okv": "доказано",
    "pr.no1": "Счётчик, который в каждом сейве был 0", "pr.nov1": "отклонено: не меняется",
    "pr.no2": "Названия глав, написанные по памяти", "pr.nov2": "отклонено: нет в файлах игры",
    "pr.no3": "«Гусенички x / 46» с итогом из вики", "pr.nov3": "отклонено: итоги — из данных игры",
    "in.kicker": "Установка", "in.h2": "Проверь альфу на Деке.", "in.soon": "альфа 0.1.0",
    "in.deck": "Steam Deck", "in.d1": "Установи <b>Decky Loader</b>.", "in.d2": "Открой <b>Decky → Настройки → Разработчик → Установить из URL/ZIP</b> и выбери ZIP релиза.", "in.d3": "Проверь Continue? 0.1.0 и открой игру.",
    "in.dopt": "Перед отчётом прочитай полные инструкции установки, восстановления, удаления и тестирования.",
    "in.pc": "ПК · Big Picture", "in.p1": "Не входит в 0.1.0.", "in.p2": "Помощник Windows и проверенный setup не поставляются.", "in.p3": "Смотри дорожную карту, а не старые проектные заметки.",
    "in.popt": "Поддержка ПК и Big Picture появится позже.",
    "up.t": "Обновления Деки с контрольной суммой.", "up.p": "Continue? ежедневно ищет ZIP релиза с совпадающим SHA-256 и передаёт установку Decky. Ошибка проверки не ломает установленную версию.",
    "cl.kicker": "Что нового", "cl.preview": "публичная альфа",
    "cl.1v": "0.1.0 · октябрь 2026", "cl.1": "<li>Самодостаточный Decky ZIP для установки</li><li>22 публичных читателя с golden-регрессией</li><li>Живой фон на странице игры и главной Steam</li>",
    "cl.2v": "Диагностика тестера", "cl.2": "<li>Просмотр обезличенного JSON до сохранения</li><li>ZIP прикладывается к шаблону Issue для альфы</li>",
    "cl.3v": "Безопасный релиз", "cl.3": "<li>Для обновления нужны ZIP релиза и совпадающий SHA-256</li><li>Устанавливает Decky; ошибка проверки не ломает текущую версию</li>",
    "faq.kicker": "Полезно знать", "faq.h2": "Примечания и нюансы.",
    "q1": "Куда пропали подсказки кнопок Steam?",
    "a1": "Continue? умеет прятать нижнюю полосу подсказок Steam, чтобы странице игры было больше места. Кнопки делают то же, что и раньше, — пропадают только напоминания. Впервые с Декой? Оставь подсказки включёнными (один переключатель в меню ⋯), пока не привыкнешь к кнопкам.",
    "q2": "Может ли он сломать мои сейвы?",
    "a2": "Нет. Сейвы только читаются — копируются и разбираются, никогда не записываются. Файлов и процессов игр Continue? тоже не касается.",
    "q3": "Steam обновился, и что-то выглядит не так.",
    "a3": "Continue? живёт внутри интерфейса Steam, а Valve иногда его меняет. После обновления плагин сам подключается заново; если что-то всё же пропало — выйдет обновление Continue?. В каждом релизе указана версия Steam, на которой проверено.",
    "q4": "Моей игры нет. Что я получу?",
    "a4": "Всё равно много: живой фон, музыку темы, время в игре, достижения, HowLongToBeat и ProtonDB. «Где остановился» и факты требуют разбора сейва — и его можно добавить вместе со своим ИИ-агентом.",
    "q5": "Нужен ли интернет?",
    "a5": "Чтение сейвов — полностью офлайн. Описания, трейлеры, HowLongToBeat и ProtonDB загружаются один раз и кэшируются.",
    "q6": "Почему нет моего языка?",
    "a6": "Названия берутся из самой игры: если в игре есть твой язык — Continue? его использует; если нет — покажет английский игры. Интерфейс переводит сообщество.",
    "sup.kicker": "Поддержать", "sup.h2": "Бесплатно. Навсегда.",
    "sup.p": "Continue? ничего не стоит и не будет. Если он вернул тебе желание поиграть — можно помочь проекту жить: каждый донат идёт в разработку и в подписку на ИИ, с которым он строится.",
    "sup.mono": "Банка monobank", "sup.mono.p": "Карты любой страны, Apple Pay, Google Pay.", "sup.mono.b": "Открыть банку", "sup.card": "Карта банки",
    "sup.pp": "PayPal", "sup.pp.p": "Отправляй на этот адрес — нажми, чтобы скопировать.",
    "sup.cr": "Крипта · USDT", "sup.cr.p": "TRC20 (Tron) или BEP20 (BNB Smart Chain). Нажми, чтобы скопировать, или сканируй.",
    "sup.soon": "скоро", "sup.copied": "Скопировано", "sup.qr": "QR",
    "sup.deck": "Тестируешь альфу? Открой Continue? → «Собрать отчёт для разработчика», проверь данные и приложи ZIP к шаблону Issue.",
    "foot.made": "Сделано в Украине, автор —", "foot.lic": "Код: GPL-3.0",
    "foot.legal": "Названия, логотипы, музыка и видео игр принадлежат их владельцам. Проект не связан с Valve.",
  },
};

// Ролик-тур (index.html?reel=1&lang=en): подписи сцен
const REEL_TXT = {
  en: {
    tag: "Your games remember where you left off.",
    k1: "Where you left off", t1: "Read straight from your save — offline, on the Deck itself.",
    k2: "Proven facts", t2: "Only what really changes between saves. Even who is still alive.",
    k3: "In your language", t3: "Names come from the game's own files.",
    k4: "Your gameplay", t4: "Your own play, recorded by Steam, becomes the background.",
    k5: "Alpha diagnostics", t5: "Review the sanitized report before saving its ZIP.",
    end: "Free · open source · Steam Deck alpha",
  },
  uk: {
    tag: "Твої ігри пам'ятають, де ти зупинився.",
    k1: "Де зупинився", t1: "Просто з файлу збереження — без інтернету, на самій Деці.",
    k2: "Доведені факти", t2: "Лише те, що справді змінюється між сейвами. Навіть хто ще живий.",
    k3: "Твоєю мовою", t3: "Назви — з файлів самої гри.",
    k4: "Твій геймплей", t4: "Твоя власна гра, записана Steam, стає фоном.",
    k5: "Діагностика альфи", t5: "Перевір знеособлений звіт перед збереженням ZIP.",
    end: "Безкоштовно · відкритий код · альфа Steam Deck",
  },
  ru: {
    tag: "Твои игры помнят, где ты остановился.",
    k1: "Где остановился", t1: "Прямо из файла сохранения — без интернета, на самой Деке.",
    k2: "Доказанные факты", t2: "Только то, что правда меняется между сейвами. Даже кто ещё жив.",
    k3: "На твоём языке", t3: "Названия — из файлов самой игры.",
    k4: "Твой геймплей", t4: "Твоя собственная игра, записанная Steam, становится фоном.",
    k5: "Диагностика альфы", t5: "Проверь обезличенный отчёт перед сохранением ZIP.",
    end: "Бесплатно · открытый код · альфа Steam Deck",
  },
};
