# Job Health Board — Muse procedure (read-only)

Source of truth is the live cron list, NOT files under `workspace/goals/*/crons/`
or `workspace/cron.d/`. Those files include archived and closed jobs.

When the user asks for job health, Muse runs, in order:
1. `cron.list` — keep only `is_system: false` jobs for the user board.
   System jobs (feed-pulse, deterministic-doctor, profile-image, heartbeat)
   are counted as a group, not listed one by one.
2. For each user job: `cron.status` (enabled, schedule, last run, next run)
   and `cron.runs` (recent run status).
3. Report short, one line per job: id, schedule, enabled, last run, next run.
   Flag any failure plainly. Do not paste full run logs.

Guardrails:
- Read-only. This board never edits, disables, deletes, or recreates a job.
  Deleting and recreating a working job revokes its grants — never do that
  as a repair.
- If a job fails, report it and ask before any change. A permission change
  needs a live shakedown while the user is present, never allow-once.
- Keep church and personal jobs in separate messages when reporting.
  (Church jobs: Sunday slide deck, weekly sermon MP3 — report only in a
  church context.)
