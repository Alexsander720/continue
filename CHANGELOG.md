# Changelog

All notable public changes are recorded here. Continue? follows semantic versioning once the public alpha starts.

## 0.1.5 — 2026-11-24

Steam Deck and Windows Big Picture update (`continue-deck-0.1.5.zip` and `continue-pc-0.1.5.zip` with `.sha256`).

### Added

- **Sally Face** (`541570`, 23rd public reader): episode title, current objective, pocket inventory with item icons, remaining episode achievements with Steam achievement icons, and the game's custom visual theme.
- **God of War Ragnarök**: Nine Realms favors icon row (Odin's Ravens, Draugr Holes, Hel Tears, Lindwyrms, Stags of Yggdrasil, Berserker Souls, Nine Realms in Bloom) and Nornir Chests row (Chests, Idunn Apples, Horns of Blood Mead) with custom icons, plus an exact Table 1 journal counter for Odin's Ravens.
- **SILENT HILL 2 Remake**: expanded live save reader with James's vitals/condition row (health, drinks, syringes), arsenal with ammo and weapon kill counters, pocket key items with item icons, Strange Photos (`X / 26`), Glimpses of the Past (`X / 26`), memos, and survival stats.
- Shared themed card visuals across Deck and PC: decorative vertical rails per catalog game, accent-matched Play button styling, and a static vector flashlight beam for Alan Wake.
- Controller button prompt glyphs derived from Kenney Input Prompts (CC0) on Windows Big Picture.
- Windows local Steam Game Recording discovery and HEVC → AVC background clip normalization, plus `-OwnerThemeOnly` compatible visual installation mode.

### Changed

- Unified `groups` icon-row renderer in the shared frontend (`plugin/dist/index.js`) and safe lazy icon caching in `plugin/main.py` for both Steam Deck and Windows Big Picture.
- Updated the website showcase, README files (EN/UK/RU), and installation guides for `0.1.5` and 23 public readers.

## 0.1.4 — 2026-10-16

Steam Deck and Windows Big Picture release. Tested on a real Steam Deck OLED and Windows 11 x64.

### Added

- Public Windows / Steam Big Picture package (`continue-pc-0.1.4-r19.zip` with `.sha256`), tested on Windows 11 x64 and automated test suites.

### Changed

- Theme music plays as exactly one track: no overlapping or doubled audio across page changes.
- Music pauses when a game starts or the Deck goes to sleep, and resumes when you come back.
- Volume and **No music** in Quick Access now apply instantly to the track that is already playing.
- Battery care on Steam Deck: the first music setup asks for a charger at 30% or below.
- Revoking media consent stops active downloads immediately and removes temporary files.
- Fact icons and portraits restored for NieR:Automata, Horizon Forbidden West, and Alan Wake.
- Clear theme statuses: when YouTube temporarily rejects a request, the plugin says so and lets you retry later.
- More reliable media helper on Steam Deck: it runs with a clean environment under Decky.

## 0.1.0-alpha — 2026-10-10

First installable public alpha for Steam Deck testers.

### Added

- Self-contained Decky package with the Python save readers, localized data, frontend, and media manager included.
- English, Ukrainian, and Russian plugin interface.
- 22 public-alpha readers: Alan Wake, Clair Obscur: Expedition 33, God of War Ragnarök, Hogwarts Legacy, Hollow Knight, Horizon Forbidden West, Inscryption, It Takes Two, Life is Strange 2, Life is Strange: Double Exposure, Little Nightmares, Little Nightmares II, Marvel's Spider-Man 2, NieR:Automata, Nine Sols, REANIMAL, SILENT HILL 2, Slay the Spire, The Last of Us Part II Remastered, UNDERTALE, Uncharted: Legacy of Thieves Collection, and Until Dawn.
- Deterministic EN/UK/RU golden snapshots for every available research fixture, plus an explicit-only `--update` generator and readable structural diffs.
- Steam, YouTube, local Steam Game Recording, and artwork background choices. YouTube and theme music have separate consent dialogs.
- Light, Balanced, and Maximum presets; 1/2/4/8 GB cache budgets; live Steam Home background; optional brightness bar.
- Daily release checks that require both a ZIP and matching SHA-256 and delegate installation to Decky.
- **Collect a developer report**: exact pre-save JSON preview, one-use preview token, Desktop/Downloads ZIP, bounded log tail, reader timing/status, cache state, and identity/path redaction. Saves and media are excluded.
- EN/UK/RU alpha tester guides and GitHub issue templates.
- Browser layout regression renders for Deck, 720p, 1080p, and high-DPI 1440p in all three languages.

### Changed

- The website and README files now describe the installable Deck alpha instead of a presentation-only preview.
- The website catalog matches the 22 readers in the public build. Unproven ENSLAVED was removed; Alan Wake and Uncharted were added.
- Report-dialog actions fit on the Deck-sized viewport without losing either button.

### Intentionally not included

- Windows/Steam Big Picture runtime and installer. They remain later work.
- Sally Face and Alice: Madness Returns readers: the available research did not meet the multi-stage proof gate.
- ENSLAVED, LEGO Harry Potter, and Bleach readers: excluded by the public build allowlist.

### Known alpha limits

- A reader is skipped by the golden suite when its private research fixture is absent. The current local run has no fixture for God of War Ragnarök or The Last of Us Part II Remastered.
- Real-device focus, suspend/resume, Decky installation/update, and Steam-client-version compatibility still require testing on physical Steam Deck hardware.
- Game text can fall back to proven English when the installed game data has no demonstrated Ukrainian string.

See [installation](docs/install-deck.md), the [tester checklist](docs/alpha-testers.md), and the [roadmap](docs/ROADMAP.md).
