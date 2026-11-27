# Laigter Sprite Lighting

Flat 2D sprites that react to light, for $0. [Laigter](https://github.com/azagaya/laigter)
(free, GPL-3.0) turns one flat sprite into normal, specular, occlusion and
parallax maps, so a game light can shade and glint across it instead of the
sprite staying flat. `SKILL.md` is the full workflow: pick sprites with
readable shading, keep the alpha if you need occlusion and parallax,
generate in the GUI or with the verified headless CLI line, check the maps
with numbers (a real normal map has wide value spread, a blank one has std
near 0), and preview with a moving light before wiring your engine.
`render_moving_light.py` renders that preview: a 24 frame orbiting light
GIF and a before/after sheet from any diffuse, normal and specular set
(Python, Pillow, numpy). `PROMPTS.md` has five copy paste prompts: light a
sprite set, batch a whole asset pack, build a day to night variant, check
maps you already have, and bake lit frames for a retro engine like Pyxel.
`examples/` holds a tested set from a real run on 2026-11-26: a flat crate
sprite, its Laigter normal and specular maps, the before/after sheet and
the moving light GIF.

Copy `SKILL.md` into your Muse's custom skills folder, or just ask your
Muse to light your next 2D game and point it here.
