# Before/After Slider — SocialForge's standard comparison view

Rusty loved the first one (Capture Coach Tier 2 examples,
2026-11-12): **"Make sure to use this in SocialForge. Great for
comparing changes in all sorts of ways."**

## Use it whenever a person needs to judge a change
- **Capture Coach Tier 2** — the offer (show the examples) and the
  per-photo approval (their original vs the cleaned version).
- **Grouped-pieces editor** — compare an edit against the original
  snapshot before saving (the editor's own Compare toggle is the
  in-canvas sibling of this view; this builder is for shareable /
  chat-delivered comparisons).
- **Template redesigns and re-renders** — old version vs new version.
- **Brand-guide options** — original photo treatment vs a direction.
- **Seasonal refresh** — last year's post vs the refreshed draft.
- Anything else where "did the change help?" is the question.

## Build one
Write a small spec JSON (title, optional lede/note, and `pairs` of
`{title, sub, before, after}` image paths), then:

```
python3 make_slider.py spec.json output.html
```

Output is a single standalone HTML file (images downscaled and
embedded), draggable wipe + range slider, BEFORE left / AFTER
right, theme-aware. First production use:
`capture-coach/examples/tier2-before-after-slider.html`, built
from `capture-coach/examples/tier2-slider-spec.json`.
