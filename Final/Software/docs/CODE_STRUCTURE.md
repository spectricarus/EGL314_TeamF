# Code Structure

Which file to run, and how `finalphotobooth.py` is organized internally.

## Which file to run

`finalphotobooth.py` — this is the entire application; everything runs from this one file. `style.py` holds colours/fonts and is imported directly into it (see [file-connections.md](./file-connections.md)).

## How the file is organized

The constants at the top of the file (camera settings, colours-by-reference to `style.py`, the event banner text, timing/threshold values) are grouped under a `SETTINGS` banner — this is the first place to look if you need to change something like the event banner text, a timing value, or which GPIO pin the speaker uses, without needing to understand the rest of the code.

Below that, everything lives inside one class, `PhotoboothApp`, split into clearly labelled sections (each marked with a `# ====` banner comment in the file, so you can jump to them by searching):

| Section | What's in it |
|---|---|
| `__init__` | Startup: opens the window, starts the rclone daemon, sets up the speaker, loads the AI models |
| **BASIC HELPERS** | Small reusable utilities — resizing images for display, building buttons/popups consistently |
| **CAMERA** | Opening the camera, the background reader thread, the loading spinner |
| **AUDIO** | The three sound effects (countdown beep, capture sound, success chime) |
| **SCREEN 1: LIVE PREVIEW + CAPTURE** | The starting screen, the countdown, triggering a capture |
| **SCREEN 2: CAPTURED STILL + RETAKE / PROCEED** | The review screen after taking a photo |
| **SCREEN 3: PROCESSING** | Background removal and compositing against each theme |
| **SCREEN 4: OUTPUT GALLERY** | Browsing and selecting finished photos |
| **SCREEN 5: DOWNLOAD (ZIP → RCLONE → QR)** | Uploading and generating the QR code |
| **ERROR / AUTO DELETE / EXIT** | The error screen, local file cleanup, and shutdown |

Outside the class, at the very bottom of the file, is `fix_system_clock()` (corrects the Pi's clock at every startup — see [troubleshooting.md](./troubleshooting.md)) and the actual entry point that starts the app.

## If you're trying to find something specific

- **Change what the booth says or how it looks** → `SETTINGS` at the top, or `style.py`
- **Something camera-related is acting up** → the **CAMERA** section, and read [camera-reliability.md](./camera-reliability.md) first — this was the single biggest source of bugs in the whole project, and the reasoning behind how it's built now matters more than the code alone shows
- **Something about uploads/QR codes** → **SCREEN 5**, and [download-pipeline.md](./download-pipeline.md)
- **How the actual background-removal works** → [pipeline-explained.md](./pipeline-explained.md), which walks through it independent of the code
