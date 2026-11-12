# 05 — Design-System Styling Setup

Give every tool your Muse builds one consistent look — chosen by you, not
by whichever library a builder happened to reach for. This prompt has your
Muse compare a few real design systems on the *same* small test card,
measure what each one costs to build with, then walk you through picking
your own styling and lock it into a single reusable theme file.

No styling choices are baked in. Your colors, your corners, your shadows —
the prompt asks, shows you the options live, and writes down exactly what
you picked.

## Hand this to your Muse

```text
Help me standardize the look of the tools you build for me. Work in four
phases, and show me real rendered results — not descriptions — at each
decision point.

PHASE 1 — COMPARE (build the same card in each candidate system)
Pick three candidate design systems. Good starting candidates:
  - Mantine — https://mantine.dev (repo: https://github.com/mantinedev/mantine)
  - Astryx by Meta — https://github.com/meta/astryx
  - shadcn/ui — https://ui.shadcn.com
Build the SAME small test card in each, as its own page: a heading and
subtitle, a badge, a progress bar at 60%, a Week/Month/Year segmented
control, a text input with a Save button that shows a success message,
and a Preview button that opens a dialog. Use a placeholder brand color
for now. For each system, measure and report: build time, how many fix
passes it needed, whether every control actually works when clicked,
and how it behaves at phone width. Put the survivors side by side so I
can compare the feel myself, then recommend one — speed and reliability
count, but my feel pick wins ties.

PHASE 2 — MY STYLING (ask me, one choice at a time, with live previews)
Ask me these one at a time, rendering the test card with my pick applied
before moving on:
  1. My brand color (a hex value), and whether I want dark mode too.
  2. Corner feel: sharp, rounded, or soft/pill-shaped controls.
  3. Edge feel: flat borders, soft shadows, or strong shadows.
  4. Density: roomy or compact.
Never substitute your own taste for mine, and never merge two directions
I didn't ask you to merge.

PHASE 3 — LOCK IT (one theme file, verified)
Write ONE theme file in my chosen system's own theming API that holds
exactly the choices from Phase 2 — brand color, radius, shadows,
component defaults. Then verify it like you mean it:
  - My brand hex must survive exactly in the rendered output (some
    systems shift colors algorithmically; if yours does, say so and
    show me the shifted value before we accept it).
  - Typecheck the theme and a sample card against the real installed
    packages. Zero errors, or tell me what's failing.
  - Use only component names and props you verified against the
    system's docs or installed package. If you're unsure an API
    exists, flag it in the output instead of guessing silently.

PHASE 4 — MAKE IT THE STANDARD
Save the theme file somewhere stable and record in your memory: "Our
standard look for professional/informative tools lives in <theme file>,
using <system>. Use it by default; creative one-off pieces may opt out
when I say so." From then on, every new tool starts from that theme
instead of inventing a new look.

Report at the end: which system won and why, what my locked choices are,
where the theme file lives, and what it cost to run the comparison.
```

## Why this works

- **Same card, every system.** A fixed test piece makes the comparison
  honest — differences you see are the library, not the content.
- **Measured, not vibes.** Build time, fix passes, and working controls
  are numbers. Feel is yours to judge on the rendered side-by-side.
- **One theme file.** Styling decided once, imported everywhere, is what
  turns "each tool looks different" into a family resemblance — and it
  makes future builds faster and cheaper, because nobody (human or
  model) re-derives the look each time.
- **Verified, not assumed.** A typecheck against the real packages
  catches invented APIs that a confident-looking answer can hide.

## Credits

The candidate systems named in the prompt are other people's excellent
work — this repo just points at them:

- **Mantine** — MIT-licensed component library by the Mantine team.
  Site: https://mantine.dev · Code: https://github.com/mantinedev/mantine
- **Astryx** — Meta's open-source design system, MIT-licensed.
  Code: https://github.com/meta/astryx · Docs: https://astryx.atmeta.com
- **shadcn/ui** — MIT-licensed component collection.
  Site: https://ui.shadcn.com · Code: https://github.com/shadcn-ui/ui

The compare → choose → lock → standardize method is ours; the libraries
are theirs. If you publish your own theme, credit the library you built
it on the same way.
