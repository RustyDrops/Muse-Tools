# Prompt 17 - Generate a verified game level, then draw it as a fantasy map

Hand this to your Muse when you want a game map whose layout is
guaranteed in code, plus a hand-drawn fantasy version of the same map.

> Using the tool in `wfc-level-generator/`:
>
> 1. Run `python wfc5.py --sheet` (Python 3.10+, `pip install pillow`).
>    It generates terrain with a WaveFunctionCollapse solver over a
>    noise layout and writes only maps that pass every gate in code:
>    water never touches land directly, one connected landmass, blobby
>    lakes and forest, three clearings, and a dirt path that is fully
>    connected with no diagonal joints. If it exits nonzero, tell me the
>    error - that means no verified map exists, and I would rather hear
>    that than get a quiet bad map.
> 2. Open the contact sheet and the keeper PNG and look at them
>    yourself. Report the keeper seed, how many candidates passed, and
>    the keeper's water and sand shares from its JSON.
> 3. Then turn the keeper into a fantasy map with image generation,
>    using the keeper PNG as the input image and this prompt exactly:
>    "Redraw this flat game map as a hand-drawn fantasy world map,
>    keeping the geography EXACTLY the same. Same square canvas, same
>    top-down view. Every coastline, lake shape, forest blob, and the
>    full route of the brown path must stay in the same place and keep
>    the same shape. Do not add or remove any land, water, forest, or
>    path, and do not add rivers, roads, mountains, or islands that are
>    not in the source map. Style: ink and watercolor on warm parchment,
>    like a storybook atlas plate. Water: layered blue washes, darker in
>    the deep center and pale at the edges, with a soft sandy beach rim
>    following the shore exactly, plus a few tiny hand-drawn wave marks.
>    Forest: each dark green area becomes a dense cluster of small
>    individually drawn round trees with ink outlines. Grassland: a soft
>    green watercolor wash with subtle paper texture and a few tiny
>    grass tufts, no grid lines. The brown path becomes a winding dirt
>    road with soft edges and occasional small stones, following the
>    exact route of the original. The white ring clearing becomes a
>    tiny campsite with two small tents. The orange X clearing becomes a
>    small village of three tiny houses with red roofs. The grey stone
>    circle becomes a ring of mossy standing stones. Finish with a thin
>    ink border around the map and one small compass rose in an empty
>    grass corner. No text, no labels, no legend, no UI elements. The
>    result must still read clearly as the same map, just drawn as a
>    fantasy world."
> 4. Compare the fantasy version against the keeper before showing me:
>    same lake, same shores, same forest blobs, same path route. If the
>    geography moved, regenerate it. The JSON/TMX grid stays the source
>    of truth for gameplay; the fantasy map is the art on top.
>
> Tested end to end 2026-11-26: the example keeper and its fantasy
> restyle are both in `wfc-level-generator/examples/`.
