# Environment Setup

[← Back to Software README](../README.md)

This document walks through setting up a Raspberry Pi from a blank state to
run this app. Follow these steps in order.

## 1. Create the conda environment

This project runs inside a dedicated conda environment (not the system Python)
to keep its dependencies isolated from the rest of the Pi.

```bash
conda create -n photobooth_usb python=3.11
conda activate photobooth_usb
```

Every time you open a new terminal to work on this project, you need to run
`conda activate photobooth_usb` again first — the environment doesn't stay
active between terminal sessions.

## 2. The `photobooth` folder

All project files live in a folder called `photobooth` (typically
`~/photobooth` on the Pi). This isn't a strict technical requirement — the app
would work from any folder name — but keeping it consistent matters because:

- Several relative paths in the code (backgrounds folder, saved images folder,
  QR code folder) are built relative to wherever the script is run from
- It keeps the setup reproducible and matches what's documented here

```bash
mkdir -p ~/photobooth
cd ~/photobooth
```

Copy `finalV6.py` and `style.py` into this folder.

## 3. Install dependencies

With the `photobooth_usb` environment active:

```bash
pip install mediapipe --break-system-packages
pip install ultralytics --break-system-packages
pip install opencv-python --break-system-packages
pip install numpy --break-system-packages
pip install pillow --break-system-packages
pip install qrcode --break-system-packages
```

See [`dependencies.md`](./dependencies.md) for what each of these is actually
for.

**Note on `--break-system-packages`**: this flag is needed on Raspberry Pi OS
because pip normally refuses to install packages system-wide to avoid
conflicting with OS-managed packages. Since we're installing into the
dedicated `photobooth_usb` conda environment (not the system Python), this is
safe here.

## 4. Install rclone (for the download/QR feature)

```bash
sudo apt install rclone -y
rclone config
```

`rclone config` walks you through connecting a Google Drive account
interactively — choose "Google Drive" as the storage type and follow the
prompts. Once done, note the **remote name** you gave it (e.g. `gdrive`) — you
need this to match `RCLONE_REMOTE` near the top of `finalV6.py`.

Test the connection works before relying on it:

```bash
echo "test" > test.txt
rclone copy test.txt gdrive:Photobooth
```

(replace `gdrive` with your actual remote name)

## 5. Camera setup

The app expects a USB webcam accessible via V4L2. Confirm it's detected:

```bash
ls /dev/video*
v4l2-ctl --list-devices
```

If the camera doesn't appear at `/dev/video0`, check `CAMERA_DEVICE` near the
top of `finalV6.py` and update it to match whatever device path your camera
actually shows up as.

## 6. Time sync

Google Drive uploads (via rclone) require the Pi's system clock to be
genuinely correct — not just displaying a plausible time, but actually
synced. On first boot, or on a network that blocks NTP traffic, this can fail
silently. Check with:

```bash
timedatectl status
```

Look for `System clock synchronized: yes`. If it says `no`, see the
troubleshooting note in [`file-connections.md`](./file-connections.md) for
how to force it.

## 7. You're ready

At this point you should be able to run the app — see
[`file-connections.md`](./file-connections.md) for how to actually launch it.
