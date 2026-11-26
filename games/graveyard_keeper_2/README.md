# graveyard_keeper_2

Steam appid: `4358690`. Status: **proven** (day, graveyard quality, church quality); reputation and citizens hidden.

## Save locations

- Windows: `%USERPROFILE%\AppData\LocalLow\Lazy Bear Games\Graveyard Keeper 2\<slot>.info` and `<slot>.dat`
- Steam Deck / Proton: `steamapps/compatdata/4358690/pfx/drive_c/users/steamuser/AppData/LocalLow/Lazy Bear Games/Graveyard Keeper 2/`

The reader uses `ddsaves._common.proton_user(4358690)` to walk every Steam library and picks the newest `*.info`.
Only the small JSON sidecar is read; the 12 MB binary `.dat` is never opened. Steam Cloud syncs the sidecars, so a Deck
shows the same card as the PC.

## What the card shows

- `day` — in-game day (fact id `day`, label `facts.graveyard_keeper_2.day`).
- `graveyard_quality` — the game's "Graveyard Quality" value (declared non-monotonic: it can fall).
- `church_quality` — the game's "Church Quality" value (declared non-monotonic).
- `observed_at` — the save timestamp from `saveDateTime`.

## What stays hidden

- `villageRep`: the sidecar value stayed 17 while the HUD reputation went from 0 to 10 between saves, so its meaning is
  unknown and it is never displayed.
- `townCitizens`: matched the HUD (20) but was constant across all seven stages, so it stays unproven.

See `proof.md` for the stage table.

## Checks

```bash
python tools/run_game_tests.py graveyard_keeper_2
python tools/gate/check_cards.py graveyard_keeper_2
```
