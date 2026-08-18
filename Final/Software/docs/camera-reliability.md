# Camera Reliability: The Biggest Problem, and How It Was Actually Solved

This was, by a wide margin, the single most time-consuming problem in the entire project. It's documented in detail here because the *final* fix only makes sense in light of everything that was tried and ruled out first — and because "why is it built this way" is a completely reasonable question to ask about the eventual, simple-looking solution.

## The symptom

Intermittently, taking a photo would fail or hang — the countdown would finish, but the actual capture would stall, sometimes for several seconds, sometimes much longer, with the console showing repeated `select() timeout` errors from the camera driver.

## What was tried, and why each attempt wasn't the real fix

**Attempt 1: Add longer delays before reading from the camera.** The theory was the camera hardware just needed more time to "settle" after being opened or reconfigured. This helped somewhat, but the problem kept coming back — because it wasn't really about *how long* to wait, it was about *what specifically* was being waited for.

**Attempt 2: Suspect the high-resolution capture.** The app originally captured photos at a higher resolution (4K) than the live preview (1080p), switching the camera's resolution briefly for each photo and switching back afterward, on the theory that a higher-resolution source photo gives a cleaner final result. This seemed like a plausible suspect — but testing showed the 4K capture itself reliably worked; the problem was elsewhere.

**Attempt 3: Move the camera reading off the main thread.** This was a real, necessary fix — described in [architecture.md](./architecture.md) — and it solved a genuine, separate problem: the *entire app* freezing (not just the camera) whenever a camera read took a while. But it didn't fully solve the capture failures, because the actual photo-taking step still ran directly on the main thread, still blocking everything when it hit trouble.

**Attempt 4: Detect and recover from a "stuck" camera thread.** Even after moving continuous reading to a background thread, there was a separate edge case: if a single camera read *never returned at all* (a true hang, not just a slow one), that background thread could get permanently stuck, with no way to safely force-stop it (Python cannot cleanly kill a thread that's blocked inside a lower-level system call). The fix was to track when the last successful frame arrived, and if too long passed, treat the thread as dead and start a completely fresh one rather than trusting a thread that claims to be running but isn't producing anything. This is a real, valuable safety net — but it still wasn't *the* root cause of the original failures.

## The actual root cause

The breakthrough came from a single test: the failure happened on the *very first capture of a session*, with nothing else going on — no retake, no idle wait, nothing unusual. That ruled out every theory above, which all assumed the problem was tied to *timing* or *history*.

What was actually happening: **every single photo capture involved changing the camera's resolution** — switching from the 1080p live-preview stream to a 4K capture, then switching back. That resolution-change operation itself, on this specific camera and driver combination, had a real, ever-present chance of triggering the failure — regardless of how long anything had been running, regardless of retakes, regardless of anything else. It wasn't rare or edge-case-y; it was baked into every single photo.

## The fix

**Stop changing resolution at all.** The final photo is now simply a copy of whatever frame the live preview was already showing at the moment of capture — the same 1080p stream, no separate high-resolution grab, no resolution switch of any kind.

This has one real, deliberate trade-off: the final photo is 1080p instead of a higher-resolution capture. Given how much instability the resolution switch caused, and how consistently the fix eliminated it, this was judged the right trade — a reliably-working booth beats a marginally sharper photo that sometimes doesn't work at all.

This fix was validated by deliberately trying to break it — repeated rapid retakes, retaking after full processing, leaving the booth idle for long stretches — and it held up cleanly where every earlier version eventually failed.

## Why the earlier fixes are still in the code

Even though none of attempts 1–4 were *the* fix, they weren't wasted effort — each of them fixed a real, separate problem (the whole-app-freezing issue, the stuck-thread edge case) that would still exist even with resolution-switching removed. The final, reliable version is the combination of all of them together, not just the last one.
