# Interactive demo evidence

Audit: 2026-10-07. The website contains 20 curated save snapshots, not live player telemetry. The first seven examples are retained from the earlier verified showcase. The following thirteen were added after a read-only audit of copied saves and existing game-derived tables. No saves, personal identifiers or extracted localization archives are included in the website.

| Game | Snapshot source | Shown subset |
|---|---|---|
| The Last of Us Part II Remastered | Author snapshot · 2026-09-22 | saved chapter, collectibles, save time |
| Hogwarts Legacy | Author snapshot · 2026-10-04 | saved location, house, level, Merlin Trials, collections, gold |
| Slay the Spire | Author snapshot · 2026-10-04 | act location, character, floor, HP, deck, relics, gold |
| Horizon Forbidden West | Author snapshot · 2026-10-04 | saved quest title, level, save time |
| NieR:Automata | Author snapshot · 2026-10-04 | saved chapter only |
| Life is Strange: Double Exposure | Author snapshot · 2026-10-04 | episode, scene title, album photos |
| UNDERTALE | Author snapshot · 2026-10-03 | area, LV, maximum HP, G, save time |
| Marvel's Spider-Man 2 | [MessyCelia](https://www.playground.ru/marvels_spiderman_2/cheat/marvels_spider_man_2_sohranenie_pered_missiej_s_venomom-1766985) · 2026-10-03 | saved story mission, level, story missions, Spider-Bots |
| SILENT HILL 2 | [FallenGhost](https://www.playground.ru/silent_hill_2/cheat/silent_hill_2_remake_poetapnye_sohraneniya_bez_smertej_tri_kontsovki-1728316) · 2026-10-02 | memos, maps, reserve handgun ammunition |
| Clair Obscur: Expedition 33 | [platapoop](https://steamcommunity.com/app/1903340/discussions/0/592895838866379576/#c592895838866380326) · 2026-10-03 | area, story stage, save time |
| Little Nightmares | [FANIS WEST](https://www.playground.ru/little_nightmares/cheat/little_nightmares_secrets_of_the_maw_chapter_1_sohranenie_savegame_sobrany_vse_kollektsionnye_predmety-825334) · 2026-10-03 | chapter, Nomes, statues, DLC collectibles |
| Little Nightmares II | [Вячеслав Рачков](https://www.playground.ru/little_nightmares_2/cheat/little_nightmares_ii_poshagovye_sohraneniya_bez_dopolnenij-1876715) · 2026-10-03 | saved chapter, save time |
| It Takes Two | [shurik-777_94](https://www.playground.ru/it_takes_two/cheat/it_takes_two_sohranenie_savegame_projdeno_3_glavy-1102742) · 2026-10-03 | saved chapter, chapter group, unlocked minigames |

Dates identify the selected snapshot or the date its fixture was collected, not the visitor’s last played date. The TLoU II example is an intermediate story slot, not the later completed autosave.

## Scope limits

- TLoU II: exact Russian chapter text and numeric fields agree between the game-generated JSON description, binary header and descriptor tag. Three story stages change from 58 to 80 to 170 collectibles. No chapter percentage, collectible total or inferred chapter number is displayed.
- Hogwarts Legacy: place is metadata for the selected save slot; Merlin total 95 is a fresh count of game database locations. No collection total or guessed quest is shown.
- Slay the Spire: values are from the selected Ironclad autosave; they replace stale Watcher values from a handoff.
- Horizon Forbidden West: title is the saved quest title. No geographic location or story percentage is inferred.
- NieR:Automata: only the chapter matched through native event data is shown. Numeric offsets and hand-translated Russian names remain excluded.
- Double Exposure: episode and scene names use the independently generated native table. Album photos include multiple photo types; no Polaroid total or timeline is claimed.
- UNDERTALE: original English area name is used. Maximum HP is labeled explicitly; it is not current health.
- Spider-Man 2: the documented MessyCelia series is used. An older fixture labeled owner had a mismatched Steam account identifier and was excluded as an owner example.
- Expedition 33: the displayed Russian strings are from the locally installed localization, including its Russian patch. The community fixture is labeled and linked.
- Silent Hill 2: ammunition means reserve ammunition; no ending or unnamed map is inferred.
- Little Nightmares II: saved replay chapter is shown, not the furthest unlocked chapter. No hats/remains are shown without their separate metadata.
- It Takes Two: the saved chapter is separate from the furthest unlock. The chapter and minigame totals come from the native chapter catalog.

ENSLAVED remains under review with no demo. BLEACH, Alan Wake, and the single-stage LEGO Harry Potter Collection save were not promoted. TEKKEN remains an example of recorded gameplay, without invented save facts.

## Presentation assets

Existing SteamGridDB/Steam art cached in the author’s GameHub library is reused. No paid analysis or new media download was requested. Videos were encoded from those local loops to silent H.264 1280-pixel copies. Newly copied artwork retains its original bytes; five existing catalog covers keep their earlier prepared versions. CSS controls placement. Publisher trailers are identified as trailers; they are not labeled as the author’s own gameplay.

| Game | Background source |
|---|---|
| The Last of Us Part II Remastered | [PlayStation France](https://www.youtube.com/watch?v=8ANI53dfzqg) |
| Hogwarts Legacy | [PlayStation](https://www.youtube.com/watch?v=1O6Qstncpnc) |
| Slay the Spire | [Launch Trailer](https://store.steampowered.com/app/646570/) |
| Horizon Forbidden West | Static game artwork |
| NieR:Automata | Static game artwork |
| Life is Strange: Double Exposure | Static game artwork |
| UNDERTALE | [UNDERTALE Trailer](https://store.steampowered.com/app/391540/) |
| Marvel's Spider-Man 2 | [PlayStation](https://www.youtube.com/watch?v=wOJaeD0Si04) |
| SILENT HILL 2 | [PlayStation](https://www.youtube.com/watch?v=pyC_qiW_4ZY) |
| Clair Obscur: Expedition 33 | [BANDAI NAMCO Europe](https://www.youtube.com/watch?v=lws5GGYV3gg) |
| Little Nightmares | [Little Nightmares Launch Trailer UNRATED](https://store.steampowered.com/app/424840/) |
| Little Nightmares II | [BANDAI NAMCO Europe](https://www.youtube.com/watch?v=MlX3kh1Y7Cg) |
| It Takes Two | [PlayStation](https://www.youtube.com/watch?v=2AysHTv7X8k) |
