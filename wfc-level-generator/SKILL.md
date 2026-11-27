# WFC Level Generator - Skill

## What this is

`wfc5.py` generates game terrain (water, sand, grass, forest) with a
WaveFunctionCollapse solver laid over a fractal-noise layout, carves
three clearings (spawn, camp, objective), and stitches a fully
connected dirt path between them. Its defining feature is the contract:
**a map is written only after it passes every quality gate in code.**
If no seed passes within the attempt cap, it writes nothing and exits
nonzero. There is no silent "best effort" map.

Python 3.10+, Pillow is the only dependency (`pip install pillow`).

## When to use it

- A game level, RPG overworld, or roguelike floor needs terrain that is
  guaranteed sane: no water touching grass, one connected landmass, a
  path the player can actually walk.
- A map someone hands you needs checking (`--verify`).
- A hand-drawn fantasy version of a generated map is wanted (prompt 1
  in `PROMPTS.md`, also prompt 17 in the repo prompt library).

## Workflow

1. Generate: `python wfc5.py` writes a verified 32x32 map
   (`map_v5.png/.json/.tmx/.txt`). Use `--seed N` for a specific seed,
   `--seeds N` to shop more candidates, `--size`, `--width/--height`,
   `--water`, `--forest` to taste, `--sheet` for a contact sheet of the
   passers it found.
2. Trust the exit code: 0 means the written map passed every gate.
   Exit 3 means no passer within `--max-attempts`; report that, do not
   present a failing map as a keeper. `--allow-unguaranteed` exists for
   debugging only and marks its output `.FAILED`.
3. Look at the PNG yourself before presenting it. The gates check
   structure, not taste.
4. Verify a handed map: `python wfc5.py --verify map.json` re-runs
   every gate and reports `gates_passed`.
5. Fantasy restyle: feed the keeper PNG to image generation with
   prompt 1 in `PROMPTS.md`. The prompt locks geography by area, place,
   and route while ordering every outline redrawn in one flowing
   stroke - that wording is what stops the model copying the pixel
   steps. Compare the result against the source grid; if geography
   moved, regenerate.

## World-size maps

Rectangular sizes make proper world maps: `--width 96 --height 64`.
Two lessons from the tested world build (examples `world_map.png`,
seed 331, `--water 0.24 --forest 0.57`):

- At world size the plain shop keeper can be gate-passing but dull
  (one blocky forest, lakes crowding the edges). Probe a few knob
  combinations, render the first passer from each, and pick by eye.
  The gates guarantee structure; composition at this size is a
  judgement call.
- Generation is slower per attempt at 96x64 (seconds, not the ~1s of
  32x32), so budget the shop accordingly.

The JSON/TMX grid is always the source of truth for gameplay; a
fantasy restyle is presentation art on top of it.

## Guarantees the gates check

Water never touches land directly (sand always between), exactly one
connected landmass, blobby lakes and forest (shape scores, no spikes),
sand share in band, forest in a few large regions, composition spread
across halves and quadrants, clearings present and spaced, path fully
4-connected with zero dotted (diagonal-only) cells, zero broken
adjacencies on the grid and on the rendered image.

## Honest limits

- Yield is about 1 in 4 seeds at 32x32, about 1 in 5 at 64x64; the
  shop exists because single seeds often fail.
- No bridges: the path never crosses water, by design of the water
  rule.
- One biome set (temperate). Hills, swamp, and snow are not in v5.
