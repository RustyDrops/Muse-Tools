#!/usr/bin/env python3
"""Delegate Cost Ledger — totals only from the existing tracker log.

Usage: python3 cost-ledger.py
Reads ~/workspace/ai-cost-tracker/usage.jsonl. Prints no prompts, keys,
or response text — only token counts, costs, and remaining credit.
OpenAI budget: $5.00 (user-stated 2026-10-26). Gemini free tier: $0.
"""
import json
from collections import defaultdict
from pathlib import Path

LOG = Path.home() / "workspace" / "ai-cost-tracker" / "usage.jsonl"
BUDGET = 5.00

def main():
    if not LOG.exists():
        print("No usage log found.")
        return
    rows = [json.loads(line) for line in LOG.read_text().splitlines() if line.strip()]
    by_provider = defaultdict(lambda: {"calls": 0, "cost": 0.0, "in": 0, "out": 0})
    for r in rows:
        p = by_provider[r.get("provider", "unknown")]
        p["calls"] += 1
        p["cost"] += float(r.get("cost_usd", 0) or 0)
        p["in"] += int(r.get("prompt_tokens", 0) or 0)
        p["out"] += int(r.get("completion_tokens", 0) or 0)
    print("Delegate Cost Ledger")
    for provider, p in sorted(by_provider.items()):
        print(f"{provider}: {p['calls']} calls, {p['in']:,} in / {p['out']:,} out tokens, ${p['cost']:.6f}")
    spent = by_provider.get("openai", {}).get("cost", 0.0)
    remaining = BUDGET - spent
    print(f"OpenAI: spent ${spent:.6f} of ${BUDGET:.2f}, remaining ${remaining:.6f}")
    if remaining < 1.00:
        print("WARNING: OpenAI credit under $1.00 — check before more image/text calls.")
    if rows:
        print(f"Last logged call: {rows[-1].get('ts')} — {rows[-1].get('provider')} / {rows[-1].get('model')} / {rows[-1].get('task')}")

if __name__ == "__main__":
    main()
