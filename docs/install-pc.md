# Windows / Big Picture installation

**English** · [Українська](install-pc.uk.md) · [Русский](install-pc.ru.md)

This guide covers the Windows Steam Big Picture package (`continue-pc-0.1.4-r19.zip`) released in [v0.1.4](https://github.com/Alexsander720/continue/releases/latest).
The installer and runtime code are present in the repository under `pc/`. The package has passed real-Steam checks on Windows 11 x64 on the owner's PC and in automated tests, while acceptance on clean Windows 10, ARM64, and with diverse antivirus suites is ongoing.
On 2026-10-13, installation, repair, a game card, native library tabs, settings, refusal and removal were also checked with real Steam Big Picture on Windows 11 x64, with Python and Steam debugging already available. A clean account without Python, Windows 10 and ARM64 are experimental; physical controller use is still pending. Treat this package as an alpha and close games before restarting Steam.

Requirements: Windows 10 or 11, Steam installed for the current Windows user, and Steam Big Picture. Administrator
rights are neither requested nor needed. Continue? uses only Python's standard library. If Python 3.10 or newer with
`pythonw.exe` is unavailable, setup downloads a pinned, publisher-signed embeddable Python package from python.org,
checks its published SHA-256, and installs it only under your user profile. It does not change PATH or the registry.

## Install: double-click, consent, restart Steam

1. Download `continue-pc-0.1.4-r19.zip` together with its checksum file `continue-pc-0.1.4-r19.zip.sha256` from the [latest release](https://github.com/Alexsander720/continue/releases/latest).
   Verify the checksum in PowerShell:
   ```powershell
   (Get-FileHash .\continue-pc-0.1.4-r19.zip).Hash -eq ((Get-Content .\continue-pc-0.1.4-r19.zip.sha256) -split '\s+')[0]
   ```
   If it outputs `True`, extract the whole ZIP to an ordinary local folder.
   Alternatively, you can build a local test candidate from repository source:
   ```bash
   python tools/build_pc_zip.py
   # or with an explicit version:
   python tools/build_pc_zip.py 0.1.4
   ```
   This creates `dist/continue-pc-<version>.zip` and `dist/continue-pc-<version>.zip.sha256`.
2. Double-click `Continue\setup.cmd` (or `Continue\pc\setup.cmd`). Windows may show a warning because the package is
   readable `.cmd`, `.ps1`, `.py`, and JavaScript rather than a signed installer EXE. Inspect the scripts if desired;
   do not grant administrator rights. `setup.cmd` uses `-ExecutionPolicy Bypass` only for its own local PowerShell script.
3. Read the debugging-port disclosure and answer yes only if you agree. Continue? creates the empty file
   `<Steam>\.cef-enable-remote-debugging`. On the next Steam start this exposes Steam's UI debugging endpoint at
   `127.0.0.1:8080`. It is not reachable directly from another computer, but **any process running as you on this PC can
   talk to the Steam interface while the flag is active**. This is the principal security trade-off of the PC version.
4. Let setup copy the app and register its per-user task. When asked about restarting Steam, first close every running
   game. Setup asks Steam to close normally only after your consent; it never force-kills Steam. You may answer no and
   restart Steam yourself later.
5. Open Big Picture and a supported game's page. The service waits and reconnects if Steam is closed, restarted, or not
   yet listening. A missing save or internet connection produces an empty/static fallback rather than changing the game.

Running setup again is a repair install: it preserves settings/data, replaces the application atomically, preserves
ownership of the Steam flag, and repairs the task. An installation manifest records the version, paths, selected Python,
task, and whether Continue? itself created the debugging flag.

## Settings in Big Picture

Open **Continue?** in Steam's main menu, or **…** on a game page. Library, Game card, Backgrounds, Music, Appearance and Connections contain the settings. Continue? library tabs start disabled; TabMaster keeps control when present.

Enable automatic music once for the library after explicit permission. Backgrounds and music prepare only for games you open. Hide save details globally or per game. The optional SteamGridDB key stays in your own profile.

[First use: music, quality and storage, cards, artwork and language](pc-first-start.md). The buttons, controller symbols and card styling preserve the original Big Picture presentation. Extra themes are under Appearance → More appearance options.

## What changes on the PC

| Item | Exact behavior |
|---|---|
| Steam debugging flag | Empty `<Steam>\.cef-enable-remote-debugging`; removed on uninstall only when Continue? created it and it is still empty |
| Steam debugging port | Steam exposes `127.0.0.1:8080` after a Steam restart; Continue? does not open this port itself |
| Continue media port | The service binds only `127.0.0.1:8793`; it serves approved media types only from `%LOCALAPPDATA%\Continue\data`, with Range support, strict Host/header/path/link checks |
| Scheduled task | Per-user `ContinueBigPicture`, at sign-in and every 10 minutes, `IgnoreNew`, limited privileges, running the recorded `pythonw.exe` without a console window |
| Application | `%LOCALAPPDATA%\Continue\app` |
| Settings/data/logs | `%LOCALAPPDATA%\Continue\settings.json`, `data`, and rotating `logs\bp.log` |
| Install record | `%LOCALAPPDATA%\Continue\install.json` |
| Optional Python | `%LOCALAPPDATA%\Continue\python`, only when no suitable existing Python was found |

The public build includes standalone Artwork, Music and Themes controls with the original presentation. The developer's hub, Deck SSH support and API key are excluded. Save cards are read locally by the same public `ddsaves`
readers as the Deck build. Descriptions and media metadata can come from Steam Store; HLTB/network/media failures are
non-fatal. `ffmpeg`/`ffprobe` arrive only with the optional media tools, downloaded with explicit consent into the
Continue? profile and verified by checksum; they are never installed system-wide.

### Third-party software and media

YouTube trailers and theme music are downloaded only after explicit consent, locally on this PC. The project ships no
third-party audio or video, and the user is responsible for following the services' terms and copyright. Helper programs
(the pinned Python from python.org, yt-dlp, Node and FFmpeg) are third-party software under their own licenses; they are
downloaded only with consent into the Continue? profile, and each archive is verified by checksum before use.

## Status and logs

Open PowerShell in the extracted or installed `pc` directory and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\status.ps1
```

The command reports the installed version, whether the exact recorded service is running, whether the task still belongs
to this installation, Steam/flag state, whether ports 8080 and 8793 answer as Steam/Continue?/another program, cache size,
the latest log path/line, and a suggested next action. It is read-only. The service log rotates in
`%LOCALAPPDATA%\Continue\logs` and remains usable under `pythonw.exe`, where stdout may not exist.

## Updates

A public installation checks GitHub Releases no more than once per day. It accepts only a newer stable
`continue-pc-<version>.zip` and its matching `.sha256`, validates HTTPS origins, size/path limits, SHA-256, and the public
`RELEASE.json`, then starts a detached helper. The live service exits, the helper unpacks beside the current app, swaps
the directory atomically, starts the new service, and waits for a fresh version/nonce health record. If startup fails, it
restores and restarts the previous app. Development checkouts without `RELEASE.json` do not update.

The public PC alpha package is published on GitHub Releases starting with v0.1.4 (`continue-pc-0.1.4-r19.zip`). Future updates will be checked automatically against subsequent releases once published.

## Remove

Run the installed uninstaller so it can use the recorded ownership information:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\Continue\app\pc\uninstall.ps1"
```

It stops only the recorded Continue? service, removes only the matching `ContinueBigPicture` task, and deletes the Steam
debugging flag only if Continue? created it and it is still empty. A pre-existing or later-edited flag is preserved. By
default it asks to delete data/cache, logs, and settings and shows the cache size; choose no to keep them. The copied app
and an embedded Python owned by Continue? are removed. The JavaScript already injected into a running Steam UI remains in
memory until Steam restarts, so close games and accept the offered normal restart or restart Steam manually.

## Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| “Steam was not found” | Steam is not installed for this Windows account or its HKCU path is missing | Install/start Steam once in this account, then run setup again |
| Flag exists, but port 8080 is closed | Steam was not restarted after the flag was created | Close games, fully exit Steam, and start it again |
| Port 8080 is “another program” | A non-Steam process owns it, or Steam returned an unrecognized target | Close the conflicting program; then restart Steam and run status again |
| Port 8793 is “another program” | Another service already uses Continue?'s media port | Close that program, then run setup again; do not terminate unknown processes blindly |
| Service/task missing | Task was removed, paths changed, Python was quarantined, or setup was interrupted | Check Windows Security and the last log, then rerun `setup.cmd` to repair |
| Big Picture has no Continue? panel | Steam has not loaded the flag, SharedJSContext is still starting, or the current Steam build changed | Wait briefly, check status/log, restart Steam; report the Steam version if it persists |
| Panel appears but save facts are empty | The game/slot is unsupported, save is elsewhere, or no save exists | Check the public reader list; Continue? never invents facts and never writes saves |
| Descriptions/trailers/HLTB are empty | Offline service, Store failure, consent/settings, low disk space, or no optional `ffmpeg` | The static card should still work; reconnect and retry later or inspect media status |
| Python download/hash/signature error | Network interception, incomplete download, or antivirus quarantine | Do not bypass the check; retry from a normal connection and inspect Windows Security |
| SmartScreen/antivirus warning | Alpha scripts are not code-signed; embedded Python itself is signed by python.org | Inspect the readable source and checksum. Do not disable protection globally or run as administrator |
| Uninstall says another installation owns the task | A task with the same name does not match `install.json` | Preserve it; restore the correct manifest or remove that unrelated task manually only after identifying it |

[Steam Deck installation](install-deck.md) · [Quick install](quick-install.md) · [Alpha tester checklist](alpha-testers.md) · [README](../README.md)
