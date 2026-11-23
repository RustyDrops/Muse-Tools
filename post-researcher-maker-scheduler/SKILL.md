# Post Researcher, Maker & Scheduler

Run a Facebook Page's recurring posts end to end: research what's current,
draft the batch, get the owner's approval of the exact posts, make a graphic
for each, and schedule them. Built for a weekly cadence (e.g. Mon/Wed/Fri)
but works for any schedule the owner sets.

First working run: STEMpact (STEM resources for middle schoolers), weekly
batch approved Sunday evening, three posts scheduled with graphics.

## Seven roles, one pipeline (v2.1, 2026-11-22)

The Muse-Tools roles. One agent wears all seven hats inside this single
pipeline — never separate bots or subscriptions. Separate agents drift on
brand and add handoffs; named roles in one flow do not. (The Log step was
always its own job, so the Archivist makes seven, not six.)

1. **The Lookout** — research and trend sweep (step 1)
2. **The Storyteller** — drafts the batch in the Page's voice (step 2)
3. **The Gatekeeper** — approval + the three-question check (step 3,
   enforced again at step 5)
4. **The Maker** — the graphics (step 4)
5. **The Scheduler** — schedules, only after the gate (step 5)
6. **The Archivist** — logs the batch and its verdicts (step 6)
7. **The Scorekeeper** — measures results and feeds the next batch (step 7)

Deliberately NOT adopted from that idea: autopilot publishing, a separate
hosted scheduler (Postiz is AGPL-3.0 — a problem for a paid client product —
and an extra subscription; the Page connector already schedules), and
installing a 100+ skill pack wholesale. A cherry-picked reference set is
listed under Storyteller instead.

## The pipeline

### 1. The Lookout — Research
- Cover both national sources and a local sweep around the Page's community.
- **Verify every date, deadline, and eligibility rule on the source page
  itself** — never from a search snippet alone. If two pages from the same
  source disagree (e.g. two different submission dates), use only the fact
  both agree on, or leave it out and note the conflict.
- Respect the owner's inclusion rules (e.g. "tribal programs only when open
  to the public — if openness can't be verified, leave it out and say so").
- Note closures and dead weeks honestly (holidays, breaks) instead of
  padding the batch with stale items.
- **Start from the Scorekeeper's last report** (step 7): last batch's winner and
  loser set this batch's topics and formats before any new searching.
- **Trend sweep (Last 30 Days method):** when the Page's topic calls for it,
  sweep recent conversations across Reddit, X, YouTube and the web for what
  is rising *now* — then verify any fact you actually use on its source page,
  as above. A trend is a topic lead, never a source of facts.

### 2. The Storyteller — Draft the batch
- Exactly the number of posts the owner set, slotted to named days.
- Each draft: exact post text (under the platform limit — 1,024 characters
  for Facebook Page posts via the connector), the link it points to, and
  its scheduled day.
- Write for the Page's audience: hook first, plain language, deadline
  stated plainly when there is one.
- **Cherry-picked reference set** (inspired by the MIT-licensed Social Media
  Skills pack — use these twelve as a checklist, do not install the whole
  pack): brand-profile, voice-builder, audience-research, content-pillars,
  hook-writer, caption-writer, cross-platform-repurposing,
  platform-specs-and-validation, scheduling-and-queue, engagement-routine,
  plus this skill's own Lookout and Scorekeeper steps. The client's locked brand
  kit and banned-words list outrank every one of them.

### 3. The Gatekeeper — Approval gate, never skip
- Deliver the batch to the owner with the exact texts, days, and one short
  line on anything notable (a big deadline, a local find, a thin week).
- **Nothing is published or scheduled until the owner approves the exact
  posts.** Approval of a batch covers those texts; any change needs a
  fresh OK. The owner saying "create graphics and schedule them" approves
  scheduling those exact texts with graphics.
- **The Gatekeeper three-question check** — run it before the batch goes to
  the owner, and again before scheduling; any "no" stops the pipeline:
  1. Facts verified on the source page? (dates, deadlines, eligibility)
  2. Brand clean? (locked kit followed, banned words absent, nothing invented)
  3. Graphics viewed and QA-passed? (step 4 checks, on the final files)

### 4. The Maker — Make the graphics
- One graphic per post, code-drawn with Pillow (`make_post_graphic.py` in
  this folder) — no generative AI imagery needed: bold color card, kicker
  line, big title, one short sub, a deadline/date pill, Page name footer.
- 1080×1080 PNG works well for Facebook Page posts.
- **View every finished graphic before scheduling it.** Known failure:
  a fixed-position deadline pill overlapping the last line of the sub
  text when the sub wraps to 3 lines. The maker script flows the pill
  below the sub text — keep it that way, and still look at each render.
- Re-renders go to new filenames; apps cache images by path.

### 5. The Scheduler — Schedule
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

### 6. The Archivist — Log
- Record the batch on the Page's tracked item / goal timeline: what was
  scheduled, when, and the research notes file. Trends and verdicts
  accumulate there, not in chat.

### 7. The Scorekeeper — Measure and feed the next batch
- Before scheduling, name each post's ONE goal metric (e.g. saves, comments
  that name an intent, clicks) — reach alone is not a goal.
- Check at ~24 hours and ~7 days after each post goes live, using the
  platform's own insights for that Page.
- Write one winner/loser line per batch: which post won on its goal metric,
  which lost, and one plain-language guess why (hook, topic, format, timing).
- That line is the Lookout's first input for the next batch (step 1) and is
  logged with the batch (step 6). No report, no repeat: never schedule a
  new batch on a format the Scorekeeper has flagged as a loser twice without
  naming why this time is different.

## Files
- `make_post_graphic.py` — config-driven Pillow card maker (JSON in, PNGs out).
- `example-cards.json` — the three STEMpact cards from the first run.
