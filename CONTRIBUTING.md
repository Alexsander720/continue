# Contributing to Continue?

Continue? by Doctor_Nerd — https://github.com/Alexsander720/continue

This repository contains the **Continue? static showcase**, the **Deck plugin runtime** (`plugin/`), the **Windows helper** (`pc/`), and the **game contribution tools** (`tools/`). Work against files that exist;
do not invent missing runtime commands or report an unrun gate as passing.

## Useful contributions today

| Contribution | Where | What to include |
|---|---|---|
| Showcase bug / accessibility fix | `site/index.html`, `site/style.css`, `site/app.js` | Reproduction, screenshots and actual checks |
| Interface translation | `STR` in `site/data.js`; matching README / guides | EN / UK / RU parity, fallback and empty states |
| Documentation | Root Markdown and `docs/` | Working links, reproducible commands and accurate preview/v1 labels |
| Game request | [Game request](https://github.com/Alexsander720/continue/issues/new?template=game_request.md) | Appid, generic save location, useful fields |
| Reader contribution | `games/<slug>/` via [AGENTS.md](AGENTS.md) | Proven save stages, generator, reader, and passing gate |

Run `python tools/preview.py`; see the [preview guide](docs/preview.md). No npm install or frontend build is needed.

## Website or documentation pull requests

1. Describe the player's or reader's problem and the resulting behavior.
2. Keep EN / UK / RU consistent. Game names use only verified source languages; do not manually translate them.
3. Check relevant narrow/wide layouts, keyboard focus, dialog close/return, reduced motion and missing-media states.
4. If JavaScript changed, run `node --check site/app.js` and `node --check site/data.js`.
5. Open changed relative links and check that referenced media are tracked.
6. Separate checks from assumptions: browser checks do not establish physical controller or real Deck acceptance.

New demo snapshots need a source, date, semantic evidence for shown fields and an entry in [DEMO_SOURCES.md](site/DEMO_SOURCES.md).
Label trailers as trailers and community saves as community saves. Record presentation-asset provenance in
[ASSET_SOURCES.md](site/img/ASSET_SOURCES.md). Theme audio stays excluded from Git.

## Contributing game readers

[AGENTS.md](AGENTS.md) defines the contribution layout and card contract.

The repository includes already exported runtime readers in `plugin/py_modules/ddsaves/` and the Windows service in `pc/`.
New game additions are developed as isolated contributions under `games/<slug>/` with the following workflow:

1. **Scaffold the contribution:** `python tools/new_game.py <slug> <appid>` creates the initial `games/<slug>/` skeleton with stub reader, generator, documentation, and tests.
2. **Implement reader and tests:** Write `reader.py` and independently verified tests in `test_reader.py`. Run tests with `python tools/run_game_tests.py <slug>` (this command expects an existing `games/<slug>` directory; do not run it on legacy readers in `plugin/py_modules/ddsaves/`).
3. **Run the proof gate:** Run `python tools/gate/check_cards.py <slug>` on your stage data to verify the proof contract mechanically.

**Important:** New games in `games/<slug>/` do **not** integrate into the shipping plugin automatically. The `games/` folder is a contribution and validation staging area. Integrating accepted game readers into the shipping plugin runtime (`plugin/py_modules/ddsaves/` and runtime metadata) is an explicit maintainer release step requiring provenance and licensing review.

- Copy saves and resources; never write to originals, launch games or restart Steam during research.
- Compare at least two stages of one playthrough, ideally three to five; establish meaning independently of the parser output.
- Record source URLs/dates and hashes. A changing number alone does not prove its meaning.
- Generate names and totals from the user's game files. No extracted localization, game assets or generated name tables in a reader PR.
- Hide unproven fields. Distinguish saved chapter from furthest unlock and current run from historical statistics.
- Do not upload raw saves with IDs, account names, personal paths or other private content. Describe the evidence first.
- Run the actual proof gate (`python tools/gate/check_cards.py <slug>`) and reader tests (`python tools/run_game_tests.py <slug>`), and include their real output and remaining limitations in your PR.

AI coding agents are welcome, with human evidence review. A confident answer is not validation.

## Bug reports

Use the [bug template](https://github.com/Alexsander720/continue/issues/new?template=bug_report.md).
For the showcase include browser, viewport, language, game/device view and steps. For a future installed runtime include
the actual release, platform and Steam client version. Remove personal identifiers from screenshots/logs;
do not attach a whole save directory.

## License

Code contributions are under GNU GPL v3 and the existing [NOTICE.md](NOTICE.md) terms. Retain attribution and identify
modified distributions. Third-party game/device media are not licensed by the code license.
