# How the Files Connect & How to Run It

[← Back to Software README](../README.md)

## The two files

- **`finalV6.py`** — the entire application. All logic, all screens, the full
  background-removal pipeline, camera handling, and the download/QR flow live
  in this one file.
- **`style.py`** — a small file of constants only: colors (e.g. `BG_COLOR`,
  `CAPTURE_COLOR`), fonts (e.g. `TITLE_FONT`, `BUTTON_FONT`), imported at the
  top of `finalV6.py` with:

  ```python
  from style import (
      BG_COLOR,
      PANEL_COLOR,
      TEXT_COLOR,
      ...
  )
  ```

  It exists purely to keep the visual styling in one place, separate from the
  application logic — if you want to re-theme the app (different colors,
  different fonts), this is the only file you need to touch.

Both files must be in the **same folder** for the `import` to work.

## Folder structure the app expects at runtime

```
photobooth/
├── finalV6.py
├── style.py
├── assets/
│   └── backgrounds/       ← background template images go here
├── saved_images/          ← created automatically, holds each session's output
├── qrcodes/               ← created automatically, holds generated QR codes
```

The `assets/backgrounds/` folder needs to exist with at least one image in it
before the app can generate any output — see
[`background-templates.md`](./background-templates.md).

## Running the app

```bash
conda activate photobooth_usb
cd ~/photobooth
DISPLAY=:0 python finalV6.py
```

The `DISPLAY=:0` part is necessary if you're running this over SSH/PuTTY
rather than directly on the Pi's own desktop — it tells the app which physical
screen to draw the GUI on.

## Troubleshooting: download fails with a certificate/time error

If the download step fails and the Pi's system clock isn't actually synced
(check with `timedatectl status`), force it manually:

```bash
sudo apt install ntpdate -y
sudo ntpdate -u time.google.com
```

If that fails too (some networks block NTP traffic specifically), fall back to
setting the time from a normal HTTPS request instead, which almost never
gets blocked:

```bash
sudo date -s "$(curl -sI https://google.com | grep -i '^date:' | cut -d' ' -f2-)"
```

## Troubleshooting: camera fails to open

```bash
ls /dev/video*
```

If your camera isn't at `/dev/video0`, update the `CAMERA_DEVICE` constant
near the top of `finalV6.py` to match the correct path.
