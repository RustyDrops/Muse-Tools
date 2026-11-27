# Hand-Drawn Story Animation

Make short hand-drawn style story videos (Storytime, illustrated explainers, gentle couple Reels) as code-drawn HTML animations. No image generation anywhere in the pipeline. Nothing posts; Rusty approves each exact version.

## Use Gemini for the art. This is the whole point of the skill.

Ann's flat shape art is the known weak spot. The division of labor that works, decided with Rusty on 2026-11-15 and proven on the Bramble test on 2026-11-26:

- **Gemini drafts the hero artwork as SVG code.** First an `analyze` call on the current frames for a blunt critique and a redesign spec (palette hexes, detail passes), then a `generate` call (gemini-4-argon) that writes the character groups as Bezier SVG with base plus shade plus highlight fills, clipped fur or feather detail passes, and soft ground shadows. The exact prompts live in PROMPTS.md; use the current version there, do not improvise a new one without logging an iteration.
- **Ann rigs and ships it.** Timeline beats, draw-on or fade staging, speech bubbles, captions, the eye swap, rendering, measured QA, and the phone-size viewing gate all stay with Ann.

Hard limits that do not move:
- Gemini image and video generation is HARD STOPPED (Rusty's call, 2026-11-03). Never call `gemini-api image` or `gemini-api video` for this skill. Gemini is used for analysis and text/code generation only. Lifting the stop requires Rusty explicitly asking for the stop itself to be lifted.
- No other image generation either. Every pixel is code: SVG paths, CSS, canvas.
- Run Gemini through the connector helper so the key stays a surrogate: `python3 ~/workspace/custom-connectors/custom.google-gemini/bin/gemini.py cli analyze ...` and `... cli generate --stdin -m gemini-4-argon --stream=false`.

## Workflow

1. **Script first.** One scene, 15 seconds, 3 beats, from an existing story script where one exists. Lock the lines before any art.
2. **Gemini critique.** Analyze the current best frames (or a first flat draft) with the critique prompt in PROMPTS.md. Save the raw reply next to the project as gemini-critique.txt.
3. **Gemini art.** Run the art prompt from PROMPTS.md. Extract the two groups (`bearBed` hero group, `owlTree` set group) from the reply, verify the SVG parses as XML, save as gemini-art.svg. Check the groups carry `bearEyesOpen` and `bearEyesClosed` subgroups if the story needs the sleepy eye swap.
4. **Build.** `tools/build_scene.py --art gemini-art.svg --out scene.html --frame slight` plus `--cap1/2/3` and `--bub1/--bub2` for the scene's lines. The builder adds the sky gradient, moon and halo, 3-tier star field, grain overlay, line boil, and the timeline.
5. **Probe before you pay for a render.** `tools/render_frames.py --scene scene.html --frames qa --probe 7.5,11,14.5`. View every probe at phone size yourself. Fix art problems at the prompt level (log the iteration in PROMPTS.md), not by patching paths by hand.
6. **Full render.** `tools/render_frames.py --scene scene.html --frames frames --mp4 out.mp4`. Draft size is 540x960 (`--scale 1`); production is 1080x1920 (`--scale 2`) from the same file. Budget about 7 minutes per 15 seconds at draft size on this VM.
7. **QA gate, measured.** Console errors none, seek purity diff 0.0 (the tool prints it), ffprobe facts recorded, freezedetect checked, and frames at the beat boundaries viewed at phone size. Never call it checked from a builder report alone.
8. **Deliver in chat** with the MP4 attached, a before/after frame comparison when the art changed, and the honest flaw list. Approval per exact version.

## Sizing rules (learned the hard way, encoded in the art prompt)

- Canvas 540x960 viewBox, 9:16. A slight frame sits at 14px inset; ALL art stays inside x 30 to 510, y 30 to 930. A tree trunk crossing the frame edge was the v3 flaw.
- Hero character bounding box roughly x 50 to 370, y 545 to 835; hero head at least 150px wide at this size (about 300px at production scale).
- Second character at least 95px tall or it reads as a sticker.
- Captions live at y 886, one short line, cream #F3E9CF on the dark ground. Keep caption text under about 38 characters per line at 25 to 29px.
- Speech bubbles: soft cream, thin stroke, deckled edge. No pure white comic balloons; Gemini's critique was right that they break the bedtime mood.

## Frame options (build_scene.py --frame)

- `slight` (default): a soft dark outer line at 6px inset plus a thin wobbly cream inner line at 14px inset, 45% opacity. Reads as a picture-book plate, keeps attention inside the scene.
- `none`: for scenes that bleed to the edge on purpose.

## Iteration routine for the prompt

Change ONE lever per prompt version, name what it targets, probe-render, view, and log it in PROMPTS.md with the verdict. The v1 to v2 log there is the worked example: sizing boxes fixed the cropped trunk, the canopy clause fixed the stacked-disc tree, the owl minimum size fixed the sticker owl.

## Proven results

- Bramble and the Sleepy Stars, 15s: v2 (Ann art) passed the format test; v3 (first Gemini art) fixed character shading and palette; v4 (prompt v2 plus slight frame) fixed canopy, trunk crop, and bed shape, and is the current keeper. Full records in `~/workspace/x-bookmarks-2026-11-26/category-c-tests/hand-drawn-98-105/` (RESULT.md, RESULT-V3.md).
- Fit: Storytime PASS. Christian couples format fits (two characters, one bubble each, illustrated only) but human figures in this style are still untested; run one 10 second couple probe before adopting it there.
