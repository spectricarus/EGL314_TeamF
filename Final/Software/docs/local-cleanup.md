# Local File Cleanup: Why the 15-Minute Timer Was Removed

## What needs to happen

Every photo session writes files to the Pi's local storage — the composited photos themselves, and the QR code image generated for download. Left unmanaged, these accumulate indefinitely across a whole event's worth of guests. Something needs to clean them up.

## The original approach, and the real bug that killed it

The first version scheduled a 15-minute timer per session: take a photo, and 15 minutes later that session's files would be automatically deleted, on the Pi and on Google Drive.

In practice, this had a genuine, fairly deep bug. The timer read *whichever session folder happened to be currently active* at the moment it fired — not necessarily the one it was originally scheduled for. If a new photo was taken within that 15-minute window (extremely likely at a real, busy event), the old timer would eventually fire and delete the *new*, currently-active session instead of the one it was actually meant to clean up. On top of that, the QR code images lived in a separate folder that this cleanup never touched at all, so they piled up indefinitely regardless. And separately, closing the app was found to only *cancel* the pending timer — which does not delete anything, it just prevents the scheduled deletion from ever happening. None of this was a single simple bug; it took several rounds of genuine debugging to fully understand.

## The fix: no timers at all

The current approach is much simpler, and was chosen specifically because it avoids all of the above by construction: **the local output folders are wiped completely — deleted and recreated empty — at both app startup and app shutdown.** No per-session tracking, nothing scheduled, nothing that can point at the wrong session because nothing is waiting on a clock in the first place.

This is also **crash-safe in a way the timer approach never was**: even if the app crashes or gets force-closed and never reaches a clean shutdown, the *next* time it starts, the startup wipe still clears out whatever was left behind before the new session begins. There's no window where stale files can accumulate indefinitely from a bad exit.

## What actually gets wiped, and what doesn't

- **`saved_images/`** (the finished photos) and **`qrcodes/`** (the generated QR code images) — both wiped on the Pi, automatically, at every startup and shutdown.
- **The uploaded copy on Google Drive is deliberately left alone.** There's no code that touches it at all — it's cleaned up manually, by whoever's running the booth, whenever they choose to. This was a deliberate simplification: earlier auto-delete-from-Drive logic added real complexity for a problem (Drive storage filling up) that isn't especially urgent compared to keeping the Pi's own local storage tidy between guests.

If you need to clear out old uploads, that's a manual step in Google Drive itself — nothing in the app will do it for you.