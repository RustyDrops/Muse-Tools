#!/usr/bin/env python3
"""Deterministic model router CLI. No network, no model calls.

Models are generic slots — light, standard, planner, worker — mapped to
your own models in router_rules.json. Fill in your own per-model rates
there; 0.0 means unpriced.
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(HERE, "router_rules.json")
LOG_PATH = os.path.join(HERE, "router_log.jsonl")


def load_rules():
    with open(RULES_PATH) as f:
        return json.load(f)


def est_cost(rules, model, effort):
    table = rules.get("est_cost_usd", {})
    if model == "script":
        return table.get("script", 0.0)
    return table.get(f"{model}-{effort}", table.get(model, 0.0))


def pick(task_type, size, complexity, low_failed=False):
    rules = load_rules()
    t = (task_type or "").lower()

    trivial = {"trivial-check", "lint", "test-run", "file-exists", "format-check",
               "trivial", "lint-check", "test", "format"}
    if t in trivial:
        return {"model": "script", "effort": "none",
                "reason": "trivial check — deterministic $0 script",
                "est_cost_usd": 0.0}
    if t == "planning":
        return {"model": "planner", "effort": "planning",
                "reason": "planning — strong planning model",
                "est_cost_usd": est_cost(rules, "planner", "planning")}
    if t in ("grilling", "implementing", "file-tool", "final-qa"):
        effort = "high" if t == "final-qa" else "medium"
        reason = {"grilling": "grilling — worker model",
                  "implementing": "implementing — worker model",
                  "file-tool": "file tool work — worker model",
                  "final-qa": "final QA — worker model"}[t]
        return {"model": "worker", "effort": effort, "reason": reason,
                "est_cost_usd": est_cost(rules, "worker", effort)}
    if complexity == "hard" or low_failed:
        r = ("hard complexity — standard model" if complexity == "hard"
             else "low failed retry — standard model")
        return {"model": "standard", "effort": "medium", "reason": r,
                "est_cost_usd": est_cost(rules, "standard", "medium")}
    return {"model": "light", "effort": "low",
            "reason": "routine small draft — light model",
            "est_cost_usd": est_cost(rules, "light", "low")}


def cmd_route(args):
    record = pick(args.task_type, args.size, args.complexity, args.low_failed)
    record["actual_cost_usd"] = None
    record["logged_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    out = {k: record[k] for k in ("model", "effort", "reason", "est_cost_usd")}
    print(json.dumps(out))


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("route")
    r.add_argument("--task-type", required=True)
    r.add_argument("--size", required=True, choices=["s", "m", "l"])
    r.add_argument("--complexity", required=True, choices=["routine", "hard"])
    r.add_argument("--low-failed", action="store_true")
    r.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if args.cmd == "route":
        cmd_route(args)


if __name__ == "__main__":
    sys.exit(main())
