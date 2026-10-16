# Website asset sources

## Project SVG glyphs

The 53 white SVG glyphs in `plugin/assets/icons/` were created specifically for Continue?. The project owner confirmed
this provenance on 2026-10-13. These original project glyphs are covered by the project's GPL-3.0-or-later license and
its notices. No origin or license from Feather, Lucide or another icon library is claimed.

## steam-deck-oled.png

- Creator: Valve Corporation.
- Source page: https://www.steamdeck.com/en/press
- Original file: https://cdn.akamai.steamstatic.com/steamdeck/images/press/renderings/press_oled_front_english.png
- Retrieved: 2026-10-07.
- Format: original RGBA PNG, 2500 x 980. Image bytes have not been modified.
- Use: Steam Deck OLED body around the interactive Continue? demo. CSS crops the transparent padding and overlays the existing live interface on the display.
- Display alignment, in original pixels: body (336, 176, 1828, 725); screen (758, 236, 984, 614).

The hardware render belongs to Valve. The displayed Continue? interface is a composite for this independent project.

## share-card.png and favicon.svg

- `share-card.png`: 1200 x 630 browser capture composed from this project's existing interface, typography and the official Steam Deck render above. Generated 2026-10-07 for link previews; it shows the project name and identifies the v1 preview.
- `favicon.svg`: original pixel question-mark artwork in the project's black/gold palette, generated 2026-10-07.

## Additional game presentation assets

The thirteen added demo games reuse cached library art and local trailer loops. Individual background sources and save provenance are recorded in [DEMO_SOURCES.md](../DEMO_SOURCES.md). No game save or extracted localization archive is included.

## README banners, tours and screenshots

The three `docs/img/banner-<lang>.jpg` headers were refreshed on 2026-10-13 with the public alpha 0.1 status, as 1280 x 440 browser-rendered compositions
of the project's interface and the original Valve Steam Deck OLED body above. EN/RU show Until Dawn; UK shows Nine Sols
with its verified Ukrainian localization. The three tours and nine highlight captures were refreshed on 2026-10-07
with the same original device rendering. These compositions illustrate the interface; the hardware rendering and
game presentation media retain their respective owners' rights.
