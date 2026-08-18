# Getting the Photo to the Guest: Upload & QR Code

## What needs to happen

Once a guest has picked their favourite photo(s), the software needs to: upload the file(s) to Google Drive, get a shareable link back, turn that link into a QR code, and show it on screen — ideally within a few seconds, since the guest is standing there waiting.

## Why this needed real engineering attention

The straightforward way to do this — running the `rclone` upload tool fresh for every single photo — turned out to be genuinely slow and inconsistent in testing, sometimes taking 30+ seconds for the same small file that had just uploaded in under 5 seconds moments earlier. Investigation traced this to the overhead of starting a brand new connection (including re-authenticating) from scratch on every single upload, rather than the actual file transfer itself, which is small and should be near-instant.

## The fix: a persistent background service

Instead of starting a fresh upload process for every photo, `rclone` is run once as a **persistent background service** when the app starts, and stays running for the whole session. Each individual upload then talks to that already-running, already-authenticated service, instead of paying the "starting from scratch" cost every single time.

This meaningfully improved typical upload speed, though some variability remains — this is talking to an external service over wifi, which is never going to be perfectly consistent no matter how the code is written.

## A safety net for when it doesn't cooperate

If the background service ever fails to respond for any reason, the software automatically falls back to the original, slower-but-proven method (a single direct upload command) for that one photo — the guest still gets their photo, just via the slower path for that one instance.

**When this happens, the download screen shows a "Taking longer than usual..." message.** This is the exact text shown on screen — it only appears when the fallback actually triggers, never during a normal fast download, so it's clear to the guest (or operator) that something real is happening, not that the booth has frozen.

## A deliberate design decision: no *forced* recovery

**If the background upload service fails once, nothing in the code forces it back to a working state** — there's no explicit "detect a failure and restart the process" logic. An automatic-restart fix that added exactly that was built and tested, but the resulting version introduced its own instability, and was deliberately dropped in favour of the simpler behaviour described above.

**This is not the same as "permanently broken for the rest of the session," though — that would overstate it.** The background service is still a real, running process; if whatever caused a given failure was transient (a momentary network hiccup, for example, rather than the process actually dying), a *later* upload attempt can simply succeed against that same service again on its own, with nothing needing to "fix" it in between. What's genuinely true is that there's no guarantee either way — recovery isn't forced, but it isn't ruled out either. In practice this showed up as occasional, not permanent, fallback use.

**This is the exact version that was used in the final presentation.** The trade-off was judged, tested, and accepted: the booth stays *reliable* (the fallback means every photo still gets uploaded successfully, no guest ever leaves without their photo) even without a guaranteed self-healing mechanism. Given how close this decision was made to the actual event, a simpler, already-proven system was chosen deliberately over a more complex one with less-tested recovery logic — and it held up.