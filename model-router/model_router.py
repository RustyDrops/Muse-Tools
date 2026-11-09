#!/usr/bin/env python3
"""Deterministic model router CLI. No network, no model calls."""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(HERE, "router_rules.json")
LOG_PATH = os.path.join(HERE, "router_log.jsonl")

DENY_REASONS = {"terra": "backup-only", "gemini": "retired-reliability"}


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

    def denied(name):
        return {
            "model": name,
            "effort": "denied",
            "reason": DENY_REASONS[name],
            "est_cost_usd": 0.0,
        }

    if t in ("terra",):
        return denied("terra")
    if t in ("gemini", "gemini-cli"):
        return denied("gemini")

    trivial = {"trivial-check", "lint", "test-run", "file-exists", "format-check",
               "trivial", "lint-check", "test", "format"}
    if t in trivial:
        return {"model": "script", "effort": "none",
                "reason": "trivial check — deterministic $0 script",
                "est_cost_usd": 0.0}
    if t == "planning":
        return {"model": "wonder-muse-code", "effort": "planning",
                "reason": "planning — Wonder (Muse Code, planning only)",
                "est_cost_usd": est_cost(rules, "wonder-muse-code", "planning")}
    if t in ("grilling", "implementing", "file-tool", "final-qa"):
        effort = "high" if t == "final-qa" else "medium"
        reason = {"grilling": "grilling — Spark in Muse Code",
                  "implementing": "implementing — Spark in Muse Code",
                  "file-tool": "file tool work — Spark in Muse Code",
                  "final-qa": "final QA — Spark in Muse Code"}[t]
        return {"model": "spark-muse-code", "effort": effort, "reason": reason,
                "est_cost_usd": est_cost(rules, "spark-muse-code", effort)}
    if complexity == "hard" or low_failed:
        r = "hard complexity — Luna medium" if complexity == "hard" else "low failed retry — Luna medium"
        return {"model": "gpt-6-luna", "effort": "medium", "reason": r,
                "est_cost_usd": est_cost(rules, "gpt-6-luna", "medium")}
    return {"model": "gpt-6-luna", "effort": "low",
            "reason": "routine small draft — Luna low",
            "est_cost_usd": est_cost(rules, "gpt-6-luna", "low")}


def cmd_route(args):
    record = pick(args.task_type, args.size, args.complexity, args.low_failed)
    record["actual_cost_usd"] = None
    record["logged_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    out = {k: record[k] for k in ("model", "effort", "reason", "est_cost_usd")}
    print(json.dumps(out))


def _gap(name, detail):
    print(json.dumps({"gap": name, "detail": detail}), file=sys.stderr)
    return 2


def cmd_reconcile(args):
    try:
        with open(args.tracker_summary) as f:
            summary = json.load(f)
    except FileNotFoundError as e:
        return _gap("tracker-summary-missing", str(e))
    except json.JSONDecodeError as e:
        return _gap("tracker-format-drift", f"summary is not valid JSON: {e}")
    except OSError as e:
        return _gap("tracker-summary-unreadable", str(e))
    try:
        section = summary["openai"]
        total = section["cost_usd"]
        calls = section["calls"]
    except (KeyError, TypeError) as e:
        return _gap("tracker-format-drift",
                     f"summary lacks openai.calls/cost_usd: {e}")
    if isinstance(total, bool) or not isinstance(total, (int, float)):
        return _gap("tracker-format-drift",
                     "summary openai.cost_usd is not a number")
    if isinstance(calls, bool) or not isinstance(calls, int):
        return _gap("tracker-format-drift",
                     "summary openai.calls is not an integer")
    try:
        with open(args.log) as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = []
    except OSError as e:
        return _gap("router-log-unreadable", str(e))
    rows = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            return _gap("router-log-drift",
                         f"log line {i + 1} is not valid JSON: {e}")
        if not isinstance(row, dict):
            return _gap("router-log-drift",
                         f"log line {i + 1} is not an object")
        rows.append(row)
    luna = [r for r in rows if r.get("model") == "gpt-6-luna"]
    filled = [r for r in luna if isinstance(r.get("actual_cost_usd"),
                                           (int, float))
              and not isinstance(r.get("actual_cost_usd"), bool)]
    pending = [r for r in luna if r.get("actual_cost_usd") is None]
    if not pending:
        print(json.dumps({"reconciled": 0, "actual_cost_usd": None}))
        return 0
    if calls != len(luna):
        return _gap("tracker-attribution-ambiguous",
                     f"summary openai.calls={calls} != {len(luna)} "
                     "Luna rows in router log; refusing to guess attribution")
    if len(pending) != 1:
        return _gap("tracker-attribution-ambiguous",
                     f"{len(pending)} unreconciled Luna rows; reconcile "
                     "fills exactly one row per run, never a guessed split")
    actual = round(total - sum(r["actual_cost_usd"] for r in filled), 6)
    if actual < 0:
        return _gap("tracker-format-drift",
                     "summary total is below already-reconciled actuals")
    for r in rows:
        if r is pending[0]:
            r["actual_cost_usd"] = actual
    tmp = args.log + ".tmp"
    try:
        with open(tmp, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        os.replace(tmp, args.log)
    except OSError as e:
        return _gap("router-log-unwritable", str(e))
    print(json.dumps({"reconciled": 1, "actual_cost_usd": actual}))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("route")
    r.add_argument("--task-type", required=True)
    r.add_argument("--size", required=True, choices=["s", "m", "l"])
    r.add_argument("--complexity", required=True, choices=["routine", "hard"])
    r.add_argument("--low-failed", action="store_true")
    r.add_argument("--dry-run", action="store_true")
    c = sub.add_parser("reconcile")
    c.add_argument("--tracker-summary", required=True,
                   help="path to a tracker summary JSON file "
                        "(tracker stays the single cost source; read-only)")
    c.add_argument("--log", default=LOG_PATH,
                   help="router log to reconcile (default: router_log.jsonl)")
    args = p.parse_args(argv)
    if args.cmd == "route":
        cmd_route(args)
    elif args.cmd == "reconcile":
        return cmd_reconcile(args)


if __name__ == "__main__":
    sys.exit(main())
