#!/usr/bin/env python3
"""Handoff Summary Maker — start a fresh chat from a short summary file only.

Usage:
  python3 handoff.py new my-topic --title "My topic"
Creates ~/workspace/handoffs/<slug>.md with locked sections for Muse (or
the user) to fill. It never copies a full transcript, log, or file into the
handoff, and it refuses to overwrite an existing handoff without --force.
"""
import argparse
import sys
from pathlib import Path

OUTDIR = Path.home() / "workspace" / "handoffs"
TEMPLATE = """# Handoff: {title}

Slug: {slug}
Purpose: start a fresh side chat with this file only — no history re-read.

## Locked decisions
- (decision, date, source)

## Specs
- (spec, file path or rule)

## Open items
- (what is still undecided, who decides)

## Do NOT reopen
- (closed items, only if the user explicitly closed them)

## Source files (paths only, never pasted content)
- 
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["new"])
    ap.add_argument("slug")
    ap.add_argument("--title", required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if "/" in args.slug or "\\" in args.slug or args.slug in ("", ".", ".."):
        print("Invalid slug: use letters, numbers, and hyphens only.", file=sys.stderr)
        return 2
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = OUTDIR / f"{args.slug}.md"
    if out.exists() and not args.force:
        print(f"Refusing to overwrite existing {out} — use --force to replace it.")
        return 1
    out.write_text(TEMPLATE.format(title=args.title, slug=args.slug), encoding="utf-8")
    print(f"Created {out}")
    return 0

if __name__ == "__main__":
    main()
