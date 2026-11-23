# Append-only change logs — the Rigario add-on to SIM

Suggested by [@Rigario](https://x.com/Rigario) in a reply to our SIM test post:

> "I keep an append-only log of every change and why, then rebuild a clean
> page from it. That way a shrink can get checked against earlier corrections
> instead of simply trusting it."

We tested it, ran it through an Elephant-Goldfish review (two cold reviewers,
18 findings, none rejected), hardened it, and adopted it. It fixes SIM's
blind spot: a fact checklist derived from the *current* file ratchets down —
if one lossy shrink slips through, every later checklist is smaller and the
loss is invisible.

## Evidence (same 953-byte test file, 24 facts, 5 of them corrections)

- Page rebuilt from a 9-entry append-only log: **byte-identical, 24/24**.
- A deliberately bad shrink: **41.7% against the log** (all 5 corrections
  caught, including two direct reversals) vs **100% against itself** — its
  self-derived checklist had shrunk from 24 facts to 10.
- A second successive shrink: 70% vs the shrunk baseline, **29.2% vs the
  log** (17/24 missing cumulatively).

## The method (v2, after cold review)

1. **Per-file append-only log.** Header: an atomic fact list (fact +
   qualifier/negation + superseded-by) as structured data, plus the file's
   SHA-256 state hash. Body: appended entries only — semantic changes
   (ADD / CORRECTION / REMOVE, with why and what they supersede) and one-line
   OPS entries for shrink runs (in/out hash + gate result).
2. **Fail-closed sync.** Before any condensation, hash the file. If it
   doesn't match the log's last recorded state, refuse to edit and flag it.
   Discipline forgets; a hash check doesn't.
3. **Gate against the log, never the file alone.** Candidates are scored by
   the deterministic evaluator against the log's non-superseded facts.
   100% retention or the candidate dies.
4. **No log = no condensation.** Unlogged files may gain appended detail but
   are never rewritten or shrunk.
5. **Backfill is marked UNVERIFIED.** A retrospective log proves the page
   matches the log, not that either matches the original record. The
   guarantee starts at a live-verified baseline entry.
6. **Rebuilds are audits, not gates.** Periodically rebuild one file from
   its log and investigate drift; don't byte-diff every shrink.
7. **Entries are never removed.** Superseded values stay in the body for
   audit; the header fact list carries current values, which is what the
   gate loads — so cost stays bounded without breaking append-only.

## Pilot (on copies, before adoption)

Successive shrink PASS at 24/24 → planted lossy shrink FAIL at 41.7% with
every hard correction caught → unlogged tamper refused (OUT_OF_SYNC) →
mid-sequence correction appended: the pre-correction candidate then FAILed
(missing the new fact) and the corrected candidate PASSed.

## Files

- `log_gate.py` — check / gate / record CLI implementing the above (stdlib)
- `LOG_TEMPLATE.md` — start a log for a file
- `sim_evaluator.py` + `README.md` — the SIM loop this extends
