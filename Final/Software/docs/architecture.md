# Architecture: Why This App Uses Multiple Background Threads

## The problem this solves

A touchscreen app needs to feel responsive at all times — a guest tapping a button should get an immediate reaction, not a frozen screen. But this app also has to do several *slow* things: reading from a camera that can occasionally hang for several seconds, running an AI model that takes a few seconds per photo, and uploading a file over wifi that might be slow or flaky.

Python (and the graphical toolkit this app is built on, called Tkinter) normally runs everything on a single thread. If any single operation on that thread takes a while, *the entire app freezes* — not just the part that's slow, literally everything, including the ability to tap any button, while that one operation is running.

Early in development, this caused a specific, confusing set of bugs: things like the loading spinner not animating, or the settings button seeming completely unresponsive — which looked like separate problems, but were actually all the same root cause showing up in different places.

## The fix: background threads for anything slow

A **thread** is a way for a program to do more than one thing at once. This app moves every slow, unpredictable operation off the main thread and onto its own background thread, so the main thread — the one responsible for drawing the screen and responding to taps — is always free.

There are four background threads running during normal use:

1. **Camera reader thread** — continuously reads frames from the webcam in a loop. The main thread never talks to the camera directly; it just checks "what's the most recent frame this background thread has grabbed?" every fraction of a second. If the camera hangs for a moment, only this background thread is affected — the rest of the app keeps working.
2. **Photo processing thread** — the AI-based background removal (see [pipeline-explained.md](./pipeline-explained.md)) runs here, so the "Analyzing your photo..." screen can show a genuinely animating spinner instead of a frozen one.
3. **Upload thread** — uploading the finished photo and generating the QR code link happens here (see [download-pipeline.md](./download-pipeline.md)), for the same reason.
4. **Keep-alive thread** — periodically pings the upload system in the background to keep its connection warm, so the *next* upload doesn't have to pay a slow "reconnecting" cost.

## The one rule that makes this safe

Background threads are **never allowed to directly touch anything on screen**. Tkinter (the screen-drawing library) isn't designed to be touched from more than one thread at once — doing so causes crashes or corrupted screen state.

Instead, whenever a background thread finishes its work and needs to update the screen, it hands the result back to the main thread using a scheduling call (`root.after(0, ...)` in the code), which safely queues that update to happen on the main thread at the next opportunity. This is the pattern used consistently everywhere background threads interact with the screen.

## Why this mattered more than it might sound like

This wasn't a minor performance tweak — several real, previously mysterious bugs turned out to be the *same underlying issue* (something blocking the main thread) showing up in different disguises: a frozen loading spinner, an unresponsive settings button, camera capture appearing to hang. Once background threads were properly introduced for every slow operation, all of these were fixed by the same underlying change, not four separate patches.
