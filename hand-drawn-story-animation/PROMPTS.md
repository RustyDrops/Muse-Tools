# Prompts - Hand-Drawn Story Animation

The two Gemini prompts for this skill, with the iteration log. Change one lever per version and log it here with the verdict, the same routine used to get from v1 to v2.

## 1. Critique prompt (analyze)

Attach the two best current frames with `gemini-api analyze -i frame1.png -i frame2.png` and use this as the question:

> You are an expert children's book SVG illustrator whose code-drawn art is known for organic cubic Bezier silhouettes, every fill carrying a base color plus a shade color plus a highlight color, subtle grain tooth around 0.12, clipped detail passes such as individual fur strokes inside a shape, and soft stippled ground shadows. These frames are from a flat code-drawn animation. Critique what makes them look flat and amateur, in at most 8 short bullet points. Then give a concrete redesign spec I can code: exact palette hexes for sky, moon, stars, tree, grass, and each character (base, shade, highlight); the detail passes each character needs; and composition fixes. Keep the same layout as the frames. Plain text, no code yet.

## 2. Art prompt, CURRENT VERSION v2 (use this one)

Pipe this text to `gemini-api generate --stdin -m gemini-4-argon --stream=false`. Swap the character descriptions and palette for a new story; keep the frame, sizing, and canopy rules unless an iteration below says otherwise.

> Write SVG code for a children's picture-book night scene, viewBox 0 0 540 960. Output ONLY two <g> elements, no explanation, no markdown fences, no <svg> wrapper.
>
> FRAME AND SIZING RULES, mandatory:
> - A picture frame will be drawn at inset 14px. Keep ALL artwork inside x 30 to 510 and y 30 to 930. Nothing may touch or cross the frame, especially not the tree trunk.
> - Bear group bounding box: x 50 to 370, y 545 to 835. Bear head at least 150px wide. Eyes at about y 640.
> - Owl and tree group bounding box: x 295 to 505, y 130 to 570. The trunk is a tapered shape that stays fully inside x 440 to 505 and ends at y 570. Owl body at least 95px tall, perched on a branch at about y 380, owl occupying x 390 to 500, y 250 to 395.
>
> Style rules, mandatory: organic cubic Bezier silhouettes only, no plain ellipses or rectangles for body shapes. Every fill uses base plus shade plus highlight from this palette. Thin warm dark outlines (#231815, stroke-width 3 to 4, round joins) or no outline where value contrast works. Add clipped detail passes: fur strokes on the bear, feather scallops on the owl. Soft blurred ellipse ground shadow under the bed.
>
> CANOPY RULE, read carefully: the oak canopy must be ONE irregular cloud silhouette made of 4 to 5 overlapping lobes merged into a single outline path, with separate shadow crescent paths tucked under the lobes. Do NOT draw the canopy as separate stacked circles, discs, coins, or ellipses. The outline must wander like a real tree crown, wider than it is tall.
>
> Palette: bear fur base #8D5B38, shade #5E3A21, highlight #B07850; muzzle #CEAB86, muzzle shade #A88562; inner ear and cheek #B86B65; eyes and nose #231815 with #FFFFEE pin highlights. Owl feathers base #6E5845, shade #4A392C, highlight #8F755E; belly and face discs #D8CCA8, shade #B0A27E; beak #D69336; iris #E2A32D. Quilt base #99342C, shade #661E18, highlight #BD4C43; sheet #EADBCE, shade #BFAF9F. Bark base #4A3525, shadow #2C1E14, highlight #664C37. Foliage base #243D2F, shade #16281E, crest #385A44.
>
> Group 1, id="bearBed": a baby bear sitting up in bed inside the bear bounding box. Plump quilt with a rolled cream cuff and fold ribbons across it, blurred ground shadow beneath. Bear head and shoulders above the quilt: asymmetric rounded head, ears indented into the scalp with rose inner ears, heart-wedge muzzle, sleepy open eyes with pin highlights, cheek blush, clipped fur strokes along jaw and crown, a gold rim highlight stroke along the right side of the head. Paws resting on top of the quilt. Also include inside this group a group id="bearEyesOpen" wrapping the open eye elements, and a group id="bearEyesClosed" with two closed curved eyelid paths at the same eye positions.
>
> Group 2, id="owlTree": the oak and owl inside the owl bounding box, following the CANOPY RULE and trunk rule above. Gnarled trunk with bark fissure lines, one horizontal branch reaching left from the trunk at about y 380, and the owl perched on that branch: head tilted slightly down toward the lower left, twin heart-shaped face discs with feather ticks, amber iris eyes, small beak, scalloped breast feathers in 3 tiers, a folded wing with 3 primary tips, talons gripping the branch.
>
> Keep each group self-contained with its own <defs> clip paths if needed, ids prefixed bb- or ot- to avoid collisions.

## Iteration log

### v1 (2026-11-26, first Gemini art, became scene v3)
No sizing boxes, no frame rule, no canopy rule. Result: characters were a clear win over Ann's flat art (shading, fur strokes, scallops all landed), but three flaws showed on viewing: canopy drawn as stacked dark discs, trunk cropped by the right frame edge, round quilt reading like a beanbag, owl a touch small.

### v2 (2026-11-26, current, became scene v4)
Levers changed, one per flaw:
- Added FRAME AND SIZING RULES with exact bounding boxes and the 30 to 510 / 30 to 930 safe area. Verdict: trunk fully inside the frame, owl bigger and clearly perched. FIXED.
- Added the CANOPY RULE (one merged cloud silhouette, discs named and banned). Verdict: canopy is one wandering cloud with undercut shading. FIXED, though still a simple single cloud; a future lever could ask for a secondary smaller crown behind it for depth.
- Required paws on the quilt and named the rolled cuff and pillow zone via the bounding box and bed description carried from v1. Verdict: bed reads as a bed, plaid quilt with cuff and pillow. FIXED.
- Kept everything else identical so the comparison stayed clean.

Open levers for v3 of the prompt, not yet tried: branch drawn as a straight peg (ask for a tapered branch with two twig forks and bark lines), single-cloud canopy depth (background crown), and a hand-lettered caption treatment (needs an embedded font on the render side first).
