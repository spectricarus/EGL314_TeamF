# UI Flow

[← Back to Software README](../README.md)

**Note: Camera covered for privacy reasons**

## 1. Live Preview

![\[screenshot: live-preview.png\]](../assets/screenshots/live-preview.png)

Continuous camera preview. Status text sits along the top of the screen.
Pressing **CAPTURE** starts a 3-2-1 countdown overlaid on the live feed;
the photo is taken automatically the moment it reaches zero.

## 2. Capture Review

![\[screenshot: capture-review.png\]](../assets/screenshots/capture-review.png)

Shows the just-captured photo before any processing happens, so the user
can catch an obviously bad shot early. **RETAKE** returns to the live
preview to try again; **PROCEED** sends the photo into the background-removal
pipeline.

## 3. Processing

![\[screenshot: processing.png\]](../assets/screenshots/processing.png)

The first, unpredictable-duration stage: the captured photo is analyzed once
here — this is where YOLO finds each person and MediaPipe computes the
background-removal mask (see
[`pipeline-explained.md`](./pipeline-explained.md) for the full pipeline).
Shows an indeterminate progress bar, since this step's actual duration can't
be known in advance.

## 4. Applying Backgrounds

![\[screenshot: applying-backgrounds.png\]](../assets/screenshots/applying-backgrounds.png)

Once the mask above is computed, it's reused to composite the photo onto
every background template in turn — the mask itself is only calculated
once, not recalculated per template. Progress here is shown as plain text
("Background X of Y") rather than a bar, since each step's timing is short
and predictable.

## 5. Gallery

![\[screenshot: gallery.png\]](../assets/screenshots/gallery.png)

Every generated background variant, with:

- **Left/right arrows** to browse between templates
- Status text along the top showing position (e.g. "Photo 2 of 6")
- **Click the photo itself, or the SELECT button**, to select it — the
  button dynamically relabels to **UNSELECT**, and clicking either the photo
  or the button again removes the selection
- **RETAKE** — in case the final composited result doesn't look good, not
  just the original photo (returns to live preview, discarding this
  session's output)
- **DOWNLOAD** — proceeds once at least one photo is selected


![\[screenshot: gallery-selected-state.png\] ](../assets/screenshots/gallery-selected-state_beach.png) ![\[screenshot: gallery-selected-state.png\] ](../assets/screenshots/gallery-selected-state_city.png)

— template shown in its selected state

![\[screenshot: gallery-select-required-popup.png\]](../assets/screenshots/gallery-select-required-popup.png)

— the popup shown if DOWNLOAD is pressed with nothing selected

## 6. Preparing Your Download

![\[screenshot: preparing-download.png\]](../assets/screenshots/preparing-download.png)

Zips the selected photos and uploads via `rclone`. This step depends on the
Pi's system clock being genuinely correct — see the time-sync troubleshooting
note in [`file-connections.md`](./file-connections.md#troubleshooting-download-fails-with-a-certificatetime-error)
if this screen fails with a certificate/time-related error.

## 7. QR Download

![\[screenshot: qr-screen.png\]](../assets/screenshots/qr-screen.png)

Shows a QR code generated from the uploaded photos' share link. Scanning it
with a phone starts the download immediately — no shared Wi-Fi required. The
link stays active for 15 minutes, after which both the local copy on the Pi
and the uploaded copy on Google Drive are automatically deleted (see the
auto-delete lifecycle note near `AUTO_DELETE_MS` in `finalV6.py`). **DONE**
returns to the live preview screen.

## Settings

![\[screenshot: settings-popup.png\]](../assets/screenshots/settings-popup.png)

A settings button appears on most screens. Opens a small popup with
**END PROGRAM** and **CLOSE** — intentionally minimal, since this is a
kiosk app with no user-facing configuration needed.
