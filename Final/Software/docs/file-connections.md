# File Connections & Running the App

## How the files connect

`finalphotobooth.py` imports directly from `style.py`:
```python
from style import (
    BG_COLOR, PANEL_COLOR, TEXT_COLOR, ...
)
```
This means `style.py` **must be in the same folder** as `finalphotobooth.py` — it isn't a package that gets installed, it's a plain file the main script reads from directly. If you move `finalphotobooth.py` somewhere without `style.py` alongside it, the app won't start at all.

Everything else the app touches gets created automatically the first time it runs, inside the same folder:

| Folder | What it's for |
|---|---|
| `assets/backgrounds/` | The theme images guests can composite onto — see [background-templates.md](./background-templates.md) |
| `assets/event_overlay.png` (optional) | A custom-designed banner graphic, if you have one — see [compositing-and-banner.md](./compositing-and-banner.md) |
| `saved_images/` | Where finished photos are written during a session — wiped automatically on every startup and shutdown, see [local-cleanup.md](./local-cleanup.md) |
| `qrcodes/` | Where generated QR code images are written — also wiped automatically, same mechanism |

## Running it

Once the environment is set up (see [environment-setup.md](./environment-setup.md)):
```bash
DISPLAY=:0 python3 finalphotobooth.py
```

## Quick troubleshooting

**It doesn't start at all, complaining about `style`** — `style.py` isn't in the same folder. See "How the files connect" above.

**It starts, but the window never appears / errors about no display** — missing `DISPLAY=:0`, or the display is running Wayland instead of X11. See [environment-setup.md](./environment-setup.md).

**Camera errors on startup** — the webcam may not have finished initializing yet if the app was launched right after boot. Wait ~30 seconds and try again. See [camera-reliability.md](./camera-reliability.md) if it's a recurring problem, not a one-off.

**Uploads/QR codes don't work** — check `rclone config` has a remote set up matching `RCLONE_REMOTE` in the code, and that there's an active wifi connection. See [download-pipeline.md](./download-pipeline.md).

For anything not covered here, see [troubleshooting.md](./troubleshooting.md), which covers real problems hit during development and how they were solved.
