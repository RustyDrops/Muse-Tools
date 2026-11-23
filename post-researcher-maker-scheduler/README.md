# Post Researcher, Maker & Scheduler

A skill that runs a Facebook Page's recurring posts end to end:

1. **Research** — national sources plus a local sweep, with every date and
   deadline verified on the source page itself, never from a snippet.
2. **Draft** — a fixed-size batch (e.g. Mon/Wed/Fri), exact post texts with
   links and days, hook first, deadlines stated plainly.
3. **Approval** — the owner approves the exact posts before anything moves.
   Nothing is published or scheduled without that OK.
4. **Make** — one bold graphic per post, code-drawn with Pillow
   (`make_post_graphic.py`, JSON config in, 1080×1080 PNGs out), and every
   render is viewed before use.
5. **Schedule** — posts scheduled on the Page with their graphics, one at a
   time, each receipt checked (`state: scheduled` is the confirmation).
6. **Log** — the batch and its verdicts recorded on the Page's timeline.
7. **Analyse** — each post gets one goal metric, checked at 24 hours and
   7 days; a winner/loser line feeds the next batch's research.

**v2.1 (2026-11-22): seven roles, one pipeline — the Muse-Tools roles.**
The Lookout (research), the Storyteller (drafts), the Gatekeeper (approval +
a three-question check: facts verified? brand clean? graphics viewed?),
the Maker (graphics), the Scheduler, the Archivist (the log) and the
Scorekeeper (results, fed back into the next batch). Roles in one flow,
not separate bots — and nothing schedules on autopilot.

First working run: STEMpact, a STEM-resources Page for middle schoolers —
weekly batch researched and approved Sunday evening, three posts with
graphics scheduled for the week.

See `SKILL.md` for the full playbook and `example-cards.json` for the
graphic maker's config format.
