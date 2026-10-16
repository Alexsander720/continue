# Install the public alpha on Steam Deck

**English** · [Українська](install-deck.uk.md) · [Русский](install-deck.ru.md)

> This is an alpha for testers, not a Decky Store release. Windows and Steam Big Picture support comes later.

## Before you install

- Install a current Decky Loader using its official instructions.
- Download `continue-deck-<version>.zip` from the [latest release](https://github.com/Alexsander720/continue/releases/latest). `<version>` is the version shown on that release page. Do not unpack it.
- The release also contains `continue-deck-<version>.zip.sha256`. Decky receives the same SHA-256 through Continue?'s update check; a release without a matching checksum is not offered as an update.
- Keep a supported game's save available locally if you want to test save reading. Continue? only reads it.

## Install from the ZIP

1. Switch to Gaming Mode and open Decky from the Quick Access menu (`…`).
2. Open **Decky → Settings → Developer**.
3. Select **Install from ZIP**, choose `continue-deck-<version>.zip`, and confirm.
4. Wait for Decky to finish. Open the Decky plugin list and confirm that **Continue** shows the version you downloaded. (Decky cannot use a `?` in a plugin name, so its list shows “Continue”; the plugin itself says “Continue?”.)
5. Open a game page. Use Continue?'s `…` menu to select the interface options, background source, preset, cache budget, and brightness bar.

If the Decky version presents one combined **Install from URL/ZIP** action, choose it and then select the ZIP branch.

## Install from a URL

1. In the release page, copy the direct URL of the `continue-deck-<version>.zip` asset—not the web page URL.
2. Open **Decky → Settings → Developer → Install from URL/ZIP**.
3. Paste the direct HTTPS ZIP URL, confirm, and wait for Decky.
4. Confirm that **Continue** shows the version you downloaded in the plugin list, then open a game page.

Do not use a branch/archive URL or the `.sha256` URL in the ZIP field.

## First-run choices

- **Background source:** Steam is the default. YouTube and theme-music downloads show separate consent dialogs; declining leaves those sources disabled. Steam Game Recording is local and only works when a suitable recording exists.
- **Preset:** Light is the default. Light and Balanced cap generated video at 720p; Maximum caps it at 1080p. Light suppresses Home video and uses a still image on battery. Maximum permits video everywhere.
- **Cache:** choose 1, 2, 4, or 8 GB separately from the preset. Old background files are evicted within that budget.
- **Library tabs:** turn on **Continue? tabs** in the plugin settings, then reopen the library to see **Installed** on this device and **From PC** for other connected Steam clients. The option is off by default and stays inactive while TabMaster is present.
- **Language:** the interface follows Steam and supports English, Ukrainian, and Russian. Game text follows the proof available in that game's files.
- **Brightness:** Continue?'s brightness bar can be disabled. If the separate Brightness Bar plugin is active, Continue? avoids drawing a duplicate.

## Updates

Continue? checks the GitHub release feed at most once a day and only marks an update available when both the release ZIP and its SHA-256 are present. The update action hands installation to Decky; the plugin does not overwrite itself. After an update, Decky may keep showing its progress dialog and not list the new version straight away — close the dialog and restart the Steam client (or reboot the Deck) once. If the check fails, the installed version keeps working and you can retry from the version row later.

## If installation fails

1. Confirm that Decky itself opens and that **Settings → Developer** is available.
2. Re-download the ZIP; do not rename, unpack, or recompress it.
3. If using a URL, verify that it points directly to the `.zip` asset and begins with `https://`.
4. Restart the Steam client once, then retry through Decky.
5. If Continue? appears but a page is incomplete, open its `…` menu and choose **Collect a developer report**. Review the sanitized JSON, save the ZIP, and follow the [alpha tester guide](alpha-testers.md).

Do not attach saves, personal Steam logs, or screenshots containing account details unless the developer explicitly asks for a redacted example.

## Remove

1. Open Decky from the Quick Access menu.
2. Open Decky's plugin management/settings view, select **Continue?**, and choose **Uninstall**.
3. Confirm and let Decky remove the plugin. Restart the Steam client if an old panel remains visible.

Uninstalling must not modify saves or game files. If you want a diagnostic report, create it before uninstalling.

[Alpha tester checklist](alpha-testers.md) · [README](../README.md) · [Roadmap](ROADMAP.md)

## Music setup

Open Continue? in Decky's menu → **Music** → **Enable automatic music**. First setup: ~180 MB, about half a minute; connect the charger at 30% battery or below. Confirm the optional tools download, then individual themes. Tools stay inside Continue? data; SteamOS and PATH are unchanged. Themes prepare for games you open. Choose volume and playback on Home/game pages. For the open game, choose Automatic theme or No music. After setup, audio preparation works on battery above 15%; video preparation still waits for charging. Downloads pause during a running game. If preparation fails, use Try again or Update music downloader; a verified previous downloader can be restored. The new flow is a local 0.1.4 candidate; actual Deck audio/controller/suspend acceptance is pending.
