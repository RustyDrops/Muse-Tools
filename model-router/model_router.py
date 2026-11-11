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


def _matches(match, t, complexity, low_failed):
    """True when every condition in a rule's `match` block holds.

    Supported conditions: `task_type` (exact), `task_type_in` (any of),
    `complexity` (exact), `low_failed` (boolean). Rule order in
    router_rules.json is the precedence order — the first matching
    rule wins, so the JSON is the single source of routing decisions.
    """
    for key, want in match.items():
        if key == "task_type":
            if t != want:
                return False
        elif key == "task_type_in":
            if t not in want:
                return False
        elif key == "complexity":
            if complexity != want:
                return False
        elif key == "low_failed":
            if bool(low_failed) != bool(want):
                return False
        else:
            return False
    return True


def pick(task_type, size, complexity, low_failed=False):
    """Execute router_rules.json: first matching rule, else defaults."""
    rules = load_rules()
    t = (task_type or "").lower()
    for rule in rules.get("rules", []):
        if _matches(rule.get("match", {}), t, complexity, low_failed):
            return {"model": rule["model"], "effort": rule["effort"],
                    "reason": rule["reason"],
                    "est_cost_usd": est_cost(rules, rule["model"],
                                             rule["effort"])}
    d = rules["defaults"]
    return {"model": d["model"], "effort": d["effort"],
            "reason": d["reason"],
            "est_cost_usd": est_cost(rules, d["model"], d["effort"])}


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
