# GSAP timeline scrub test

GSAP earns a place in the motion toolkit: not as a replacement for the
frame-by-frame pipeline, but inside it. Build a paused GSAP timeline,
drive it with `seek(t)` from the same `renderAt(t)` pattern the Motion
Playbook uses, step it with Playwright, and assemble with FFmpeg.

Tested 2026-11-26 with GSAP 3.12.5, real output, not a demo claim:

- 90 frames at 30 fps, 3 s, 720x720, rendered and encoded in about 11 s.
- Determinism check: rendering t=1.0 twice produced identical frame
  hashes. Scrubbing is exact, the same guarantee hand-rolled springs give.
- Midframe viewed by eye: letters landed with the back.out overshoot,
  card in place, progress bar at the position the timeline math predicts.
- The win is the built-in eases (back, elastic, stagger) so timeline-heavy
  pieces stop hand-rolling springs.

Files: `index.html` (the test page, GSAP loaded from CDN; the verified
local run used a downloaded copy of the same 3.12.5 file) and
`render.py` (the frame stepper plus the determinism check).

## Also reviewed in the same pass, both parked

- **Hairline** (lucasmarkes/hairline): 33 pre-made isometric line figures
  that react to the pointer, plus agent skills to draw new ones in that
  style. Well built, with a validator and a screenshot look sheet worth
  borrowing. Parked: the monochrome single-stroke style clashes with
  branded work, its empty-state niche is already covered by Lottie and
  Motion, and it is young (v0.5.1).
- **Anatomy Reveal** (annnguyentt/anatomy-reveal-skill): builds any object
  from real dimensions as convex parts, then an interactive dissection
  page and an exploded-view MP4. Parked as a one-off specialty: its own
  docs budget 100-150 parts, 2-4 hours per object plus about an hour for
  the film, rendering at about 2 minutes per second of film. It also
  needs ImageMagick 7.
