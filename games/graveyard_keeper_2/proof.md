# Evidence record — Graveyard Keeper 2

Status: **proven (1 field shown)**. Saves are the contributor's own, Steam build 1.011.1, Proton on Linux.
Source files: `AppData/LocalLow/Lazy Bear Games/Graveyard Keeper 2/Steam_1*.info` (JSON sidecars written by the game).
The binary `Steam_1*.dat` world files were not parsed.

| field | stage 1 | stage 2 | stage 3 | stage 4 | game-visible evidence | source table | decision |
|---|---|---|---|---|---|---|---|
| day | 110 | 111 | 113 | 114 | HUD day counter | none needed (number) | proven, shown |
| saved_at | 20:53 | 21:08 | 21:26 | 21:32 (2026-11-09) | save slot timestamp | none | proven, used as observed_at |
| graveyardQuality | 28 | 28 | 28 | 28 | — | — | unproven (constant) |
| churchQuality | 36 | 36 | 36 | 36 | — | — | unproven (constant) |
| villageRep | 17 | 17 | 17 | 17 | — | — | unproven (constant) |
| townCitizens | 20 | 20 | 20 | 20 | — | — | unproven (constant) |

Stages are the game's own rolling backups of one slot (`_backup_3` oldest → `Steam_1` newest), copied into the ignored `stages/` folder.
