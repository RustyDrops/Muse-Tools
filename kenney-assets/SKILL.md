# Kenney Assets at Real World Scale - Free Game Models That Fit Your Scene

Build game scenes from [Kenney](https://kenney.nl/assets) packs (public domain,
CC0: free for personal and commercial projects, credit optional) without the
usual scale mess. Kenney kits are authored at roughly half scale and every kit
disagrees about what a metre is, so models dropped in raw tower over each
other or shrink to doll size. The fix is mechanical: measure each loaded
model, fit it to a real world size, ground it. Never hand-tune scale numbers.

Tested end to end 2026-11-26: two packs (Furniture Kit, Racing Kit), two
playable scenes, all measurements exact. Examples are in `examples/`.

## The workflow (follow it in order)

1. **Check the license in the pack, not from memory.** Every Kenney pack
   ships a License.txt that says Creative Commons Zero CC0, free to use in
   personal, educational and commercial projects, credit not mandatory.
   Keep that file with your project copy of the pack.
2. **Download from kenney.nl.** Each pack page has a free download behind a
   donation prompt ("Continue without donating" is the free path). Packs
   include GLB models under `Models/GLTF format/`.
3. **Generate a manifest.** `tools/make-manifest.py <glb-folder> <names or ALL> manifest.json`
   measures every model's raw bounds straight from the file and attaches a
   real world fit target from its TARGETS table (chair back 0.9 m, desk
   0.75 m, tall bookcase 1.8 m, race car 1.9 m wide, road tile 10 m, and
   more). A model with no target gets mode "none": add its real world size
   to TARGETS first, do not guess a scale in scene code.
4. **Load with the helper, not by hand.** `tools/kenney-fit.js` (Three.js):
   `loadScene(loader, manifest, placements, scene)` scales, grounds and
   places everything and returns measured sizes, bases and footprints.
   Placements are a small map: `at: [x, z]`, `rotY`, and `on: "host name"`
   for items that sit on furniture (TV on its stand, laptop on a desk,
   books on a coffee table). The primitives (`fitHeight`, `fitWidth`,
   `ground`, `centerAt`, `placeOn`) are there for repeated pieces like
   track tiles, where you clone one loaded model many times.
5. **Gate it with numbers, then look at it.** A scene is done only when:
   every manifest asset loaded with zero errors; every grounded model's
   final size is within 2 percent of its target and its base is at y = 0
   within 0.01 m; stacked items sit on their host's top within 0.02 m;
   no grounded footprints overlap (helper: `footprintOverlaps`, rug
   excluded); and you have viewed the screenshot yourself, ideally with a
   1 m grid and a 2 m pole banded every 0.5 m in frame as a scale witness.
6. **Iterate one lever at a time.** If the screenshot fails, change the one
   thing that owns the problem (a fit target, a placement, or the camera),
   recapture, and compare. The tested builds below each took 2 to 3 rounds.

## Tested builds (in examples/)

- **Cozy Room** (Furniture Kit): 13 models, WASD walker, 3 collectible
  orbs. All 10 grounded models exact to target, 3 stacked items exact on
  their hosts, scripted key input moved the player and collected an orb.
  Screenshot: `examples/cozy-room.png`, scene: `examples/scenes/cozy-room.html`.
- **Race Track** (Racing Kit): oval loop from 4 corner and 4 straight road
  pieces, 3 cars lapping, 1 parked car, pits garage, trees, pylons, lights.
  Tiles measured exactly 10 m, cars exactly 1.9 m wide, car bases at
  0.20 m exactly on the road top. Screenshot: `examples/race-track.png`,
  6 second video of the cars lapping: `examples/race-video.mp4`,
  scene: `examples/scenes/race-track.html`.

The example scenes reference Three.js r160 and the pack GLBs by relative
path; serve the folder over HTTP to run them.

## Honest catches from the tests

- Accessor bounds in the GLB header matched Three.js Box3 for these packs
  (node transforms are identity), which is what lets make-manifest.py
  measure without a browser. Verify on a new pack before trusting it.
- Big kit buildings (the pits garage) are plain slabs from most angles.
  Place them as background, never as a foreground hero.
- A model can be internally consistent and still need per asset fitting:
  in the Furniture Kit the per asset scale factors ran 1.9x to 2.3x, so one
  global 2x gets you close and fit-to-target gets you exact.
