# Prompts for the WFC level generator

The rule behind every prompt: the generator owns the geography, the image
model owns only the drawing. A restyle that moves a lake is a failed
restyle, however pretty it is.

## 1. Turn a generated map into a fantasy map (image generation)

Attach the map PNG the tool wrote (`map_v5.png` or your own `--out` name)
as the input image, then use this prompt exactly:

```text
Redraw this flat game map as a hand-drawn fantasy world map. Keep the same geography: same square canvas, same top-down view, and the lake, the forests, the clearings, and the path stay in the same places, at the same sizes, covering the same areas, with the path following the same route between the same three clearings. Do not add or remove any land, water, forest, or path, and do not add rivers, roads, mountains, or islands that are not in the source map.

The source is drawn on a square pixel grid, so every outline steps and zigzags. Redraw every outline as if tracing it with a soft brush in one continuous flowing stroke. Round off every corner. There are no right angles and no straight segments anywhere except the map border itself, and no visible pixels or grid steps. The shapes stay recognizably the same map, just drawn the way a cartographer would draw them by hand.

Style: ink and watercolor on warm parchment, like a storybook atlas plate. Water: layered blue washes, darker in the deep center and pale at the edges, plus a few tiny hand-drawn wave marks. The sandy beach is a smooth ribbon of even width all the way around the lake, both of its edges flowing curves. Forest: each dark green area becomes a dense cluster of small individually drawn round trees with ink outlines, and the outline of each woodland billows softly like treetops seen from above, with no straight edges. Grassland: a soft green watercolor wash with subtle paper texture and a few tiny grass tufts. The brown path becomes a smooth, gently curving dirt road with soft edges and occasional small stones, following the exact route of the original, with no notches or steps in its sides. The white ring clearing becomes a tiny campsite with two small tents. The orange X clearing becomes a small village of three tiny houses with red roofs. The grey stone circle becomes a ring of mossy standing stones.

Finish with a thin ink border around the map and one small compass rose in an empty grass corner. No text, no labels, no legend, no UI elements. The result must still read clearly as the same map, just drawn as a fantasy world.
```

Why the smoothing paragraph is worded that way: the first tested version
said "keep every outline exactly the same", and the model faithfully
copied the pixel steps - blocky shores, rectangular forests, a notched
road. Naming the fix per element (flowing coastline, even beach ribbon
with two smooth edges, billowing woodland outline, road with no notches)
is what actually melted the grid away. Geography is locked by area,
place, and route, not by outline.

Tested 2026-11-26 on the example keeper (seed 14), result in
`examples/fantasy_restyle.jpg`. Verdict: geography held - same lake,
same forests, same path route, markers converted as asked (campsite at
spawn, village at camp, standing stones at the objective) - and the
outlines are fully hand-drawn smooth. One small nit: the model drew a
second tiny compass rose mid-map; harmless, and a regeneration or a
crop removes it. Check any restyle against the source grid before using
it: if the geography moved, regenerate, do not patch by hand.

Variants: swap the style paragraph's opening for "flat vector storybook
style, bold shapes, no texture" for a cleaner game-ready look, or "aged
pirate chart, sepia ink on stained parchment, everything in brown line
work" for a handout prop. Keep the geography paragraph, the smoothing
paragraph, and the marker sentences unchanged in every variant.

## 2. Generate a batch of levels and pick the keeper

```text
In wfc-level-generator/, run: python wfc5.py --seeds 24 --sheet --out levels/map
Then open contact_sheet_v5.png and levels/map.json yourself. Report:
the keeper seed used, how many of the candidates passed all gates, the
keeper's water and sand shares, and confirm the JSON says
"gates_passed": true. If the command exits nonzero, report its error
line instead of working around it - a nonzero exit means no verified
map exists, and that is the answer.
```

## 3. Verify a map someone hands you

```text
Run: python wfc5.py --verify <file>.json (or .txt) in wfc-level-generator/.
Report the gates_passed verdict and, if it failed, the exact failure
list from the output. Do not soften a failure: the gates are the
contract, and a map that fails them is not a keeper.
```
