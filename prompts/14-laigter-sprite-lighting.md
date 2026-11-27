# Prompt 14 - Light flat sprites with Laigter

Hand this to your Muse when a 2D game looks flat and you want real
dynamic lighting on the sprites you already have, for $0.

> Give my flat 2D sprites dynamic lighting using Laigter (free, from
> github.com/azagaya/laigter). Work through the sprites in [folder]:
>
> 1. For each sprite, generate the normal and specular maps (occlusion
>    and parallax too, but only for sprites with a transparent
>    background, opaque sprites return those blank).
> 2. Check every map with numbers: report size, min, max and standard
>    deviation. A std near 0 means the map is blank, say so plainly and
>    tell me the likely cause.
> 3. View at least one normal map directly and confirm the raised parts
>    and edges read on it.
> 4. Render a moving light preview (a GIF of a light orbiting the
>    sprite) and a before/after sheet for the main character or prop,
>    and show me both.
> 5. Tell me how to wire the maps in my engine (Godot, Unity, or baked
>    frames if the engine has no per pixel lighting, like Pyxel).
>
> Do not overwrite my original sprites. Keep the _n and _s suffixes.
> Show me the checked preview before calling any of it done.

Full workflow, the verified Linux headless run line, and a tested
example set live in `laigter-sprite-lighting/` in this repo.
