# Contributing to Continue?

Continue? by Doctor_Nerd — https://github.com/Alexsander720/continue

This repository currently contains the **static showcase and documentation**. The standalone Deck plugin, Windows helper,
readers, `i18n/` package and reader gate are not exported here yet. Work against files that exist;
do not invent missing runtime commands or report an unrun gate as passing.

## Useful contributions today

| Contribution | Where | What to include |
|---|---|---|
| Showcase bug / accessibility fix | `site/index.html`, `site/style.css`, `site/app.js` | Reproduction, screenshots and actual checks |
| Interface translation | `STR` in `site/data.js`; matching README / guides | EN / UK / RU parity, fallback and empty states |
| Documentation | Root Markdown and `docs/` | Working links, reproducible commands and accurate preview/v1 labels |
| Game request | [Game request](https://github.com/Alexsander720/continue/issues/new?template=game_request.md) | Appid, generic save location, useful fields |
| Reader research | Proposal following [AGENTS.md](AGENTS.md) | Stage provenance, field meaning and verified/unverified boundary |

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

## Readers when the public kit is available

[AGENTS.md](AGENTS.md) defines the target layout and card contract. **Its reader/gate commands are a future v1 contract**,
not runnable tools in this checkout. One game per reader PR; propose shared runtime changes separately.

- Copy saves and resources; never write to originals, launch games or restart Steam during research.
- Compare at least two stages of one playthrough, ideally three to five; establish meaning independently of the parser output.
- Record source URLs/dates and hashes. A changing number alone does not prove its meaning.
- Generate names and totals from the user's game data. No extracted localization, game assets or generated name tables in a reader PR.
- Hide unproven fields. Distinguish saved chapter from furthest unlock and current run from historical statistics.
- Do not upload raw saves with IDs, account names, personal paths or other private content. Describe the evidence first.
- When the kit ships, run its actual gate/tests and include real output and remaining limitations.

AI coding agents are welcome, with human evidence review. A confident answer is not validation.

## Bug reports

Use the [bug template](https://github.com/Alexsander720/continue/issues/new?template=bug_report.md).
For the showcase include browser, viewport, language, game/device view and steps. For a future installed runtime include
the actual release, platform and Steam client version. Remove personal identifiers from screenshots/logs;
do not attach a whole save directory.

## License

Code contributions are under GNU GPL v3 and the existing [NOTICE.md](NOTICE.md) terms. Retain attribution and identify
modified distributions. Third-party game/device media are not licensed by the code license.
