# Step 0 — Model router build brief (Spark in Muse Code, NOT Wonder)

Source plan: `~/workspace/efficiency-tools-2026-11-07/PLAN.md`, Step 0. Build only this step. No other tool, no installs, no API calls, no generative imagery.

## Goal
Tiny deterministic router CLI that picks the cheapest fitting model and logs the pick. No network, no model call from the router itself.

## Files to create (all under `~/workspace/efficiency-tools-2026-11-07/model-router/`)
- `model_router.py` — CLI: `route --task-type <type> --size <s|m|l> --complexity <routine|hard> [--low-failed] [--dry-run]`. Prints one JSON pick `{model, effort, reason, est_cost_usd}` and appends the same record to the log.
- `router_rules.json` — decision table as data (not code): routine + s/m -> Luna low; routine + low-failed flag or complexity hard -> Luna medium; planning -> Wonder (Muse Code, planning only); grilling/implementing/file-tool/final-QA -> Spark in Muse Code; trivial check (lint, test run, file existence, format check) -> deterministic $0 script, never Wonder; Terra and Gemini absent from the table (hard-coded deny with reason `backup-only` / `retired-reliability` if ever requested).
- `router_log.jsonl` — append-only pick log (model, effort, reason, est. cost before; actual cost after, filled later from tracker / Muse Code usage log).
- `test_model_router.py` — table-driven tests over the rule cases above.

## Reason strings
Leave `reason` as a short placeholder string per rule for now (e.g. "routine small draft — Luna low"). A separate Luna low chunk will draft human-readable reason strings later. Do NOT call Luna in this build.

## Reuse untouched
`~/workspace/ai-cost-tracker/tracker.py` + `usage.jsonl` (cost source), `~/workspace/muse-tools/cost-ledger.py` pattern, `~/workspace/custom-connectors/custom.openai/bin/luna_responses_delegate.py` CLI/effort names, `~/workspace/custom-connectors/custom.muse-code/bin/muse_code.py` effort guidance, `~/workspace/efficiency-tools-2026-11-07/USAGE_TRACKING.md` reporting format.

## Check (must PASS before returning)
- `python3 -m pytest model-router/test_model_router.py -q` -> PASS, including: trivial check never routes to Wonder; default table contains no Terra/Gemini pick.
- `python3 model-router/model_router.py route --task-type draft --size s --complexity routine --dry-run` -> JSON with `"model": "gpt-6-luna", "effort": "low"` and a `router_log.jsonl` line written.

## Out of scope
Actually calling any model from the router; auto-escalation loops; any Terra/Gemini route.

## Rules
- Cost-before is an estimate — label it `est_cost_usd`, never present as measured.
- Never paste large files into chat; outputs live on disk, referenced by path.
- Stop if a check fails twice on the same error — record the gap and return, do not loop.
