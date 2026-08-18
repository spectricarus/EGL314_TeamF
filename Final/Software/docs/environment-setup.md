# Environment Setup

Full from-scratch setup for running this on a blank Raspberry Pi. If you just want the short version, see the [Software README](../README.md) — this page is for actually recreating the environment, including the parts that aren't obvious from the code alone.

## 1. Operating system

**Raspberry Pi OS**, with the display running **X11, not Wayland**. Some Pi setups default to Wayland, which caused real, hard-to-diagnose touchscreen problems during development (touch position tracked correctly, but taps didn't register as clicks — a classic symptom of this specific mismatch).

Check which one you're on:
```bash
echo $XDG_SESSION_TYPE
```
Should say `x11`. If it says `wayland`:
```bash
sudo raspi-config
```
→ Advanced Options → Wayland → X11 → reboot.

## 2. Python environment (conda)

This project runs inside a **conda environment**, not the system Python — this matters, because installing dependencies into the wrong Python environment is one of the most common reasons a "correctly installed" setup still doesn't run.

```bash
conda create -n photobooth_usb python=3.11
conda activate photobooth_usb
```

*(If you're picking up this project on a Pi where the environment already exists, just `conda activate photobooth_usb` — check `conda env list` if you're not sure it's there.)*

With the environment active, install dependencies — see [dependencies.md](./dependencies.md) for what each one is for:
```bash
pip install -r requirements.txt --break-system-packages
```

## 3. Folder layout

The app expects to live in its own folder (e.g. `~/photobooth/`), with `finalphotobooth.py` and `style.py` side by side — `style.py` is imported directly by the main file, so it has to be in the same folder, not just installed as a package.

Background images go in `assets/backgrounds/` inside that same folder — see [background-templates.md](./background-templates.md).

## 4. Camera

The app expects the webcam at `/dev/video0` (the `CAMERA_DEVICE` constant near the top of `finalphotobooth.py`). Plug in the USB webcam and confirm it shows up there before running the app:
```bash
ls /dev/video0
```
If it's missing right after boot, wait ~30 seconds — some Pi setups need a moment for USB devices to finish initializing, and launching the app too early can cause camera errors that a short wait resolves on its own.

## 5. Speaker (GPIO)

Wire the speaker's Signal pin to GPIO 18 (BCM numbering — physical pin 12), with GND and VCC connected normally. The app is written to keep working with no sound at all if the speaker isn't connected or `RPi.GPIO` isn't installed, so this isn't a hard blocker to get running — just confirm the wiring against `SPEAKER_PIN` in the code if you expect sound and aren't getting any.

## 6. rclone (for photo uploads)

Install `rclone` itself (this is a separate system tool, not a Python package — see [rclone.org](https://rclone.org)), then configure a remote once:
```bash
rclone config
```
Follow the prompts to connect a Google Drive account. The remote name you choose needs to match `RCLONE_REMOTE` near the top of `finalphotobooth.py` (currently set to `gdrive`) — if you name it something else, either update the code to match or rename the remote.

## 7. Running it

With the conda environment active:
```bash
DISPLAY=:0 python3 finalphotobooth.py
```

The `DISPLAY=:0` is important if you're launching from a script, a terminal session that isn't the Pi's own desktop session, or over SSH — without it, the app can fail to find a display to draw the GUI on at all, even though everything else is set up correctly.

## What to expect on first launch

The first run will take noticeably longer than normal — the YOLO model gets downloaded and converted to a faster format (ONNX) automatically the first time, which only happens once. Subsequent launches are much quicker.
