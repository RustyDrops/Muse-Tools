# Log — <filename> (append-only, Rigario method + SIM gate)
Baseline note: <UNVERIFIED backfill summary, or "live-verified baseline">.
state_hash: <sha256 of the file at baseline>
bytes: <size>

## Facts (atomic, log-derived — the gate checks against THIS, never the current file alone)
```json
{"facts": {"<fact name>": "<regex>", "...": "..."}, "hard": ["<fact name>"], "superseded": []}
```

## Entries (append-only)
- <YYYY-MM-DD> | BASELINE | <how the baseline was set + coverage limits> | state_hash: <sha256>
- <YYYY-MM-DD> | CORRECTION | <what changed + why + what it supersedes> | state_hash: <sha256 after the change>
- <YYYY-MM-DD> | OPS | <shrink run: in->out bytes, gate result> | state_hash: <sha256 after the change>
