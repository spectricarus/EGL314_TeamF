# Software — Photobooth Final Build

[↑ Back to Final overview](../README.md)

This is the software half of the Final build: a Raspberry Pi kiosk app that captures a photo, removes the background automatically, lets the guest pick from several themed background templates, and delivers the final photo via a QR code — built on top of the MVP stage, with a large number of reliability and experience improvements made in the final stretch before the event.

## What's in this folder

| File / Folder | What it is |
|---|---|
| [`finalphotobooth.py`](./finalphotobooth.py) | The main application — everything runs from this one file |
| [`style.py`](./style.py) | Colours, fonts, and layout constants used throughout `finalphotobooth.py` |
| [`requirements.txt`](./requirements.txt) | Exact Python packages needed — `pip install -r requirements.txt` |
| [`assets/backgrounds/`](./assets/backgrounds) | The live background templates the app actually reads from |
| [`assets/screenshots/`](./assets/screenshots) | Screenshots referenced from `docs/ui-flow.md` |
| [`docs/environment-setup.md`](./docs/environment-setup.md) | Full from-scratch setup: OS, conda environment, camera, speaker, rclone |
| [`docs/dependencies.md`](./docs/dependencies.md) | Every library this project needs, and what each one is for |
| [`docs/CODE_STRUCTURE.md`](./docs/CODE_STRUCTURE.md) | Which file to run, and how `finalphotobooth.py` is organized internally |
| [`docs/file-connections.md`](./docs/file-connections.md) | How `finalphotobooth.py` and `style.py` connect, and how to actually run the app |
| [`docs/pipeline-explained.md`](./docs/pipeline-explained.md) | The background-removal pipeline, and why it's built this way |
| [`docs/ui-flow.md`](./docs/ui-flow.md) | Screen-by-screen walkthrough of the app |
| [`docs/background-templates.md`](./docs/background-templates.md) | Where template images live and how to swap them |
| [`docs/architecture.md`](./docs/architecture.md) | Why the app uses multiple background threads, and what runs where |
| [`docs/camera-reliability.md`](./docs/camera-reliability.md) | The biggest problem in the whole project — every approach tried, and what actually fixed it |
| [`docs/download-pipeline.md`](./docs/download-pipeline.md) | How photos get uploaded and turned into a QR code |
| [`docs/local-cleanup.md`](./docs/local-cleanup.md) | Why the old 15-minute auto-delete timer was removed, and how cleanup actually works now |
| [`docs/compositing-and-banner.md`](./docs/compositing-and-banner.md) | The event banner, and how it's layered onto each photo |
| [`docs/troubleshooting.md`](./docs/troubleshooting.md) | Known issues hit during development, and known accepted limitations |

## Quick start

If you just want to get the app running, read these in order:

1. [`docs/environment-setup.md`](./docs/environment-setup.md) — sets up the Pi from a blank state
2. [`docs/dependencies.md`](./docs/dependencies.md) — what's actually being installed and why
3. [`docs/CODE_STRUCTURE.md`](./docs/CODE_STRUCTURE.md) — which file to run and how it's organized
4. [`docs/file-connections.md`](./docs/file-connections.md) — how to actually launch it, plus quick troubleshooting

Everything else is reference material for understanding *why* things are built the way they are, not required just to run the app — [`docs/camera-reliability.md`](./docs/camera-reliability.md) in particular is worth reading if you want to understand the single biggest engineering problem this project ran into and how it was actually solved.
