# AGENTS.md — add a game to Continue?

This file is written for AI coding agents (Claude Code, Codex, Gemini CLI, …) and for the humans driving them.
Read it fully before touching anything. The goal: **a new game shows real, proven progress on its Continue? card.**

> Status: The runtime plugin (`plugin/py_modules/ddsaves/`), Windows backend (`pc/`), and contribution tools
> (`tools/new_game.py`, `tools/run_game_tests.py`, `tools/gate/check_cards.py`) are present in this repository.
> New game additions use the `games/<slug>/` layout described below. Note that `games/<slug>/` is a contribution
> sandbox and does not integrate into the runtime plugin automatically; maintainers review and export verified
> readers into release builds.

## What you deliver

Start by scaffolding the contribution skeleton:

```bash
python tools/new_game.py <slug> <appid>
```

This creates:

```
games/<slug>/
  reader.py      save reader: read(path_or_dir) -> card dict (stdlib only)
  tables.py      generator: builds data/<slug>.<lang>.json from the user's own game files
  stages.json    the save stages used as proof (see "Proof")
  icons.json     one entry per fact id: what the icon shows + a reference description (no images required)
  README.md      where the saves live (Windows / Steam Deck / Proton), what is proven, what is not
  test_reader.py golden values you checked by meaning, not copied from the reader's own output
```

`<slug>` is lowercase with underscores (`nine_sols`, `until_dawn`). One pull request = one game.

## The card contract

```python
def read(path_or_dir=None) -> dict:
    return {
        "place": "MEMENTO MORI",          # or None: location / chapter title exactly as the game shows it
        "chapter": None, "objective": None,
        "progress": {...},                # every raw field you decoded
        "facts": [                        # what the card shows, in display order
            {"id": "totems", "icon": "totems", "value": "1 / 36"},
        ],
        "proven": ["place", "totems_count", ...],
        "unproven": [...],                # decoded but not proven: never shown
        "fact_sources": {"totems": "totems_count"},   # fact id -> proven field
    }
```

- **Fact ids are stable English identifiers** (`totems`, `clues`, `butterfly_effects`). Labels come from
  `i18n/<lang>.json` under `facts.<slug>.<id>`, so add the `en` label (and others you know).
- Names inside values (places, items, characters) come **only** from `data/<slug>.<lang>.json` produced by `tables.py`.
- The reader must work on Windows **and** on the Steam Deck: search Proton prefixes
  (`steamapps/compatdata/<appid>/pfx/drive_c/users/steamuser/…`) and Windows `Documents` / `AppData` / `Saved Games`.
  Never hard-code a drive letter, a user name or a Steam library path. Use the helpers in `ddsaves/_common.py`.
- Standard library only. The Deck has no `pip` for plugins.

## Proof (the rule everything else depends on)

1. **A field is a fact only if it changes between save stages in the right direction.** Collect at least
   two stages of the same playthrough (ideally 3–5): your own saves at different points, backup slots, Deck vs PC copies.
   Numbers that should only grow must never decrease along the stage order. Values that are constant in every
   stage are *unproven*, however plausible they look.
2. **Names only from the game's files.** Localisation tables, data tables, enums in the game's own assets.
   Not from memory, not from a wiki. If the game has no such string, the card shows nothing.
3. **No invented totals.** "12 / 40" needs the 40 from the game data, not from a wiki guide.
4. **Encrypted or compressed?** Measure the entropy of the first ~200 KB: below ~6 bits/byte is an open format,
   above ~7.8 is compression or encryption (try zlib / zstd / lz4 / Oodle first).

Run reader unit tests:

```bash
python tools/run_game_tests.py <slug>
```

(Note: this command requires an existing `games/<slug>` directory containing `test_reader.py`; it does not run against legacy readers in `plugin/py_modules/ddsaves/`).

Then run the proof gate:

```bash
python tools/gate/check_cards.py <slug>
```

It runs your reader on every stage and checks mechanically:
- every proven field takes ≥ 2 values;
- every fact points to a proven field;
- every word shown on the card exists in the generated tables;
- no display text is typed into the code.

**A pull request without passing tests and a passing gate is not reviewed.**

## Hard rules

- **Read-only.** Copy saves before parsing. Never write to a save, a game folder or Steam's files.
- **Do not launch games, restart Steam or kill processes**: the user may be playing.
- **Commit no game content in a game contribution.** No full extracted localisation, assets, audio or video,
  or new `data/*.json` generated from game files. Commit the *generator*. The public alpha already includes
  selected runtime tables in `plugin/py_modules/ddsaves/data/*.json` (including nested game directories).
  Only the release maintainer may update this selection for card runtime needs, with source provenance
  and the third-party text declaration in `NOTICE.md`; it is not permission to add full archives.
  Saves used as proof stay on your machine unless they are
  your own and contain no personal data; downloaded saves go with a `SOURCE.md` (URL, stage).
- **Do not break or bypass encryption or DRM.** If the save or the game data is encrypted, stop and report the game
  as `blocked`.
- **Downloaded saves only.** No executables, trainers or scripts from the internet.
- Do not edit shared code (`ddsaves/_common.py`, `plugin/`, `pc/`) in a game PR. Propose such changes separately.

## Icons

Continue? icons are flat white silhouettes on transparency, one subject per icon, no background, no text:
quiet, like the Steam UI. You do **not** need to make images. Fill `icons.json`:

```json
{ "totems": { "subject": "a carved wooden totem pole fragment", "reference": "the totem item in the game's journal" } }
```

`python tools/icons/prompts.py <slug>` turns it into ready-made prompts for ChatGPT or Gemini.
A human generates the images and `tools/icons/import.py` cleans and sizes them.

## Report back

End with a short summary for the human:
- what the card now shows;
- which fields are proven and on how many stages;
- what is unproven or blocked and why;
- the gate output.
