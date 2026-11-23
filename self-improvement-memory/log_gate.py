#!/usr/bin/env python3
"""Append-only log gate (Rigario method + SIM gate), stdlib only.

Log format: a Markdown file whose header carries a ```json block:
  {"facts": {"name": "regex", ...}, "hard": ["name", ...],
   "superseded": ["name", ...]}
and state lines `state_hash: <sha256>` — the LAST one is the file state the
log believes is current.

Commands:
  check FILE LOG            fail-closed sync check: file hash must equal the
                            log's last state_hash. Exit 2 on mismatch.
  gate CANDIDATE FILE LOG   sync check first, then score CANDIDATE against
                            the log's non-superseded facts. Exit 0 PASS,
                            1 FAIL (facts lost), 2 out-of-sync.
  record FILE LOG TYPE NOTE append an entry with the file's current hash
                            (call AFTER an applied change). TYPE is a
                            semantic type (ADD/CORRECTION/REMOVE) or OPS
                            for a shrink run.
"""
import hashlib, json, re, sys
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_log(p):
    t = Path(p).read_text()
    m = re.search(r"```json\n(.*?)```", t, re.S)
    spec = json.loads(m.group(1)) if m else {"facts": {}, "hard": [], "superseded": []}
    hashes = re.findall(r"state_hash: ([0-9a-f]{64})", t)
    return t, spec, (hashes[-1] if hashes else None)

def check(file, log):
    _, _, last = load_log(log)
    cur = sha(file)
    if last is None: print("NO_BASELINE: log has no state_hash"); return 2
    if cur != last: print(f"OUT_OF_SYNC: file {cur[:12]} != logged {last[:12]} — shrink refused"); return 2
    print(f"IN_SYNC: {cur[:12]}"); return 0

def gate(candidate, file, log):
    rc = check(file, log)
    if rc: return rc
    _, spec, _ = load_log(log)
    text = Path(candidate).read_text()
    active = {k: v for k, v in spec["facts"].items() if k not in spec.get("superseded", [])}
    missing = [k for k, v in active.items() if not re.search(v, text, re.I)]
    hard_missing = [k for k in missing if k in spec.get("hard", [])]
    pct = round(100*(len(active)-len(missing))/len(active), 1) if active else 100.0
    verdict = "PASS" if not missing else "FAIL"
    print(json.dumps({"candidate": str(candidate), "active_facts": len(active),
                      "retention_pct": pct, "missing": missing,
                      "hard_missing": hard_missing, "gate": verdict}, indent=2))
    return 0 if verdict == "PASS" else 1

def record(file, log, typ, note):
    import datetime
    line = f"\n- {datetime.date.today().isoformat()} | {typ} | {note} | state_hash: {sha(file)}\n"
    with open(log, "a") as f: f.write(line)
    print("recorded:", line.strip()); return 0

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "check": sys.exit(check(a[1], a[2]))
    if a[0] == "gate": sys.exit(gate(a[1], a[2], a[3]))
    if a[0] == "record": sys.exit(record(a[1], a[2], a[3], a[4]))
    print(__doc__); sys.exit(2)
