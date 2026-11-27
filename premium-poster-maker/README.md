# Premium Poster Maker (code-drawn, no AI)

Turn a real photo into a premium poster with Python and Pillow only. No image
model, no API, $0, fully reproducible: the same photo, style and settings give
the same poster every time.

Why coded instead of AI-generated:
- Text is drawn from the exact strings passed in. It can never be mangled.
- The photo is never re-rendered. A pet, a product and its label stay pixel
  true, which matters when the poster is selling that exact animal or product.
- It works offline and inside code-only pipelines (for example SocialForge,
  which bans generative imagery).

Styles (1600x2000, 4:5):
- `dark`    cinematic grade, dark top gradient, gold inset border, gold serif title
- `bright`  editorial grade, cream top fade, dark serif title
- `bw`      black and white fine art, white inset border, white title
- `vintage` sepia heirloom grade, brown title banner, cream border

The agent's part ("with your help"): pick the style, set `--focus-x/--focus-y`
on the subject, choose title and subtitle, run, VIEW the output, and adjust.
If the subject's head is near the top of the photo, add `--band`: the title
moves into a solid band above the photo so text never covers the subject.
That one rule came from a real test failure (a beagle whose face sat under
the title) and its fix.

Usage:
```
pip install Pillow
python3 poster_maker.py photo.jpg poster.png --style dark \
    --title "RUSTY JORDAN STUDIOS" --subtitle "Pet Keepsakes" --focus-y 0.60
python3 poster_maker.py puppy.jpg poster.png --style dark --band \
    --title "RUSTY JORDAN STUDIOS" --subtitle "Pet Keepsakes"
```

Options: `--focus-x`, `--focus-y` (subject centre, 0 to 1), `--font` (path to
a serif TTF; otherwise a system serif is used), `--band`.

Tested 2026-11-26 on two pet photos across all four styles plus the band fix.
Every output was viewed; text was exact in all of them, and the coded dark
and black-and-white versions held up next to AI-generated versions of the
same photos, at zero cost and with the photo untouched.
