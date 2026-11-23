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

First working run: STEMpact, a STEM-resources Page for middle schoolers —
weekly batch researched and approved Sunday evening, three posts with
graphics scheduled for the week.

See `SKILL.md` for the full playbook and `example-cards.json` for the
graphic maker's config format.
