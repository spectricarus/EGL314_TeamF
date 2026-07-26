# Software — Photobooth Background-Removal App

[↑ Back to MVP overview](../README.md) (Hardware section is documented separately by teammate — linked from there)

This is the software half of the MVP: a Raspberry Pi kiosk app that captures a
photo, removes the background automatically, lets the user pick from several
background templates, and delivers the final photos via a QR code.

## What's in this folder

| File / Folder | What it is |
|---|---|
| [`finalV6.py`](./finalV6.py) | The main application — everything runs from this one file |
| [`style.py`](./style.py) | Colors, fonts, and layout constants used throughout `finalV6.py` |
| [`requirements.txt`](./requirements.txt) | Exact Python packages needed - `pip install -r requirements.txt` |
| [`docs/CODE_STRUCTURE.md`](./docs/CODE_STRUCTURE.md) | Which file to run, and how `finalV6.py` is organized internally |
| [`docs/file-connections.md`](./docs/file-connections.md) | How `finalV6.py` and `style.py` connect, and how to actually run the app |
| [`docs/dependencies.md`](./docs/dependencies.md) | Every library this project needs, and what each one is for |
| [`docs/environment-setup.md`](./docs/environment-setup.md) | Full from-scratch setup: conda environment, folder layout, camera, rclone |
| [`docs/pipeline-explained.md`](./docs/pipeline-explained.md) | The background-removal pipeline, with a visual diagram, and why it's built this way |
| [`docs/ui-flow.md`](./docs/ui-flow.md) | Screen-by-screen walkthrough of the app with screenshots |
| [`docs/background-templates.md`](./docs/background-templates.md) | Where template images live and how to swap them |

## Quick start

If you just want to get the app running, read these in order:

1. [`docs/environment-setup.md`](./docs/environment-setup.md) — sets up the Pi from a blank state
2. [`docs/CODE_STRUCTURE.md`](./docs/CODE_STRUCTURE.md) — which file to run and how it's organized
3. [`docs/file-connections.md`](./docs/file-connections.md) — how to actually launch it, plus troubleshooting

Everything else is reference material for understanding *why* things are built
the way they are, not required just to run the app.
