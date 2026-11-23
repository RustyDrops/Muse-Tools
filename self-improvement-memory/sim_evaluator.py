#!/usr/bin/env python3
"""SIM evaluator + selector (stdlib only).

Checks candidate rewrites of a memory file against a deterministic fact
checklist, applies a hard gate (100% retention, and no hard fact missing),
then selects the passing candidate with the largest size saving.

facts.json format:
  {"facts": {"fact name": "regex", ...}, "hard": ["fact name", ...]}

A candidate named X with a sibling X-archive.md has the archive's bytes
counted in its total (splitting is scored on total system size), while its
fact score is measured on the main file alone — what a single load sees.

Usage:
  python3 sim_evaluator.py --original FILE --candidates DIR --facts facts.json
"""
import argparse, json, re, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--original", required=True)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--facts", required=True)
    args = ap.parse_args()

    orig = Path(args.original).read_bytes()
    spec = json.loads(Path(args.facts).read_text())
    facts, hard = spec["facts"], set(spec.get("hard", []))

    results = []
    for p in sorted(Path(args.candidates).glob("*.md")):
        if p.stem.endswith("-archive"):
            continue
        text = p.read_text()
        arch = p.with_name(p.stem + "-archive.md")
        total = len(text.encode()) + (len(arch.read_bytes()) if arch.exists() else 0)
        found = {k: bool(re.search(v, text, re.I)) for k, v in facts.items()}
        missing = [k for k, v in found.items() if not v]
        retention = round(100 * (len(facts) - len(missing)) / len(facts), 1) if facts else 100.0
        # Hard gate as tested: any hard fact missing, or retention below 100%, fails.
        gate = "FAIL" if (hard & set(missing)) or retention < 100 else "PASS"
        results.append({
            "candidate": p.stem, "bytes": total,
            "size_saving_pct": round(100 * (1 - total / len(orig)), 1),
            "fact_retention_pct": retention, "missing_facts": missing,
            "hard_gate": gate,
        })

    passed = [r for r in results if r["hard_gate"] == "PASS"]
    winner = max(passed, key=lambda r: r["size_saving_pct"]) if passed else None
    out = {"original_bytes": len(orig), "fact_count": len(facts),
           "results": results, "winner": winner["candidate"] if winner else None}
    print(json.dumps(out, indent=2))
    return 0 if winner else 1

if __name__ == "__main__":
    sys.exit(main())
