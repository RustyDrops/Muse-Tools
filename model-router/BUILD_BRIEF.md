# Model router build brief

## Goal
Tiny deterministic router CLI that picks the cheapest fitting model and logs the pick. No network, no model call from the router itself. Models are generic slots — light, standard, planner, worker — so anyone can map them to their own models.

## Files to create (all under `model-router/`)
- `model_router.py` — CLI: `route --task-type <type> --size <s|m|l> --complexity <routine|hard> [--low-failed] [--dry-run]`. Prints one JSON pick `{model, effort, reason, est_cost_usd}` and appends the same record to the log.
- `router_rules.json` — decision table as data (not code): routine + s/m -> light/low; routine + low-failed flag or complexity hard -> standard/medium; planning -> planner; grilling/implementing/file-tool/final-QA -> worker; trivial check (lint, test run, file existence, format check) -> deterministic $0 script, never planner. Rates in the table are placeholders (0.0) — fill in your own models' rates.
- `router_log.jsonl` — append-only pick log (model, effort, reason, est. cost before; actual cost after, filled later from your cost tracker).
- `test_model_router.py` — table-driven tests over the rule cases above.

## Check (must PASS before returning)
- `python3 -m pytest model-router/test_model_router.py -q` -> PASS, including: trivial check never routes to planner; the table contains no vendor model names.
- `python3 model-router/model_router.py route --task-type draft --size s --complexity routine --dry-run` -> JSON with `"model": "light", "effort": "low"` and a `router_log.jsonl` line written.

## Out of scope
Actually calling any model from the router; auto-escalation loops; cost reconciliation against a specific tracker (the log is plain JSONL — any tracker can read it).

## Rules
- Cost-before is an estimate — label it `est_cost_usd`, never present as measured.
- Never paste large files into chat; outputs live on disk, referenced by path.
- Stop if a check fails twice on the same error — record the gap and return, do not loop.
