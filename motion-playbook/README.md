# Motion Playbook

A small, tested way to make short animations in one HTML file, where the
quality is checked with numbers instead of eyeballs.

## The contract

Every film exposes one function, so any frame can be drawn, checked, and
fixed on its own:

```js
window.renderAt = (t) => { /* draw exactly time t, in seconds */ };
window.__ready = true; // only after everything has loaded
```

`renderAt(t)` is a pure function of `t`: no clocks, no random numbers, no
state carried between frames. If frame 300 drawn cold does not match frame
300 drawn in sequence, pixel for pixel, the film is broken — and you can
prove it either way.

## The rules

- **One beat grid drives everything.** Declare the tempo up top (this
  example: 120 BPM, one landing every 2 beats) and compute every hop, cut,
  and the loop point from it. Nothing is timed by hand, so picture and
  timing cannot drift apart.
- **Numbers, not adjectives.** "Bouncy" is not an instruction; a spring
  damping ratio is. 1.0 lands dead, 0.8 bounces once, 0.5 bounces twice.
  Same for colour (exact hex), squash (landing 1.25 × 0.75), and lenses.
- **The hero stays big enough to read.** At least 170 px wide at 1080p in
  every main shot, measured from the pixels, per shot, and reported.
- **Motion is checked, not watched once.** A model that checks stills will
  pass a frozen film. The checks below measure the motion itself.

## What's here

- `film.html` — the worked example: a small mascot hops up four crates of
  rising height and back down, 8 hops, an 8-second seamless loop at
  1920×1080, 60 fps. Canvas 2D, no dependencies, runs offline.
- `render.py` — renders the film frame by frame through headless Chromium
  and pipes the frames to FFmpeg for a clean MP4.
- `qa.py` — the measured checks: hero width at several timestamps, seek
  purity (cold frame vs in-sequence frame), freeze detection, loop seam.
- `QA.md` — the example's own QA report, with the numbers it passed on.

## The example's numbers

- Hero width at 0.5 / 1.8 / 3.0 / 4.6 s: 212 / 212 / 274 / 213 px (≥170)
- Seek purity, frame 300: difference 0.0 — pixel-identical
- Freeze detection: no freezes
- Loop seam: continuous, the only change is the intended landing squash

## Rendering HTML to video

For a quick HTML → MP4 render without a project scaffold, see
[HyperFrames](https://github.com/heygen-com/hyperframes) in the main list:
one HTML file in, a video out, with a built-in check for lint, motion, and
contrast problems before you render.
