# Background Removal: How the Software Knows Which Pixels Are "The Person"

## The goal, in plain terms

Given a photo of someone standing in front of the booth, the software needs to produce a version where the background behind them has been replaced with a themed scene — while keeping the person looking clean and natural, especially around tricky edges like hair.

This is genuinely one of the harder problems in the whole project. A person's outline isn't a simple shape, hair has fine, semi-transparent strands that don't cleanly belong to "person" or "background," and lighting varies. Getting this right took real trial and error, including approaches that were tried and deliberately abandoned.

## The final approach, step by step

1. **Find the person(s) in the frame.** A detection model (YOLO) is used first, purely to answer "where roughly is each person in this photo?" — it draws a bounding box, not a precise outline.
2. **Get a rough body outline.** Within each person's bounding box, a segmentation model (MediaPipe, using its "landscape" mode) produces a reasonably reliable outline of the body — good at the overall shape, less reliable at fine detail.
3. **Refine the hardest areas — especially hair.** The rough outline from step 2 is good but not great at fine, wispy detail. A second pass, using MediaPipe's more detail-sensitive "general" mode, is applied specifically to the *uncertain* regions (mainly hair edges and hands) rather than the whole image — this targeted approach gets the benefit of the more detailed model without its downsides (it's more prone to letting background through elsewhere).
4. **Blend the two results.** Rather than fully replacing the rough outline with the refined one, the two are blended, with a cap on how much influence the refined pass can have. This matters because the more detail-sensitive model can occasionally make mistakes of its own in harsh lighting — blending limits how much damage a bad call there can do, while still capturing most of the improvement when it gets it right.
5. **Composite onto the chosen background**, using the original photographed pixel colours directly (not re-estimated or blended colours) — this avoids a washed-out or faded look that other approaches produced.

**If YOLO doesn't find anyone in the frame** (or isn't available at all), the software falls back to running MediaPipe directly on the full photo instead of per-person crops — a safety net that keeps the booth working rather than failing outright, just without the extra accuracy the crop-first approach normally provides.

## Approaches that were tried and deliberately not used

It's worth knowing what *didn't* make it into the final version, since these were genuine, reasoned attempts, not oversights:

- **Reference-image subtraction** (comparing the "empty booth" photo against the "person in booth" photo to isolate the difference) — rejected after measurement showed a very high false-positive rate under normal camera auto-exposure changes.
- **A general-purpose background-removal library (`rembg`)** — produced good hair detail in testing, but gave inconsistent results on the exact same photo run twice, and was too slow on this hardware.
- **A more advanced segmentation model with more output categories** — best at hair edges in testing, but misclassified some clothing patterns as background and was the slowest of everything tested.
- **A traditional alpha-matting technique (`pymatting`)** — mathematically well-suited to this kind of problem, but caused the program to hang unpredictably on certain images during testing (a numerical stability issue), and was removed from the final code entirely.

## Why this matters for the final result

This layered approach — detect first, segment roughly, refine only where it's genuinely needed, then blend cautiously — is why the final photos hold up reasonably well even on hair, which is normally the hardest part of this kind of background removal. It's not perfect (very light-coloured clothing against certain backgrounds remains a known soft spot), but it's a considered, tested design rather than a single off-the-shelf tool applied blindly.
