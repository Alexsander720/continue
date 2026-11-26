# Evidence record — Graveyard Keeper 2

Status: **proven (4 fields shown)**. Saves are the contributor's own, one playthrough, Steam builds 1.011.1 (stages 1–4)
and 1.012.9 (stages 5–8), Proton on Linux (stages 1–4 are the Steam Cloud copies on a Steam Deck, 5–8 the PC's rolling
backups). Each stage folder holds the slot's `Steam_1.info` (JSON sidecar) and `Steam_1.dat` (binary world state,
uncompressed: entropy 3.7 bits/byte, UTF-16 field names of the C# serializer).

| field | s1 | s2 | s3 | s4 | s5 | s6 | s7 | s8 | game-visible evidence | source | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| day (.info) | 110 | 111 | 113 | 114 | 116 | 117 | 117 | 117 | HUD day counter | number | proven, shown |
| saved_at (.info) | 20:53 | 21:08 | 21:26 | 21:32 (11-09) | 21:56 | 21:58 | 22:02 | 22:09 (11-26) | save slot timestamp | — | proven, observed_at |
| graveyardQuality (.info) | 28 | 28 | 28 | 28 | 23 | 23 | 23 | 23 | "Graveyard Quality" panel; player read 23 at s7/s8; equals `wz_graveyard` in the .dat | label from game strings | proven, shown, **nonmonotonic** |
| churchQuality (.info) | 36 | 36 | 36 | 36 | 36 | 36 | 29 | 29 | "Church Quality" panel; player read 29 at s7/s8; equals `wz_church` in the .dat | label from game strings | proven, shown, **nonmonotonic** |
| happiness (.dat) | 0 | 3 | 3 | 0 | 5 | 5 | 5 | 10 | HUD thumbs-up counter: player read 0/20 at s4, 5/20 at s5–s7, 10/20 at s8 | game identifier `happiness` / `town_happiness` | proven, shown, **nonmonotonic** |
| villageRep (.info) | 17 | 17 | 17 | 17 | 17 | 17 | 17 | 17 | never matched the HUD; `repValue: false`; equals `village_REP` in the .dat (an NPC-style reputation) | — | **hidden** |
| townCitizens (.info) | 20 | 20 | 20 | 20 | 20 | 20 | 20 | 20 | player read 20 (matches) | — | unproven (constant) |

Non-monotonic declarations: the two quality values are state values recomputed from the current graves / church
(28 → 23 across the 1.011.1 → 1.012.9 update, 36 → 29 within one session). Happiness is a spendable town resource: the
game's own texts say "spend <sprite name=\"happiness\"> to get what you want" and it dropped 3 → 0 between s3 and s4.
`read()` declares all three in `nonmonotonic` with the reason, so the gate reports them for human review.

How `happiness` is read: the `.dat` stores typed variables as `\x01 <u32 len> <utf-16 name> \x1f\x01 \x05\0\0\0 "value" <f32>`.
The reader scans for that exact byte pattern with the name `happiness`; the value must occur exactly once with one value,
otherwise the field is `None` and hidden. Nothing else in the `.dat` is interpreted, and the file is never written.

The HUD shows happiness as `x/20`. No variable in the `.dat` carries that cap (no `happiness_max`, no `happiness_cap`;
`townCitizens` happens to be 20 but is not proven to be the denominator), so the card shows only the current value.

Label strings in the game's `resources.assets`: `Graveyard Quality`, `Church Quality` (EN), `Качество кладбища`,
`Качество церкви` (RU), `Friedhofsqualität`, `Kirchenqualität` (DE). Happiness has no text label in the HUD (icon only);
its identifier in the game data is `happiness` / `town_happiness`, so the fact label is the plain word "Happiness".

Stages are the game's rolling backups of one slot (`_backup_3` oldest → `Steam_1` newest), copied into the ignored
`stages/` folder (`.info` + `.dat` per stage, ~13 MB each).
