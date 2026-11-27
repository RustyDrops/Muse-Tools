# Prompts - Laigter Sprite Lighting

Copy paste prompts. Replace the paths with your own.

## 1. Light one sprite set

> Take the sprites in [folder] and give them dynamic lighting with Laigter.
> For each sprite, generate the normal and specular maps, check each map
> with numbers (report min, max and std, a std near 0 means blank), view
> the normal map, and render a moving light preview GIF with
> render_moving_light.py. Show me the before/after sheet before anything
> goes into the game.

## 2. Batch a whole asset pack

> Run Laigter headless over every PNG in [pack folder], keeping the _n and
> _s suffixes, output to a maps subfolder per sprite. Report any sprite
> whose normal map comes out near blank and tell me why (flat shading or
> no alpha are the usual causes). Do not overwrite the originals.

## 3. Day to night variant

> Using the normal maps you made for [game], render the main props lit
> under a dim blue night light and a warm side torch light, next to the
> day versions. I want to judge whether we can do night scenes by
> relighting instead of repainting. Show me one contact sheet.

## 4. Audit maps I already have

> Check the lighting maps in [folder]. For each one, report size, min,
> max and std, flag blanks and wrong size maps, and pair each map with
> its diffuse sprite. Render one moving light preview from a pair you
> judge good and one from a pair you judge bad, so I can see the
> difference.

## 5. Bake lit frames for a retro engine

> My engine (Pyxel / Game Boy style / other retro) has no per pixel
> lighting. Take [sprite] and its Laigter normal map and bake lit frames:
> front light, left torch, right torch, and dim night, at the sprite's
> native size with nearest neighbor scaling. Name them so I can swap
> frames in code when the light changes.
