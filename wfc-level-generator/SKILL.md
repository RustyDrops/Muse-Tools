# Skill: verified game levels with wfc5, plus a fantasy restyle

Use when someone wants a game map or level layout that is guaranteed
playable-shaped, not just pretty: lakes with real shores, one landmass,
forest with body, three clearings and a connected dirt path.

## Workflow

1. Generate with the tool, never by hand:
   `python wfc5.py` (shop) or `python wfc5.py --seed N` (retries forward
   to a verified passer and reports the seed used). Knobs: `--water`
   0.12 to 0.28, `--forest` 0.55 to 0.68, `--size` 16 to 128 or
   `--width/--height` for rectangular maps.
2. Trust only the contract: exit 0 plus `"gates_passed": true` in the
   JSON. Exit 3 means no verified map exists; report that, never ship
   the `.FAILED` fallback as a keeper.
3. Check the render yourself before presenting it. The gates prove
   structure; your eyes prove it reads as a place.
4. For a fantasy version, use PROMPTS.md prompt 1 with the map PNG as
   the input image. After generating, compare the restyle against the
   source: same lake, same shores, same forest, same path route. If the
   geography moved, regenerate. The grid files stay the source of truth
   for gameplay; the restyle is art.
5. For an existing map file, `python wfc5.py --verify file.json`
   re-checks every gate without generating anything.

## Gates (enforced in code, see README.md)

0 water-next-to-land adjacencies, one land region, no single-cell
regions, no inland sand, composition spread across all quadrants, solid
forest and lake shapes, and a path that is fully 4-connected with no
diagonal-only joints, never touching water.

## Proof in this folder

`examples/` holds a keeper (seed 14) in all four export formats, its
contact sheet, and a tested fantasy restyle of that keeper.
`test_wfc5.py` is the production exam as a runnable suite (29 checks:
reliability, determinism across processes, size and knob matrix, export
parse-backs, refusal behaviour). Run it after any change to wfc5.py.
