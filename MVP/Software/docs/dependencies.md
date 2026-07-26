# Dependencies & Libraries

[← Back to Software README](../README.md)

Every external library this project uses, and what it's actually responsible for.

| Library | What it's for |
|---|---|
| **mediapipe** | Provides `SelfieSegmentation` — the core model that separates a person from the background. Used twice in this project with two different settings: once tuned for full-body framing, once tuned for close-up framing (specifically for refining hair). |
| **ultralytics** (YOLO) | Provides YOLO11n, used purely for *detecting where each person is* in the photo (bounding boxes only, not segmentation). This is what makes the app handle group photos reliably — see [`pipeline-explained.md`](./pipeline-explained.md) for why. |
| **opencv-python** (`cv2`) | Camera capture, image resizing/cropping, color space conversion, and general image processing throughout the pipeline. |
| **numpy** | Array/matrix math underlying the alpha-mask blending logic — combining masks from multiple people, feathering edges, etc. |
| **Pillow** (`PIL`) | Image format conversion between OpenCV's format and what other libraries (like the YOLO/MediaPipe interfaces) expect. |
| **qrcode** | Generates the QR code shown on the download screen, from the Google Drive share link. |
| **tkinter** | Built into Python already — the GUI framework the entire touchscreen interface is built with. No separate install needed. |
| **rclone** (not a Python library — a separate command-line tool) | Uploads the selected photos to Google Drive and generates the shareable link used for the QR code. Called from the app via `subprocess`. |

## Why some things were tried and removed

A few libraries appear in earlier development but are **not** part of the
final app, worth knowing if you see references to them in old commits or
notes:

- **rembg** — tested extensively for background removal quality, ultimately
  not used in the final version (too slow, and gave inconsistent results on
  identical input across repeated runs)
- **pymatting** — tested for true alpha matting (a formal mathematical
  technique for soft edges), ultimately not used — MediaPipe's own native
  output, used correctly, turned out simpler and equally good
