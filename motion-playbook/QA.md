# QA — Playbook Film (measured, 2026-11-22)

Film: `film.html` → `film.mp4`. Renderer: **plain Canvas 2D**, not Three.js —
Three.js via CDN is unreliable headless on this CPU VM and WebGL/swiftshader
adds cost for a flat mascot shot; Canvas 2D is self-contained and deterministic.
Full resolution kept: **1920×1080** (no downscale). Render time: **327.6 s**
for 480 frames on this VM (~0.68 s/frame, Playwright headless Chromium,
`--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`, no `--disable-gpu`).

Method: `qa.py` (Playwright + PIL/numpy). Hero width is **pixel-measured**
from screenshots: bounding box of accent (#D97757) pixels — the mascot is the
only accent object in frame. Raw numbers: `qa/qa_results.json`.

## 1. Stills + hero width — PASS (all ≥ 170 px at 1080p)

| t (s) | PNG | Mascot width (px) | Height (px) | Pose |
|---|---|---|---|---|
| 0.5 | `qa/still_0.5s.png` | **212** | 213 | mid-hop, floor → crate 1 |
| 1.8 | `qa/still_1.8s.png` | **212** | 213 | mid-hop, crate 1 → crate 2 |
| 3.0 | `qa/still_3.0s.png` | **274** | 154 | landing frame on crate 3 (squash 1.25×0.75) |
| 4.6 | `qa/still_4.6s.png` | **213** | 214 | mid-hop, crate 4 → crate 3 |

Minimum measured: 212 px — clears the 170 px floor with ~25% headroom.
(Design widths: base 220, takeoff stretch 0.85×220 = 187, landing 1.25×220 = 275;
pixel bbox reads 1–2 px wider from anti-aliasing/ears.)

Also verified in the encoded MP4 itself: `qa/mp4_frame_4.6s.png` (extracted with
ffmpeg) matches the 4.6 s still — mascot airborne over crate 4, heading down.

## 2. Seek check (renderAt purity) — PASS, exact

Frame 300 (t = 5.0 s) rendered two ways:
- cold: fresh browser/page, frame 300 is the first frame drawn (`qa/frame300_cold.png`)
- sequential: after drawing frame 299 on the same page (`qa/frame300_after_299.png`)

**Mean absolute pixel difference: 0.0. Max channel difference: 0.**
Pixel-identical — `renderAt(t)` carries no state, no clock, no randomness.

## 3. freezedetect — PASS

`ffmpeg -i film.mp4 -vf freezedetect=n=-60dB:d=0.5 -map 0:v:0 -f null -`
**No `freeze_start` events reported.** No unintended frozen stretch ≥ 0.5 s
(the longest designed hold is the 0.25 s settle/crouch per hop).

## 4. Loop seam (frame 479 → frame 0) — PASS, with the intended impact cut

- Mean absolute pixel difference 479 vs 0: **2.38** (out of 255) — the frames
  are near-identical overall; the background/crates never change.
- Mascot position is continuous: frame 479 bbox x 174–363, bottom y 881
  (descending, 19 px above the floor, pre-landing stretch 190 px wide);
  frame 0 bbox x 123–396, bottom y 899 (on the floor, landing squash 274 px wide).
- The only discontinuity is the deliberate one: stretch → squash at the
  landing instant, exactly on the beat (t = 8 = 0). Position and travel
  direction flow straight into frame 0; there is no jump, teleport, or
  lighting change at the seam.

## 5. ffprobe facts

| Field | Value |
|---|---|
| Codec | h264 |
| Resolution | 1920×1080 |
| Frame rate | 60/1 (r and avg) |
| Frames | 480 |
| Duration | 8.000000 s |
| File size | 591,455 bytes (~578 KiB) |

## Known minor flaw (not fixed — cosmetic, outside the measured checks)

The contact shadow snaps to the floor when the mascot is just off a crate's
edge mid-hop (visible in the 4.6 s MP4 frame: shadow on the floor while the
mascot is above crate height). It does not affect any playbook check, but a
production pass should clamp the shadow to the nearest surface below the
mascot's x, not any surface.
