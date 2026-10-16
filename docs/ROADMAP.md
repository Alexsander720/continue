# Continue? roadmap

The current release is **0.1.4** (with `continue-deck-0.1.4.zip` and `continue-pc-0.1.4-r19.zip`). The registry contains 23 active readers (22 games) and 3 reserved stubs; only the active readers ship, with 30 runtime name tables. The media cache budget is 1 / 2 / 4 / 8 GB on Deck and a shared 2 / 4 / 8 / 16 GB for backgrounds, music and private media tools on PC.

## Available in the 0.1.4 candidate

- Installable Decky ZIP (`continue-deck-0.1.4.zip`), and a Windows Big Picture package (`continue-pc-0.1.4-r19.zip` with `setup.cmd` and matching checksum files).
- Save reading with 23 active readers (22 games), backed by real-save golden stages; 3 reserved stubs are not shipped. Game and save names come only from demonstrated sources.
- English, Ukrainian, and Russian interface; game/save names only from demonstrated sources.
- Per-game Steam, YouTube, local-recording, or artwork background choice.
- Separate consent for YouTube trailers and theme music.
- Light/Balanced/Maximum media presets; quality ceiling up to 4K on PC; Deck cache 1/2/4/8 GB, shared PC cache 2/4/8/16 GB.
- Live background on game pages and optional Steam Home integration.
- Optional brightness bar.
- Daily update discovery; Decky performs installation only when the ZIP and SHA-256 are both present.
- Sanitized tester-report preview and ZIP export.
- Deterministic golden reader tests and public build/smoke/clean-device/fuzz harnesses.

## Added in this test candidate

- Standalone Deck music setup with private tools tested in isolated Linux (WSL), volume and playback locations, per-game Auto/None, battery-aware audio preparation and explicit downloader update/rollback. The tool/download pipeline was also run in a temporary folder on the physical Deck; playback through the installed plugin in Game Mode still needs physical acceptance.
- Recoverable music retries and Windows uninstall/retained-data recovery.

## Still to verify before release

- Acceptance of the 0.1.4 candidate with a physical controller: focus and D-pad navigation, confirm/back behavior, moving between games, backgrounds and music.
- Real Steam Deck hardware: installing the new ZIP, portraits and icons, controller use, suspend/resume, the SD-card library, update and rollback. The Deck package was not exercised on hardware in this round.
- Clean Windows without Python: first run and the Python download, SmartScreen, repair and uninstall. Windows 10 and ARM64 are experimental; the system exercised so far is Windows 11 x64.
- Live external scenarios: a real 4K source and its playback, a personal SteamGridDB key from entry to artwork restore, public update and rollback. Music downloads for two games have been exercised, but no guarantee covers every YouTube item.
- Public AI translation: dedicated user connection and authorization if desired (cloud translation APIs are not implemented in the public build; base descriptions are retrieved directly from Steam).
- Cache eviction, low-disk behavior, partial downloads, consent withdrawal, and fallback to a still image still need hardware confirmation.

## Windows / Big Picture status

The Windows package is released as a public alpha (`continue-pc-0.1.4-r19.zip`): per-user setup without administrator rights, repair, status, update rollback and uninstall were exercised with real Steam Big Picture on Windows 11 x64. The [PC guides](install-pc.md) and [quick install](quick-install.md) provide working installation instructions. Clean-device acceptance on Windows without Python, on Windows 10, and on ARM64 is ongoing, as are controller and TV-layout checks.

## Distribution

There is no Decky Store submission planned. The alpha is distributed through GitHub Releases, with update discovery from inside the plugin. The public PC package is released alongside the Deck build starting with v0.1.4.

## After the alpha stabilizes

- Expand reader coverage only when the five-part evidence gate is met: correct save selection, structural decode, at least three ordered stages from one playthrough, semantic correlation, and names from save/game files.
- Add more accessible in-plugin diagnostics and clearer per-source failure explanations.
- Add release rollback guidance after testing how current Decky versions handle it.

## Reader candidates currently blocked

- **Sally Face:** the available stages do not prove a scene-to-episode mapping across the required progression.
- **Alice: Madness Returns:** the gathered saves are from different authors/sources and do not form three ordered stages from one playthrough; the current byte scan is heuristic.
- **Black Myth: Wukong, Sifu, and Ghost of Tsushima:** the Round 8 research handoff did not mark their evidence ready for implementation.

Nothing in this roadmap is a compatibility promise. Released behavior is documented in [CHANGELOG](../CHANGELOG.md), [README](../README.md), the [Steam Deck install guide](install-deck.md), and the [PC install guide](install-pc.md).
