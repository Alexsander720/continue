# Continue? — copyright and additional terms

Continue? — Copyright (C) 2026 Doctor_Nerd (https://steamcommunity.com/profiles/76561198038135489) — https://github.com/Alexsander720/continue

This program is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version (see `LICENSE`),
with the following additional terms permitted by section 7 of that license.

## Additional terms (GNU GPL v3, section 7)

**7(b) — Author attribution.** Every copy you convey, modified or not, must keep the attribution

> Continue? by Doctor_Nerd — https://github.com/Alexsander720/continue

visible in the program's *About* screen (the "Appropriate Legal Notices" of its interactive user interface)
and in the README of your distribution.

**7(c) — Origin.** Modified versions must be clearly marked as modified (for example "based on Continue? by Doctor_Nerd")
and must not be presented as the original program or as made by its author.

**7(e) — Name and logo.** This license grants no trademark rights in the name "Continue?" or its logo.
Modified distributions must clearly identify their origin as required by 7(c) above and must not use
the name or logo to imply endorsement by the original author. This does not limit the attribution
required above or the rights granted by the GNU GPL to copy, modify and convey the program.

The project's 53 original SVG glyphs in `assets/icons/` are covered by GPL-3.0-or-later, with the notices above.
The project owner confirmed on 2026-10-13 that these glyphs were created specifically for Continue?.

Public standalone packages also include the project's existing per-game icons and character silhouettes
in `assets/game_icons/` (PC: `pc/assets/game_icons/`). They are copied from the project's authored asset
set, with no personal save files. Game-derived character likenesses and symbols retain the respective
game owners' rights; the program license does not grant rights in the underlying game artwork.

## Not covered by the code license

- Game names, logos, artwork, music, video and text belong to their respective owners and are not licensed by
  the project's code license. The website showcase includes third-party presentation artwork and footage;
  sources are documented in `site/DEMO_SOURCES.md` and `site/img/ASSET_SOURCES.md`. Theme audio is excluded from Git.
- The public alpha checkout and Deck ZIP distribute the selected runtime string tables in
  `ddsaves/data/*.json` (including nested game directories), under `plugin/py_modules/` in the checkout
  and `Continue/py_modules/` in the ZIP. These contain game-derived place and chapter names, objectives,
  some mission descriptions, and provenance needed by the cards. They are not complete localization
  archives. Their game text remains the property of the respective rights holders, outside the code
  license; removal requests can be submitted through the project issue tracker. Personal saves and
  full extracted localization archives are not distributed. There is no blanket 160-character limit.
- Steam, Steam Deck and Big Picture are trademarks of Valve Corporation. Continue? is not affiliated with Valve.
- Per-game icons and character portraits in `assets/game_icons/` (PC: `pc/assets/game_icons/`) identify the games
  and are shown for informational, non-commercial purposes. The underlying likenesses and symbols remain the property
  of the respective rights holders; removal requests can be submitted through the project issue tracker.
- YouTube trailers and theme music are downloaded only after the user's explicit consent, locally on the user's own PC.
  The project distributes no third-party audio or video; the user is responsible for following the services' terms and
  copyright. Helper programs (the pinned Python from python.org, yt-dlp, Node and FFmpeg) are third-party software
  under their own licenses; they are downloaded only with consent into the user's Continue? profile, and each archive
  is verified by checksum before use. Provided license texts (for example Node and FFmpeg) travel with the tools.

The optional media tools have separate upstream licenses:

- **Node.js** — MIT; upstream: https://nodejs.org. The downloaded runtime retains its
  license and bundled dependency notices as `LICENSE_node.txt`.
- **FFmpeg builds by BtbN** — the license depends on the selected build. The pinned
  Windows and Linux `*-gpl-*` packages use GPL v3, retained as `LICENSE_ffmpeg.txt`;
  upstream builds and their licensing details: https://github.com/BtbN/FFmpeg-Builds.
- **yt-dlp** — The Unlicense, as declared by the downloaded Python zipapp;
  upstream: https://github.com/yt-dlp/yt-dlp. Bundled dependencies retain their own licenses.

## Third-party code

The Windows PC adapter also includes filled glyph paths from Google Material Icons, including
project adaptations. These are separate from the 53 original Continue? SVG files above.
Their Apache-2.0 license is in `pc/assets/licenses/Material-Icons-Apache-2.0.txt` in the PC package.
Source: https://github.com/google/material-design-icons.

The PC theme parser and class translations are adapted from CSS Loader
(https://github.com/DeckThemes/SDH-CssLoader), under GPL-3.0;
the license is retained in `pc/assets/licenses/CSS-Loader-GPL-3.0.txt`.
Packaged CSS themes retain their authors' LICENSE files in each `pc/assets/themes/` folder:
Chromahon/CapyMenu and CapyInputs by Mugen (GPL-3.0, https://codeberg.org/mugen/Chromahon),
Clean Gameview, No Home Edge Fade and Switch Like Home by SuchMeme (MIT), and Round by EMERALD (MIT).
PC adaptations and bundled default options preserve the existing Big Picture appearance.

The brightness bar overlay is adapted from **decky-brightness-bar** (https://github.com/rasitayaz/decky-brightness-bar).
Redistributions must keep this notice and the following license text:

BSD 3-Clause License

Copyright (c) 2024, Raşit Ayaz
Original Copyright (c) 2022-2024, Steam Deck Homebrew

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
