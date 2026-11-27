# Prompt 16 - Build a game scene with Kenney assets at real scale

Hand this to your Muse when you want a game scene from free Kenney
models that come out the right size next to each other, for $0.

> Build me a Three.js game scene using only models from the Kenney pack
> in [folder] (kenney.nl, CC0: check the License.txt inside the pack and
> keep it with the project).
>
> 1. Run the manifest tool in `kenney-assets/tools/` over the models I
>    name, so each one gets a real world fit target (a chair back is
>    about 0.9 m, a desk 0.75 m, a race car 1.9 m wide). If a model has
>    no target, add its real world size to the tool first. Never put a
>    hand-guessed scale number in scene code.
> 2. Load the scene with the kenney-fit helper: it measures each model,
>    fits it to its target, grounds it, and stacks anything that sits on
>    furniture onto its host. Place things with the placements map.
> 3. Add a 1 m grid and a 2 m pole banded every 0.5 m as a scale witness,
>    capture a screenshot, and view it yourself before reporting.
> 4. Report pass or fail per gate with measured numbers: all models
>    loaded with zero errors; final sizes within 2 percent of target;
>    bases at y = 0; stacked items on their hosts' tops; no overlapping
>    footprints. A gate you did not measure is a failed gate.
> 5. If I ask for changes, change one thing at a time (a fit target, a
>    placement, or the camera), recapture, and show me the difference.
>
> Do not post or publish anything. Show me the checked screenshot before
> calling the scene done.

Full workflow, both tools, and two tested example builds (a cozy room and
a race track, with a video) live in `kenney-assets/` in this repo.
