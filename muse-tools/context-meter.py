#!/usr/bin/env python3
"""Context Meter — measured sizes only, no file contents printed.

Usage: python3 context-meter.py
Prints bytes, approx. tokens (bytes // 4, an estimate, labelled as such),
and line counts for the files that fill Muse's prompt context.
"""
import os
from pathlib import Path

HOME = Path.home()
TARGETS = [
    ("MEMORY.md (lean core)", HOME / "MEMORY.md"),
    ("memory/topics", HOME / "memory" / "topics"),
    ("memory/people", HOME / "memory" / "people"),
    ("memory/groups", HOME / "memory" / "groups"),
    ("workspace/goals (.md notes only)", HOME / "workspace" / "goals"),
]

def measure(path):
    if path.is_file():
        data = path.read_bytes()
        return len(data), data.count(b"\n") + 1
    if path.is_dir():
        total, lines, files = 0, 0, 0
        goals_only_md = path.name == "goals"
        for root, dirs, names in os.walk(path):
            # Runtime-managed indexes are not user-authored context.
            if "bank" in root or "index" in root:
                continue
            for name in names:
                # Goals hold large media/decks that are NOT injected into
                # the prompt — only their .md notes count here.
                if goals_only_md and not name.endswith(".md"):
                    continue
                f = Path(root) / name
                try:
                    data = f.read_bytes()
                except OSError:
                    continue
                total += len(data)
                lines += data.count(b"\n") + 1
                files += 1
        return total, lines, files
    return 0, 0, 0

def main():
    rows = []
    for label, path in TARGETS:
        size, lines, *rest = measure(path) if path.exists() else (0, 0, 0)
        extra = f", {rest[0]} files" if rest else ""
        rows.append((size, label, lines, extra))
    rows.sort(reverse=True)
    print("Context Meter — measured, not estimated (tokens = bytes // 4, approx.)")
    for size, label, lines, extra in rows:
        print(f"{label}: {size:,} bytes (~{size // 4:,} tokens), {lines:,} lines{extra}")
    total = sum(r[0] for r in rows)
    print(f"TOTAL listed: {total:,} bytes (~{total // 4:,} tokens)")
    print("Note: this measures files on disk. Live chat history is separate and not measured here.")

if __name__ == "__main__":
    main()
