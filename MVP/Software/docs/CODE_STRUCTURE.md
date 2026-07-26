# Code Structure

[← Back to Software README](../README.md)

## Which file to run

```bash
DISPLAY=:0 python finalV6.py
```

`finalV6.py` is the only file you execute directly. `style.py` is imported
by it automatically and never run on its own.

## File responsibilities

| File | Responsibility |
|---|---|
| `finalV6.py` | Everything: GUI screens, camera handling, the background-removal pipeline, the download/QR flow. One file, no other custom modules. |
| `style.py` | Colors and fonts only — imported constants, no logic. |

See [`pipeline-explained.md`](./pipeline-explained.md) for the visual diagram
and full reasoning behind the background-removal pipeline specifically.

## `finalV6.py` internal structure

The file is organized top-to-bottom in this order:

1. **Imports and constants** — library imports, tunable values (resolution,
   thresholds, timing), and `style.py` imports
2. **`PhotoboothApp` class `__init__`** — loads YOLO and both MediaPipe
   models once at startup (not per-photo — see below for why that matters),
   sets up the window
3. **Basic helpers** — shared UI utilities (buttons, popups, screen clearing)
4. **Camera** — opening/closing the webcam, starting/stopping the live feed
5. **Screen 1: Live Preview + Capture** — the countdown and photo capture logic
6. **Screen 2: Capture Review** — retake/proceed after taking the photo
7. **Screen 3: Processing** — this is where the actual background-removal
   pipeline runs (see [`pipeline-explained.md`](./pipeline-explained.md))
8. **Screen 4: Gallery** — browsing/selecting generated background variants
9. **Screen 5: Download** — zip, `rclone` upload, QR code generation
10. **Error handling / auto-delete / exit** — cleanup logic, including the
    15-minute auto-delete timer for local files and the uploaded Drive copy

Each section is marked with a comment banner in the file itself
(`# ===== SCREEN N: ... =====`), so you can jump to the relevant part
directly by searching for the section name.

## Why models are loaded once at startup, not per photo

`self.yolo_model`, `self.segmenter` (landscape MediaPipe), and
`self.segmenter_general` (general MediaPipe) are all created once in
`__init__` and reused for every photo taken during the whole session.
Loading a model is comparatively slow; running inference on an
already-loaded model is fast. Re-loading any of these per photo would make
every single capture noticeably slower for no benefit.
