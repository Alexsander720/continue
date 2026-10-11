# Run the Continue? showcase

**English** · [Українська](preview.uk.md) · [Русский](preview.ru.md)

The current checkout is a static browser presentation, with 20 curated save snapshots and Deck / PC views.
It does not connect to Steam, read your saves, install a plugin or launch a game.

## Start

Requirements: Git access to this repository, Python 3 and a modern browser. The repository is currently private,
so cloning requires an account with access. There are no pip/npm dependencies or API keys.

```sh
git clone https://github.com/Alexsander720/continue.git
cd continue
python tools/preview.py
```

Open **http://127.0.0.1:8811/**. Windows alternative: `py -3 tools/preview.py`;
macOS/Linux alternative: `python3 tools/preview.py`. Stop with **Ctrl+C** in that terminal.
Only the local computer can connect to this preview server.

If the port is occupied, use `python tools/preview.py --port 8813` and open **http://127.0.0.1:8813/**.
The server works from any current directory when invoked by its absolute script path.

## Explore

| Control | Result |
|---|---|
| Game covers / previous-next buttons | Select a curated snapshot |
| Deck / PC | Change the device layout |
| EN / UK / RU | Change interface language; unavailable game-name translations retain a labeled source language |
| Enlarge | Open the same demo in a dialog; Escape closes and returns focus |
| Background pause | Pause moving backgrounds |
| Catalog search and status filters | Find a game; three under-review readers expose only a verified subset |
| Tour | Watch the 40-second MP4 in the current interface language |
| Play / Continue | Show a demo response; no game is launched |

The browser includes controller mapping, but browser/gamepad support and physical hardware need separate testing.
Keyboard and touch controls are available. Reduced-motion preferences suppress automatic animation where supported.

## Media and troubleshooting

| Symptom | Explanation / action |
|---|---|
| No music button | Theme audio is intentionally excluded from Git; the control hides without a local theme file |
| Tour cannot seek on another static server | Use `tools/preview.py`, which supports HTTP byte ranges and maps tours from `docs/img/` |
| Some game names stay Russian/English | Verified source-language fallback; a translated interface does not invent native strings |
| ENSLAVED has no demo | Its reader is still under review; no verified demo was promoted |
| Browser cannot load the page | Keep the server terminal running; check its printed URL and port |
| Changes appear stale | Refresh the browser; inspect the console/network panel for a missing local asset |

Tours have one tracked copy in `docs/img/tour-<lang>.mp4`; the preview server maps `/media/tour-<lang>.mp4`
there without copying files. The Pages workflow copies them into its deployment artifact.
Name tables, personal saves and theme audio are not part of the Git checkout.

## Changes and hosting

Edit `site/index.html`, `site/style.css`, `site/app.js`, `site/data.js` or `site/store.js`, then refresh.
No build step. Check language, layout, focus and provenance after changes; see [CONTRIBUTING](../CONTRIBUTING.md).

The prepared Pages workflow deploys only on a public repository. Making the repository public, configuring Pages
and advertising its verified URL are separate owner decisions. Running the local preview does not publish anything.
