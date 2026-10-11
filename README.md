# Continue?

[Русский](README.ru.md) · [Українська](README.uk.md) · **English**

> **Public alpha 0.1.0.** The Steam Deck build is locally verified. A separate Windows/Big Picture package and installer
> are fixture-tested, but still require acceptance on a clean PC with a real Steam client before public release.

Continue? adds the last proven chapter, location, objective, and useful facts from supported save files to a game's Steam page. It can also use a Steam trailer, a consent-gated YouTube trailer, a local Steam Game Recording clip, or a still image as the background.

[Install on Steam Deck](docs/install-deck.md) · [Windows / Big Picture guide](docs/install-pc.md) · [Alpha tester checklist](docs/alpha-testers.md) · [Browser showcase](docs/preview.md) · [Roadmap](docs/ROADMAP.md)

## What is in alpha 0.1.0

- A self-contained Decky plugin; no PC helper is required on Deck.
- EN, UK, and RU interface text. Save labels and chapter names come from the game or save where proven; if a game has no Ukrainian text, that reader falls back to its verified English text.
- Per-game background source: Steam, YouTube, Steam Game Recording, or artwork. YouTube and theme-music downloads require separate, explicit consent.
- Light, Balanced, and Maximum media presets. Light and Balanced cap video at 720p; Maximum caps it at 1080p. The cache budget is selected separately (1, 2, 4, or 8 GB).
- A live background on the game page and, when enabled by the selected preset, on Steam Home.
- An optional brightness bar and a setting that avoids duplicating the separate Brightness Bar plugin.
- Daily release checks. Decky is given the release ZIP and its matching SHA-256; Continue? does not replace its own files directly.
- **Collect a developer report** in the `…` menu. You see the complete sanitized JSON before saving the ZIP.

The plugin reads saves and never writes them. Its display is based on the last save, so it may lag behind unsaved gameplay.

## Supported save readers

The fields below come from the committed golden snapshots. Values that are absent in a fixture are not invented.

| Game | Proven fields shown by the golden snapshots |
|---|---|
| Alan Wake | place, chapter; coffee thermoses, chests, can pyramids, TV and radio shows, signs |
| Clair Obscur: Expedition 33 | place, chapter, objective; party levels, story progress, save time |
| God of War Ragnarök† | reader included; no local fixture was available for this golden run |
| Hollow Knight | place; completion, time, geo, masks, nail, spells, abilities, charms, grubs, dreamers |
| Horizon Forbidden West | quest text as place/chapter; Aloy's level and play time |
| Inscryption | deck, lives, teeth, highest damage |
| It Takes Two | place, chapter; chapter group and unlocked minigames |
| Life is Strange 2 | place, chapter; episode, completed episodes, souvenirs, journal, brotherhood and morality |
| Life is Strange: Double Exposure | place, chapter; episode and photos |
| Little Nightmares | place, chapter; nomes, statues and DLC items |
| Little Nightmares II | place, chapter and save time |
| Marvel's Spider-Man 2 | place, chapter, objective; completion, level, story, photos, Prowler stashes and Spider-Bots |
| NieR:Automata | place, chapter; character, route, level, gold, quests, weapons and endings |
| Nine Sols | place; time, level, deaths, seals, skills, jades and encyclopedia progress |
| REANIMAL | place, chapter; chapter number, gameplay time, finds, masks and posters |
| SILENT HILL 2 | place; health, ammunition, healing, kills, weapons, maps and memos |
| Slay the Spire | act/floor, character, ascension, wins, HP and gold |
| The Last of Us Part II Remastered† | reader included; no local fixture was available for this golden run |
| UNDERTALE | area; LV, HP, G, time, kills, weapons and armor |
| Uncharted: Legacy of Thieves Collection | chapter; completion, treasures and play time |
| Until Dawn | place, chapter; survivors, butterfly effects, clues and totems |

**Hogwarts Legacy — PC only.** Its Oodle-compressed saves require the native `ooz` module, which is absent from Decky Python. It is excluded from Steam Deck support until a portable Oodle decoder is available.

† The golden test deliberately skips a reader when its research fixture is not present. These two readers ship, but this table does not claim fields that were unavailable to the current golden run.

Sally Face and Alice: Madness Returns are not registered: the available material did not prove a reader across the required stages. ENSLAVED, LEGO Harry Potter, and Bleach readers are also excluded from the public build.

## Languages

The plugin interface is translated directly to English, Ukrainian, and Russian. Reader output is more conservative: names must be demonstrated by the save or by localized game files. This means a field can remain in English when the installed game data does not contain a proven Ukrainian string. Uncharted is such a case: the archive marked `uke` contains English, so its Ukrainian reader output intentionally uses verified English chapter text.

## Install, update, and remove

This alpha is not in the Decky store. Install the release ZIP or its direct URL through **Decky → Settings → Developer → Install from URL/ZIP**. Keep the `.sha256` file next to the release ZIP when distributing a release. Exact steps, failure recovery, and removal are in the [Steam Deck guide](docs/install-deck.md).

The Windows build is a separate `continue-pc-<version>.zip`: extract it, double-click `setup.cmd`, consent to Steam's
local debugging flag, and restart Steam after closing games. It installs per-user without administrator rights and has
fixture-verified repair, status, update rollback, and uninstall paths. Real Steam/SmartScreen/antivirus acceptance is
still pending; read the exact security trade-off and steps in the [Windows / Big Picture guide](docs/install-pc.md).

## Sending an alpha report

Open Continue?'s `…` menu and select **Collect a developer report**. The preview contains versions that are available, language and settings, the plugin log tail, installed-game reader outcomes with parse time, and background-cache state. It contains no save files or media. User names, profile paths, and Steam IDs are redacted. Review the preview, save the ZIP to Desktop or Downloads, and attach it to the matching [alpha issue template](.github/ISSUE_TEMPLATE/alpha_tester_report.md).

See the [full tester checklist](docs/alpha-testers.md) before reporting layout, reader, or media problems.

## Browser showcase

The website is a curated demonstration, not a Steam connection:

```text
python tools/preview.py
```

Open <http://127.0.0.1:8811/>. No Steam account or installed game is needed. The 20 interactive examples are fixed snapshots; the supported-reader catalog contains 22 public-alpha games.

## Development checks

The public export has no runtime dependency beyond what is already packaged. Useful local checks are:

```text
python tools/check_links.py
node --check site/app.js
node --check site/data.js
python tools/preview.py
```

Reader changes are reviewed through deterministic JSON golden snapshots. Updating them requires the explicit `--update` command; an ordinary test run never rewrites baselines.

Contributions must follow [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md). Code is licensed under [GPL-3.0](LICENSE); game names and media remain the property of their owners.
