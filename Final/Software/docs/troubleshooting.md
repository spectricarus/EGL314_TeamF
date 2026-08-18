# Known Issues & Troubleshooting

This page covers real problems encountered during development, how they were diagnosed, and their current status — split into things that are genuinely fixed, and things that are known limitations rather than bugs waiting to be found.

## Fixed issues

**Touchscreen registered movement but not taps.** Traced to the Pi's display running Wayland instead of X11 — a display-server-level setting, not an app bug. Fixed by switching to X11 via `raspi-config`. See [environment-setup.md](./environment-setup.md).

**Some text on screen had visibly broken/missing characters (most noticeably the letter "i").** Traced to several on-screen labels having a font hardcoded directly in the code (`"Arial"`) which, on this Linux system, doesn't reliably map to a complete, well-behaved font — while other labels correctly used the app's actual configured font (DejaVu Sans) and rendered fine. Fixed by making every label consistently use the same properly-configured font.

**The Pi's clock drifts, breaking secure connections.** The school network blocks the standard internet time-sync protocol (NTP), so the Pi's clock can become inaccurate after being powered off for a while, which in turn can break the secure connection needed to upload photos (secure connections check the current date against a certificate's valid dates). Fixed by having the app correct the clock automatically at every startup, using an alternative method (reading the time from a normal, unblocked web request) instead of the blocked one.

**The camera would intermittently hang or fail during capture.** This was the largest single problem in the project — see [camera-reliability.md](./camera-reliability.md) for the full account of what was tried and what actually fixed it.

**The app would occasionally freeze entirely (not just the camera) with no visible cause.** Traced to slow operations (camera reads, photo processing, uploads) running directly on the same thread responsible for drawing the screen. Fixed by moving all of these onto background threads — see [architecture.md](./architecture.md).

## Known, accepted limitations (not bugs — deliberate trade-offs)

**Final photos are 1080p, not a higher resolution.** A deliberate trade-off made to fix the camera reliability issue above — see [camera-reliability.md](./camera-reliability.md) for the reasoning.

**Very light-coloured clothing (e.g. a white shirt) can be a soft spot for the background-removal quality**, depending on the specific background and lighting. This is a genuine, known limitation of the segmentation approach described in [pipeline-explained.md](./pipeline-explained.md), not something that was overlooked.

**If the background upload service fails once, nothing forces it back to a working state — but that doesn't mean it's guaranteed to stay broken either.** There's no explicit auto-restart logic, by deliberate design (a more complex version with exactly that was built, tested, and dropped for being less stable), but the service can still recover on its own if the underlying cause was transient rather than fatal. Every upload still succeeds regardless, via the fallback path when needed — this is the exact behaviour used in the final presentation. See [download-pipeline.md](./download-pipeline.md) for the full reasoning.

## If something looks broken that isn't listed here

Check the terminal output the app is running in — it prints a running log of what's happening (camera status, processing timings, upload status, and any errors), which is almost always the fastest way to tell what's actually going on versus guessing from the screen alone.