# Changelog

All notable public changes are recorded here. Continue? follows semantic versioning once the public alpha starts.

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
