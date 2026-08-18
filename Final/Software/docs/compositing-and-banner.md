# Compositing & the Event Banner

## The three layers of every final photo

Every photo that comes out of the booth is actually built from three layers, stacked in this order:

1. **The chosen background** — the themed scene the guest picked.
2. **The person**, cut out using the process described in [pipeline-explained.md](./pipeline-explained.md), placed on top of the background.
3. **An event banner**, added last, on top of everything.

## Why the banner is a separate, final layer — not baked into the background

An early idea was to put event text (the event name, date, etc.) directly into the background images themselves. This was deliberately avoided: if a guest is standing in the wrong spot, or the composited photo is framed a certain way, text embedded in the background image can end up partially hidden behind the person. By adding the banner as the very last layer, on top of the already-composited photo, it's guaranteed to always be fully visible, regardless of where the guest is standing or how they're posed.

## What's actually in the banner

- The event title — currently set to **"Project Phantom @ NYP S.536"** in the code (`EVENT_BANNER_TEXT`), shown in bold
- The current date, in a regular (non-bold) weight below the title — deliberately a different font weight from the title, not just a smaller size, so it reads clearly as secondary at a glance rather than competing with the title for attention
- The date is generated fresh every time a photo is taken (not a fixed date typed into the code once), so it's always accurate no matter which day the booth is actually used
- A semi-transparent dark strip behind the text, so it stays legible regardless of what colours happen to be in the photo underneath it

## Two ways the banner can look, with automatic fallback

The software supports two modes:

- **A custom-designed graphic** — if a specifically-named image file exists (a transparent PNG designed like a broadcast-style overlay graphic), it's used, with just the date drawn on top of it live at a specified position.
- **A simple built-in banner** — if that custom file doesn't exist, the software automatically falls back to a plain version it draws itself (a dark strip with text), so the booth still works and looks reasonable even without a custom design in place.

This means the custom graphic is an enhancement, not a dependency — the booth was designed to work correctly either way, and switching between them doesn't require any code changes, just adding or removing that one image file.

## Changing the banner text

The title text, date format, and styling are all plain constants near the top of the code (`EVENT_BANNER_TEXT`, `EVENT_DATE_FORMAT`, and related `EVENT_BANNER_*`/`EVENT_DATE_*` settings) — changing what the banner says or how it's dated doesn't require touching any of the drawing logic, just editing those values directly.
