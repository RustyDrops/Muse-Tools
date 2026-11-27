# Laigter Sprite Lighting - Flat Sprites That React to Light

Give flat 2D sprites real dynamic lighting for $0. [Laigter](https://github.com/azagaya/laigter)
(GPL-3.0, free on GitHub and itch.io) reads one flat sprite and generates the
maps a game engine needs: normal, specular, occlusion and parallax. With a
normal map, the same sprite brightens, shades and glints as a light moves,
instead of staying flat.

Tested end to end 2026-11-26: Laigter 1.11.0 ran headless on a Linux VM,
generated the maps for a 512x512 crate sprite, and a moving light preview
rendered from its own maps. Example files are in `examples/`.

## The workflow (follow it in order)

1. **Pick sprites with readable shading.** Laigter infers height from the
   sprite's own light and dark areas and its alpha edge. Flat color blocks
   with no internal shading give flat maps. Characters, crates, rocks,
   doors and props with painted shading work best.
2. **Keep the alpha.** Occlusion and parallax are derived from the
   transparent edge. A fully opaque rectangular sprite still gets good
   normal and specular maps, but its occlusion and parallax maps come out
   blank white (verified in the test below). Cut the background out first
   if you need those two.
3. **Generate the maps.** GUI: open the sprite in Laigter, adjust the
   normal strength and bevel sliders, export. Headless CLI (verified on
   Linux, see the run notes below):
   `laigter -g -s -d <sprite.png> -n -c -o -p -l <out-folder>`
   Flags: `-g` no GUI, `-s` software OpenGL, `-n` normal, `-c` specular,
   `-o` occlusion, `-p` parallax.
4. **Check the maps with numbers, not vibes.** A real normal map has wide
   value spread (the test map: min 11, max 255, std 62.5). A map with
   std near 0 is blank, whatever the file size says. View the normal map
   directly too: edges and raised parts should read as colored ridges on
   the purple base.
5. **Preview with a moving light before wiring the engine.**
   `render_moving_light.py` in this folder takes diffuse, normal and
   specular PNGs and writes a 24 frame orbiting light GIF plus a
   before/after sheet. Needs Python with Pillow and numpy. If the GIF
   does not visibly relight, the maps are wrong, fix them here, not in
   the engine.
6. **Wire the engine.** Godot: put the normal map in the texture's
   Normal slot on a CanvasItem material and add a PointLight2D. Unity:
   sprite material with Normal Map texture type, plus a 2D light.
   Pyxel and other retro engines have no per pixel lighting: bake the
   preview instead, render the sprite lit from the angles your game
   needs (day, torch side light, night) and swap frames.

## Linux headless run notes (verified 2026-11-26)

- Download `Laigter-x86_64.AppImage` from the GitHub releases page
  (1.11.0, about 28 MB).
- The AppImage ships only the xcb Qt plugin, so `QT_QPA_PLATFORM=offscreen`
  fails. Run it under a virtual display with the extract and run flag:
  `xvfb-run -a env APPIMAGE_EXTRACT_AND_RUN=1 ./Laigter-x86_64.AppImage -g -s -d sprite.png -n -c -l out`
- Two warnings are harmless: a duplicate `normal-suffix` option warning
  and undefined suffix warnings for occlusion and parallax.

## Tested example (in examples/)

One existing flat sprite, a 512x512 sci-fi storage crate:

- `crate_diffuse.png` - the flat original
- `crate_normal.png` - Laigter normal map (min 11, max 255, std 62.5)
- `crate_specular.png` - Laigter specular map (values 20 to 110, std 30.4)
- `before_after.png` - flat vs lit frame vs normal map, viewed and checked
- `moving_light.gif` - 24 frames, light orbiting, rendered from the maps.
  Opposite frames differ by 9.42 mean absolute pixel value, so the light
  movement is measurable, not just claimed.
- Occlusion and parallax for this sprite came out blank (std 0.0): it is
  fully opaque, see step 2. They are not shipped as examples.

## Games: where this earns its keep

- **Torch, lamp and spell light in 2D games.** One normal map pass turns
  every prop in a dungeon or night scene into something the light plays
  across. This is the cheapest big visual jump available to a flat game.
- **Day to night without repainting.** Relight the same sprites under a
  dim blue light instead of drawing a night set.
- **Batch it.** The CLI takes a folder of sprites, so a whole asset pack
  gets maps in one run. Keep the suffix convention (`_n`, `_s`) so the
  engine import stays mechanical.
- **Budget the strength.** Too much normal strength makes pixel art look
  like wet clay. For pixel sprites, lower the strength and check at the
  game's real display size, not zoomed in.

## Prompts

Copy paste prompts that run this workflow well are in PROMPTS.md in this
folder, and as prompt 14 in the repo prompts/ folder.

## Rules

- Check every map with numbers and by eye before it goes in a game.
- Sprites with alpha for occlusion and parallax, opaque is fine for
  normal and specular only.
- Laigter is GPL-3.0 software you run, its output maps are your own
  work. The sprites you feed it keep their own licenses.
- Nothing posts or publishes on the back of this skill without the
  user's approval of the exact final version.
