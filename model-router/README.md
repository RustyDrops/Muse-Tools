# Model router

Picks the cheapest model that can do each job well: the light one for routine checks, the stronger one only when the job is genuinely hard.

Models are generic slots — `light`, `standard`, `planner`, `worker` — plus `script` for trivial checks that need no model at all. Map them to your own models in `router_rules.json` and fill in your own rates there (the shipped rates are 0.0 placeholders).

## Use

```bash
python3 model_router.py route --task-type draft --size s --complexity routine
# {"model": "light", "effort": "low", "reason": "routine small draft — light model", "est_cost_usd": 0.0}
```

Every pick is appended to `router_log.jsonl` as one JSON line, with `actual_cost_usd` left null for your cost tracker to fill in later. The log is plain JSONL, so any tracker can read it — the router itself never calls a model and never phones home.
