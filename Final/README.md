# Project Phantom Photobooth — Final Build

[↑ Back to repository overview](../README.md)

This is the final, event-ready version of the photobooth built for **Project Phantom** (NYP EGL314). It builds on the earlier POC and MVP stages, with a large number of reliability, performance, and experience improvements made in the final stretch before the event.

A guest walks up, gets their photo taken, sees themselves composited onto a themed background, picks their favourite, and scans a QR code to take it home — all through a touchscreen, with no need for anyone to touch a keyboard.

## Hardware — the shared foundation for both Enclosure and Software

This section lives here, at the top level, deliberately — it isn't really an "enclosure thing" or a "software thing," it's context both halves of this documentation depend on. The enclosure needs to physically fit around this exact hardware (cutout sizes, screw mounts, cable routing); the software is written assuming these exact components and their specific capabilities. If any of these get swapped for a different model later, both sides of the documentation may need re-checking against the real thing, not just one.

**Required:**

| Component | Notes |
|---|---|
| **Raspberry Pi 4 Model B** | The computer running everything |
| **Raspberry Pi 7" touchscreen display** | The official Raspberry Pi touchscreen — what the guest sees and taps |
| **Display ribbon cable** | Connects the touchscreen to the Pi — its length and routing is a real constraint on the enclosure's internal layout |
| **Logitech BRIO 4K USB webcam** | Takes the photo. The software is written around this specific camera's capabilities (resolution, supported frame rates) — see the [Software docs](./Software/docs/camera-reliability.md) for why the exact camera matters more than you'd expect |
| **DFRobot Gravity Digital Speaker Module (SKU: FIT0449)** | Plays the countdown beeps and confirmation sounds, wired to a GPIO pin on the Pi |
| **32GB microSD card** | Holds the OS and everything the software needs to run |
| **Jumper wires and power supply** | Wiring the speaker to the Pi, and powering the whole thing |

**Optional (improves photo quality, not required for the booth to function):**

| Component | Notes |
|---|---|
| **Two studio-style LED light panels with stands** | Gives even, flattering lighting on the guest. Any reasonably even light source works — dedicated panels just do it noticeably better than ambient room lighting alone |

**Also required, but not a physical component: a wifi connection.** The software uploads each finished photo to Google Drive and generates a QR code linking to it, so the guest can get the photo on their own phone — this requires an active internet connection at the point of upload. Without wifi, photos can still be taken and previewed, but the download/QR step won't work. See the [download pipeline docs](./Software/docs/download-pipeline.md) for how this upload actually works.

None of this is exotic hardware — it's a fairly standard "Raspberry Pi + touchscreen + webcam" kiosk setup, just with the specific models above.

## Where to go from here

This documentation is split into two parts, matching the two halves of the actual physical build, both of which build on the hardware above:

- **[Enclosure](./Enclosure/README.md)** — the physical housing/case the electronics live inside.
- **[Software](./Software/README.md)** — everything that makes the booth actually work: the code, how to set it up, and how it's built.

## A quick note on how this documentation works

Each section starts with a plain-language overview that assumes no prior knowledge — you should be able to read just the top of each page and understand what's going on and why. Further down, or linked out to separate pages, is more technical depth for anyone who wants it. You never *need* to click into the deeper pages to follow the main story — they're there if you're curious, not required reading.
