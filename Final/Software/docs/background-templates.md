# Background Templates

## Where they live

All background images go in `assets/backgrounds/` (the `BACKGROUND_DIR` constant in `finalphotobooth.py`), in the same folder as the main script. The app automatically picks up every valid image file in that folder — there's no list to edit in the code, adding or removing a file there is enough.

**Accepted formats**: `.jpg`, `.jpeg`, `.png`.

## How many, and in what order

Every file found gets composited and shown to the guest as a separate option in the gallery, in alphabetical order by filename — if you want a specific display order, name the files accordingly (e.g. `01-scene.jpg`, `02-scene.jpg`).

## What makes a good background for this specific pipeline

These aren't arbitrary preferences — they come directly from how the background-removal pipeline actually works (see [pipeline-explained.md](./pipeline-explained.md)):

- **16:9 landscape**, matching the app's 1920×1080 output — a different aspect ratio will get stretched or cropped
- **No text, logos, or watermarks baked into the image** — the event banner is added separately, on top of every photo, specifically so it's never blocked by the guest; text baked into the background doesn't have that guarantee
- **Avoid busy, high-detail texture in the upper-middle of the frame** — that's roughly where a guest's head and hair land, and fine detail directly behind hair is exactly where this pipeline's background-removal is weakest. Simpler, softer detail there, with more visual interest toward the edges and lower portion, gives noticeably cleaner results
- **No people already in the scene**, for obvious reasons

## Swapping or adding new ones

No code changes needed — just add, remove, or replace image files in `assets/backgrounds/`. Changes take effect the next time the app is started (the list is read once at startup, not watched live while running).
