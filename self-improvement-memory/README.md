# Self-Improvement Memory (SIM) for agent memory files

Shrink an AI agent's memory/context files **without silently losing facts** —
using the proposer / evaluator / selector loop from Yu et al.,
*Self-Improvement Memory Enables Continual Recursive Self-Improvement*
(arXiv 2611.18856, Google Cloud AI / DeepMind / Penn State, Nov 2026),
adapted for a personal agent's memory system.

The paper gives a harness optimizer a memory of its own past edits, grouped by
the recurring problem each edit addressed, with the rationale, the **predicted**
outcome (written before evaluation), the **observed** outcome, and provenance.
Both the proposer and the selector read that log, so round 2 doesn't repeat
round 1's failures. In their paired coding test that was worth +2.36 points
(p = 0.003, 9 of 10 runs) over continuing with the harness alone.

## The loop

1. **Propose** 3–5 candidate rewrites of one memory file (tighten, restructure,
   compress, split…). Before evaluating, write each candidate's predicted
   saving + retention into the SIM log.
2. **Evaluate** deterministically — never by asking an LLM "does this look
   complete?". `sim_evaluator.py` checks every candidate against a fact
   checklist (regex per fact) for the original file.
3. **Select** with a hard gate: 100% retention of hard facts (dates,
   negations, qualifiers, "do not" rules) first, then size saving. A candidate
   that loses a hard fact is rejected no matter how small it is.
4. **Log** the observed result next to the prediction, grouped by root cause.
   Failed attempts stay in the log — they are the point.

## What a real test showed (2026-11-22)

One 1,143-byte topical memory file, 24-fact checklist, copies only:

| Candidate | Size | Saving | Facts kept | Verdict |
|---|---|---|---|---|
| Tighten prose only | 1,056 B | −7.6% | 24/24 | pass |
| Aggressive compression | 340 B | −70.3% | 14/24 | **rejected** |
| Structured rewrite | 1,034 B | −9.5% | 24/24 | pass, round-1 winner |
| Split into 2 files | 1,086 B total | −5.0% | 12/24 in the loaded file | **rejected** |
| Round 2: structured + tightened, proposer read the failure log first | 953 B | **−16.6%** | **24/24** | **winner** |

Lessons that generalised:

- The biggest "saving" was silent fact loss. Dates, negations and qualifiers
  *are* the facts in memory files.
- Splitting a file only helps if your loader actually reads both halves.
  Score total system bytes and what a single load contains.
- Round 2 won because the proposer read *why* round 1 failed — the SIM effect
  in miniature.

## Keep it capped (the part the paper doesn't do for you)

The paper reads the entire SIM every round, untruncated. For a personal agent
whose problem is pre-prompt growth, that eats the savings. Our adaptation:

- One SIM log **per topic/file**, loaded only with that file — never a global
  log in every prompt.
- Prune an attempt once its lesson has become a standing rule.
- Track net benefit: bytes saved minus SIM log bytes. Stop if it goes negative.

## Files

- `sim_evaluator.py` — deterministic evaluator + selector (stdlib only)
- `SIM_TEMPLATE.md` — copy this as your per-topic SIM log
- `example/` — a runnable toy example (one passing, one failing candidate)

## Run the example

```bash
python3 sim_evaluator.py --original example/original.md \
  --candidates example/candidates --facts example/facts.json
```
