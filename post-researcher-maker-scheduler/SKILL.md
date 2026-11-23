# Post Researcher, Maker & Scheduler

Run a Facebook Page's recurring posts end to end: research what's current,
draft the batch, get the owner's approval of the exact posts, make a graphic
for each, and schedule them. Built for a weekly cadence (e.g. Mon/Wed/Fri)
but works for any schedule the owner sets.

First working run: STEMpact (STEM resources for middle schoolers), weekly
batch approved Sunday evening, three posts scheduled with graphics.

## The pipeline

### 1. Research
- Cover both national sources and a local sweep around the Page's community.
- **Verify every date, deadline, and eligibility rule on the source page
  itself** — never from a search snippet alone. If two pages from the same
  source disagree (e.g. two different submission dates), use only the fact
  both agree on, or leave it out and note the conflict.
- Respect the owner's inclusion rules (e.g. "tribal programs only when open
  to the public — if openness can't be verified, leave it out and say so").
- Note closures and dead weeks honestly (holidays, breaks) instead of
  padding the batch with stale items.

### 2. Draft the batch
- Exactly the number of posts the owner set, slotted to named days.
- Each draft: exact post text (under the platform limit — 1,024 characters
  for Facebook Page posts via the connector), the link it points to, and
  its scheduled day.
- Write for the Page's audience: hook first, plain language, deadline
  stated plainly when there is one.

### 3. Approval gate — never skip
- Deliver the batch to the owner with the exact texts, days, and one short
  line on anything notable (a big deadline, a local find, a thin week).
- **Nothing is published or scheduled until the owner approves the exact
  posts.** Approval of a batch covers those texts; any change needs a
  fresh OK. The owner saying "create graphics and schedule them" approves
  scheduling those exact texts with graphics.

### 4. Make the graphics
- One graphic per post, code-drawn with Pillow (`make_post_graphic.py` in
  this folder) — no generative AI imagery needed: bold color card, kicker
  line, big title, one short sub, a deadline/date pill, Page name footer.
- 1080×1080 PNG works well for Facebook Page posts.
- **View every finished graphic before scheduling it.** Known failure:
  a fixed-position deadline pill overlapping the last line of the sub
  text when the sub wraps to 3 lines. The maker script flows the pill
  below the sub text — keep it that way, and still look at each render.
- Re-renders go to new filenames; apps cache images by path.

### 5. Schedule
- Facebook Pages via the facebook-cli connector:
  `facebook-cli pages posts create --page-id <id> --text '<exact text>'
  --privacy PUBLIC --file <graphic.png> --scheduled-publish-time <unix>`
- Pick a consistent time of day in the Page's timezone (9:00 a.m. local
  works) and compute the Unix timestamps with `date -d` in that timezone.
- Post text contains apostrophes and emoji — pass arguments through a
  script (e.g. Python subprocess list form), not hand-quoted shell.
- One post at a time; check each receipt before doing the next.
  Only `state: scheduled` confirms a schedule. After an unknown outcome,
  timeout, or refusal, do **not** retry — ask the owner to check the Page.
- Report back: each post's day, time (with timezone), and state.

### 6. Log
- Record the batch on the Page's tracked item / goal timeline: what was
  scheduled, when, and the research notes file. Trends and verdicts
  accumulate there, not in chat.

## Files
- `make_post_graphic.py` — config-driven Pillow card maker (JSON in, PNGs out).
- `example-cards.json` — the three STEMpact cards from the first run.
