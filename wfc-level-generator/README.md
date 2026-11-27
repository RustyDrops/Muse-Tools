# wfc5 - guided WaveFunctionCollapse level generator

Version 5.0.0. License: MIT, use it freely. The tool is one file,
`wfc5.py` in this folder; copy it anywhere and run it there.

Generates a game ready terrain map with lakes, sand shores, forest, three
clearings (spawn, camp, objective) and a dirt path connecting them. The
contract is the point: **every map this tool writes has passed every gate
below, verified in code. If no seed passes, it writes nothing and exits
nonzero.** There is no silent bad map.

## Quickstart

Needs Python 3.10+ and Pillow:

```
pip install pillow
python wfc5.py
```

That writes four files next to the script:

- `map_v5.png` - the rendered map
- `map_v5.json` - grid, features, scoreboard, and full provenance
- `map_v5.tmx` - Tiled format, with `wfc_tileset.png` written alongside so it opens ready to use
- `map_v5.txt` - the plain grid, one character per cell

## Reading the map

Tiles: `W` water, `S` sand, `G` grass, `F` forest, `P` dirt path.
In the PNG: the white ring is spawn, the campfire is camp, the grey stone
ring is the objective. Water is shaded by depth, darker is deeper. The
path is one continuous trail, fully connected in the 4 directions a game
engine pathfinds on.

## The guarantees (all checked in code on every map)

- 0 broken adjacencies: water never sits directly next to grass or forest, sand always bridges, on the grid and on the rendered image
- One connected landmass, no single-cell regions, no stray inland sand (sand must lie within 2 cells of water)
- Sand share in a sane shore band, water and forest spread across the map, no bare all-grass quadrant
- Forest and lakes are blobby shapes with solid cores, not speckles or thin scribbles
- The path never touches water, stays mostly off the map edge (at most 35% of its cells in the border band), has no long straight runs, and connects spawn to camp to objective with no diagonal-only joints
- Same seed and same settings always produce the identical grid, in any process (proven by the test suite under different hash seeds)

Exit codes: `0` a verified map was written, `2` bad arguments (clean one
line error, never a traceback), `3` no seed passed within the attempt cap,
nothing written. `--allow-unguaranteed` overrides the refusal and writes
the best failing map with a `.FAILED` marker in the filename, still exit 3.

## Usage

```
python wfc5.py                                  # seed shop, best verified keeper
python wfc5.py --seed 42                        # one seed; retries forward until a verified passer, reports the seed actually used
python wfc5.py --size 48                        # square, 16 to 128
python wfc5.py --width 64 --height 40           # rectangular
python wfc5.py --water 0.24 --forest 0.57       # biome knobs (safe ranges below)
python wfc5.py --sheet                          # also write contact_sheet_v5.png, every candidate labelled PASS or its first failing gate (b= is the beauty score, lower is prettier, the keeper is the lowest)
python wfc5.py --out levels/level_07            # custom output prefix, writes level_07.png/.json/.tmx/.txt
python wfc5.py --verify map_v5.json             # re-check any exported grid against all gates, writes nothing
python test_wfc5.py                             # the full production exam as a test suite
```

Knobs: `--water` is the water share of the map, safe range 0.12 to 0.28,
default 0.20. `--forest` is a moisture threshold, safe range 0.55 to 0.68,
default 0.60; lower means more forest. Out of range values are refused
with a clean error before any work starts.

How it works, briefly: a fractal noise layout decides the geography
(lakes, shores, forest clusters), a WaveFunctionCollapse solver grows
edge detail under hard adjacency rules, a cleanup pass fixes stragglers
without breaking any rule, then clearings are stamped and an A* path is
carved, wiggled for curves, and stitched so it is fully 4-connected.
Every candidate is scored on one fixed scoreboard; the shop draws seeds
until it has verified passers and keeps the prettiest.

## JSON format

```
{
  "tool": "wfc5", "version": "5.0.0",
  "python": "...", "pillow": "...",
  "params": {"width": 32, "height": 32, "water": 0.2, "forest": 0.6,
             "seed_requested": null, "seed_used": 14, "attempts": 15},
  "gates_passed": true,
  "size": [32, 32],
  "legend": {"W": "water", "S": "sand", "G": "grass", "F": "forest", "P": "path"},
  "origin": "grid[0][0] is the top-left cell; x grows right, y grows down",
  "grid": ["GG...", ...],            // one string per row
  "features": {"clearings": [{"name": "spawn", "x": 6, "y": 25, "radius": 2}, ...],
               "path_cells": 65},
  "scoreboard": { ... }              // every measured gate value
}
```

## Tested matrix and performance

The suite (`test_wfc5.py`, 29 checks) covers sizes 16, 24, 32, 48x32,
32x48 and 64, knob corners, determinism across processes, export parse
backs, refusal behaviour, and bad input handling. Measured on a small
shared VM: a 32x32 shop takes a few seconds; a 64x64 seed attempt takes
about 2 seconds and roughly 1 in 5 seeds passes there, so big maps lean
on the attempt cap (default 200). At 32 about 1 in 4 seeds passes.

## Honest limits

- One biome set (temperate lake country). No hills, swamp, snow, or bridges across water yet; the path routes around lakes, never over them.
- Yield drops with size: at 64x64 most seeds fail a gate and the shop needs more attempts. The tool tells you how many it took.
- The render is a clean flat game style, not textured art. The grid and TMX are the real product; bring your own tileset art for a shipped game (the bundled tileset is flat colours so the TMX opens usefully).
- Forest can sit against the map edge. It reads fine, but if you need a clean border, crop or frame the map in your engine.
