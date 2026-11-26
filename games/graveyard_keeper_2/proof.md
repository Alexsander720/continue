# Evidence record — Graveyard Keeper 2

Status: **proven (3 fields shown)**. Saves are the contributor's own, one playthrough, Steam builds 1.011.1 (stages 1–4)
and 1.012.9 (stages 5–7), Proton on Linux. Source files: `AppData/LocalLow/Lazy Bear Games/Graveyard Keeper 2/Steam_1*.info`
(JSON sidecars written by the game). The binary `Steam_1*.dat` world files were not parsed.

| field | s1 | s2 | s3 | s4 | s5 | s6 | s7 | game-visible evidence | source table | decision |
|---|---|---|---|---|---|---|---|---|---|---|
| day | 110 | 111 | 113 | 114 | 116 | 117 | 117 | HUD day counter | none needed (number) | proven, shown |
| saved_at | 20:53 | 21:08 | 21:26 | 21:32 (11-09) | 21:52 | 21:58 | 22:02 (11-26) | save slot timestamp | none | proven, used as observed_at |
| graveyardQuality | 28 | 28 | 28 | 28 | 23 | 23 | 23 | "Graveyard Quality" value in the graveyard panel; player read 23 at s7 | label from game strings | proven, shown, **nonmonotonic** |
| churchQuality | 36 | 36 | 36 | 36 | 36 | 36 | 29 | "Church Quality" value in the church panel; player read 29 at s7 | label from game strings | proven, shown, **nonmonotonic** |
| villageRep | 17 | 17 | 17 | 17 | 17 | 17 | 17 | HUD reputation was 0 in the old saves and 10 in a save written after s7 (22:09); the file says 17 in every case, with `repValue: false` | — | **hidden: field does not track the HUD reputation** |
| townCitizens | 20 | 20 | 20 | 20 | 20 | 20 | 20 | player read 20 at s7 (matches) | — | unproven (constant) |

Non-monotonic declaration: both quality values are state values the game recomputes from the current graves / church
state, not counters. They dropped between stages (28 → 23 across the 1.011.1 → 1.012.9 update, 36 → 29 within one session)
while the day counter kept growing, so `read()` declares them in `nonmonotonic` with the reason; the gate flags them for
human review instead of failing.

Label strings exist in the game's `resources.assets`: `Graveyard Quality`, `Church Quality` (EN), `Качество кладбища`,
`Качество церкви` (RU), `Friedhofsqualität`, `Kirchenqualität` (DE). The game marks graveyard quality with its own skull
sprite (`<sprite name="wskull">`), hence the icon subject.

Stages are the game's rolling backups of one slot (`_backup_3` oldest → `Steam_1` newest), copied into the ignored
`stages/` folder; stage 5 and the two day-117 stages show the quality fields moving independently of `day`.
