# Kenney Assets at Real World Scale

Free game models that actually fit your scene. [Kenney](https://kenney.nl/assets)
packs are public domain (CC0, credit optional), but every kit is authored at
its own scale, so raw models tower or shrink next to each other. This folder
fixes that the mechanical way: measure each model, fit it to a real world
size, ground it, and prove it with numbers before you look at the picture.
`SKILL.md` is the full workflow: check the pack's own License.txt, download
from kenney.nl, generate a manifest with real world targets, load through
the helper, and gate the result (sizes within 2 percent, bases at zero,
stacked items on their hosts, no footprint overlaps, screenshot viewed).
`tools/make-manifest.py` scans a pack's GLB folder and writes the manifest;
`tools/kenney-fit.js` is the Three.js loader that applies it, including
`placeOn` for anything that sits on furniture and `footprintOverlaps` for
the overlap check. `PROMPTS.md` has five copy paste prompts: build a scene,
add one asset, fix a scale problem, QA against the gates, and turn a room
description into a layout, plus a real world sizes cheat sheet.
`examples/` holds two tested builds from 2026-11-26: Cozy Room (13
Furniture Kit models, a playable walker) and a Racing Kit track with three
cars lapping, as screenshots, both scene files, and a 6 second video of
the race. The Kenney license text from the Furniture Kit is kept there too.

Copy `SKILL.md` into your Muse's custom skills folder, or just ask your
Muse to build a scene with Kenney assets and point it here.
