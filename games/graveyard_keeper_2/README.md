# graveyard_keeper_2

Steam appid: `4358690`. Status: **proven** (day counter); quality/reputation fields unproven.

## Save locations

- Windows: `%USERPROFILE%\AppData\LocalLow\Lazy Bear Games\Graveyard Keeper 2\<slot>.info` and `<slot>.dat`
- Steam Deck / Proton: `steamapps/compatdata/4358690/pfx/drive_c/users/steamuser/AppData/LocalLow/Lazy Bear Games/Graveyard Keeper 2/`

The reader uses `ddsaves._common.proton_user(4358690)` to walk every Steam library and picks the newest `*.info`.
Only the small JSON sidecar is read; the 12 MB binary `.dat` is never opened.

## What the card shows

- `day` — in-game day (fact id `day`, label `facts.graveyard_keeper_2.day`).
- `observed_at` — the save timestamp from `saveDateTime`.

## What stays hidden

`graveyardQuality`, `churchQuality`, `villageRep`, `townCitizens` are decoded into `progress` but were constant across all
four stages, so they remain `unproven` and are not displayed. See `proof.md`.

## Checks

```bash
python tools/run_game_tests.py graveyard_keeper_2
python tools/gate/check_cards.py graveyard_keeper_2
```
