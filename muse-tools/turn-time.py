#!/usr/bin/env python3
"""Turn-time log — manual, deterministic, no LLM estimates.
Usage:
  python3 turn-time.py log --chat <id> --context <tokens> [--duration <sec>] [--tools <n>] [--note <text>]
  python3 turn-time.py summary
File: ~/workspace/muse-tools/turn-times.jsonl, one JSON object per turn.
Fields: ts (UTC, when logged, approx reply time), chat, context_tokens,
duration_sec (approx, user-message timestamp to reply time, from chat
timestamps — NOT a runtime-measured turn timer), tools (tool calls in turn),
note (short, no prompts, no private content).
Limitation, stated honestly: Muse gives no turn-start hook I can rely on,
so this log is maintained by Muse at the end of substantive turns, not
automatically on every short reply. Missing a short reply is expected;
the log is for work turns and comparisons, not a complete audit.
"""
import argparse, json, sys
from pathlib import Path
LOG = Path.home() / "workspace/muse-tools/turn-times.jsonl"
def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("log"); l.add_argument("--chat", required=True); l.add_argument("--context", type=int, required=True)
    l.add_argument("--duration", type=float, default=None); l.add_argument("--tools", type=int, default=None); l.add_argument("--note", default="")
    sub.add_parser("summary")
    a = ap.parse_args()
    if a.cmd == "log":
        from datetime import datetime, timezone
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "chat": a.chat, "context_tokens": a.context,
               "duration_sec": a.duration, "tools": a.tools, "note": a.note}
        with open(LOG, "a", encoding="utf-8") as f: f.write(json.dumps(rec) + "\n")
        print(json.dumps(rec))
    else:
        rows = []
        if LOG.exists():
            for line in LOG.read_text(encoding="utf-8").splitlines():
                try: rows.append(json.loads(line))
                except Exception: pass
        ds = [r["duration_sec"] for r in rows if r.get("duration_sec") is not None]
        cs = [r["context_tokens"] for r in rows if r.get("context_tokens")]
        print(f"entries: {len(rows)}")
        if ds: print(f"duration_sec: count {len(ds)}, avg {sum(ds)/len(ds):.1f}, min {min(ds):.1f}, max {max(ds):.1f}")
        if cs: print(f"context_tokens: avg {sum(cs)/len(cs):,.0f}, min {min(cs):,}, max {max(cs):,}")
        for r in rows:
            ctx = f"{r['context_tokens']:,}" if r.get('context_tokens') else "-"
            print(f"- {r['ts'][:19]} {r['chat']} ctx={ctx} dur={r.get('duration_sec')} tools={r.get('tools')} {r.get('note','')}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
