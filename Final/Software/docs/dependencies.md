# Dependencies

Every library this project needs, and what it's actually for. For *how* to install these (conda environment, `pip install -r requirements.txt`), see [environment-setup.md](./environment-setup.md) — this page is about *why* each one is here.

| Package | What it's for |
|---|---|
| `opencv-python` (`cv2`) | Reading frames from the camera, image resizing/manipulation, drawing the countdown numbers |
| `numpy` | The underlying array/image math almost everything else builds on |
| `mediapipe` | Person segmentation — figuring out which pixels are "person" vs "background" |
| `ultralytics` | YOLO, used to detect where each person is in the frame before segmentation runs |
| `Pillow` (`PIL`) | Higher-quality text rendering (used for the event banner) and general image format handling |
| `qrcode` | Generating the QR code shown to guests |
| `RPi.GPIO` | Controlling the speaker via the Pi's GPIO pins |

**Not a Python package — a separate system tool**: `rclone`, used to upload photos to Google Drive and generate a shareable link. Installed and configured separately; see [environment-setup.md](./environment-setup.md).

## Things the app degrades gracefully without

A few of these are wrapped in a way that lets the app keep running, just with reduced functionality, if they're missing:

- **`ultralytics` (YOLO) missing or fails to load** — falls back to running MediaPipe on the whole photo directly instead of per-person crops. Still works, just without the extra accuracy the crop-first approach normally provides.
- **`RPi.GPIO` missing, or the speaker not wired up** — the app runs completely silently instead of crashing.

Everything else (`opencv-python`, `numpy`, `mediapipe`, `Pillow`, `qrcode`) is a hard requirement — the app won't start without them.
