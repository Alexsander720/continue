# Continue? roadmap

Last updated: 2026-10-10.

The current product is **public alpha 0.1.0 for Steam Deck**. The browser showcase remains available, but it is no longer the only public artifact. Dates below are deliberately omitted until the preceding physical-device checks pass.

## Available in 0.1.0-alpha

- Installable Decky ZIP with a matching SHA-256 asset.
- Save reading on Deck with 22 readers in the public allowlist.
- English, Ukrainian, and Russian interface; game/save names only from demonstrated sources.
- Per-game Steam, YouTube, local-recording, or artwork background choice.
- Separate consent for YouTube trailers and theme music.
- Light/Balanced/Maximum media presets and independent 1/2/4/8 GB cache budgets.
- Live background on game pages and optional Steam Home integration.
- Optional brightness bar.
- Daily update discovery; Decky performs installation only when the ZIP and SHA-256 are both present.
- Sanitized tester-report preview and ZIP export.
- Deterministic golden reader tests and public build/smoke/clean-device/fuzz harnesses.

## Alpha acceptance work

- Install, update, and uninstall through current Decky on clean Deck LCD and OLED devices.
- Validate controller focus, native Steam dialogs, suspend/resume, offline behavior, and recovery after a Steam client update.
- Verify game pages, Home, `…` menu, brightness overlay, and consent/report dialogs on the built-in display and external 720p, 1080p, and high-DPI/4K displays.
- Exercise every shipped reader against the owner's known stage saves; add redistributable fixtures where licensing and privacy permit.
- Collect only reviewer-approved sanitized report ZIPs and fix any remaining identity-redaction edge cases.
- Confirm cache eviction, low-disk behavior, partial downloads, consent withdrawal, and fallback to a still image on real hardware.

## After alpha stabilizes

- Prepare the Decky Store submission and its reproducible release metadata.
- Expand reader coverage only when the five-part evidence gate is met: correct save selection, structural decode, at least three ordered stages from one playthrough, semantic correlation, and names from save/game files.
- Add more accessible in-plugin diagnostics and clearer per-source failure explanations.
- Add release rollback guidance after testing how current Decky versions handle it.

## Later: Windows and Big Picture

PC/Windows and Steam Big Picture are **not** part of 0.1.0. The repository's `install-pc*.md` files are design notes, not working installation instructions. Before PC support can ship it needs:

- a packaged helper with explicit install and uninstall behavior;
- Steam path discovery without machine-specific assumptions;
- clean Windows acceptance tests and rollback;
- controller/TV layout and Steam-client compatibility checks;
- the same privacy, checksum, report-preview, and no-save-write guarantees as the Deck build.

## Reader candidates currently blocked

- **Sally Face:** no owner gameplay save; available stages do not prove a scene-to-episode mapping across the required progression.
- **Alice: Madness Returns:** the gathered saves are from different authors/sources and do not form three ordered stages from one playthrough; the current byte scan is heuristic.
- **Black Myth: Wukong, Sifu, and Ghost of Tsushima:** the Round 8 research handoff did not mark their evidence ready for implementation.

Nothing in this roadmap is a compatibility promise. Released behavior is documented in [CHANGELOG](../CHANGELOG.md), [README](../README.md), and the [Steam Deck install guide](install-deck.md).
