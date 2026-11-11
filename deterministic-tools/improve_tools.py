#!/usr/bin/env python3
"""Improve-bits tools — the shadcn/improve mechanics, implemented as code.

stamp        Record the state a brief/plan was written against (per-file
             SHA-256 + size + mtime, plus git repo + HEAD SHA when the
             file lives in one) into a stamp JSON file.
drift        Re-check a stamp file: PASS when nothing changed, DRIFT
             (exit 1) with the changed paths and why.
branch-scope Scope for a branch audit: files changed since the
             merge-base with the base branch, plus direct
             importers/callers of each changed file (grep over tracked
             files). No findings, no judgment — just the scope.
rejected     Persistent considered-and-rejected log (JSONL store):
             add / list / check. `check` word-matches a proposed item
             against past rejections so they are not re-proposed.

Stdlib only. Every function returns (exit_code, payload_dict).
Exit codes: 0 pass/found, 1 fail/not-found/drift, 2 tool error.
"""

import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

MAX_PATHS = 100
MAX_CHANGED = 50
MAX_IMPORTERS_PER_FILE = 20
MAX_LIST = 20
MAX_MATCHES = 10
GENERIC_STEMS = {"__init__", "index", "main", "app", "utils", "common",
                 "helpers", "config", "constants", "types"}
DEFAULT_STORE = Path.home() / "workspace" / "handoffs" / "rejected.jsonl"


def _git(args, cwd):
    try:
        r = subprocess.run(["git", "-C", str(cwd)] + args,
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def _entry(path):
    p = Path(path).expanduser()
    if not p.is_file():
        return None, f"not a file: {path}"
    data = p.read_bytes()
    st = p.stat()
    ent = {
        "path": str(p.resolve()),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": st.st_size,
        "mtime": int(st.st_mtime),
        "git_repo": None,
        "git_sha": None,
    }
    repo = _git(["rev-parse", "--show-toplevel"], p.parent)
    if repo:
        ent["git_repo"] = repo
        ent["git_sha"] = _git(["rev-parse", "--short", "HEAD"], p.parent)
    return ent, None


def stamp(out_path, paths, force=False):
    if not paths:
        return 2, {"error": "usage: stamp <out.json> <path> [path...]"}
    if len(paths) > MAX_PATHS:
        return 2, {"error": f"stamp: cap is {MAX_PATHS} paths"}
    out = Path(out_path).expanduser()
    if out.exists() and not force:
        return 2, {"error": f"stamp: {out} exists — pass --force to replace"}
    entries = []
    for raw in paths:
        ent, err = _entry(raw)
        if err:
            return 2, {"error": err}
        entries.append(ent)
    doc = {"created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "entries": entries}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    repos = sorted({e["git_repo"] for e in entries if e["git_repo"]})
    return 0, {"stamp": str(out), "files": len(entries),
               "git_repos": repos}


def drift(stamp_path):
    sp = Path(stamp_path).expanduser()
    if not sp.is_file():
        return 2, {"error": f"drift: stamp file not found: {stamp_path}"}
    try:
        doc = json.loads(sp.read_text(encoding="utf-8"))
        entries = doc["entries"]
    except (ValueError, KeyError, TypeError):
        return 2, {"error": "drift: stamp file is not a valid stamp"}
    changed, unchanged = [], 0
    git_checked = {}
    for ent in entries:
        p = Path(ent["path"])
        if not p.is_file():
            changed.append({"path": ent["path"], "reason": "missing"})
            continue
        cur, err = _entry(p)
        if err:
            changed.append({"path": ent["path"], "reason": "unreadable"})
            continue
        reasons = []
        if cur["sha256"] != ent["sha256"]:
            reasons.append("content")
        if ent.get("git_sha") and cur["git_sha"] != ent["git_sha"]:
            reasons.append(f"HEAD {ent['git_sha']}->{cur['git_sha']}")
        if reasons:
            changed.append({"path": ent["path"],
                            "reason": ", ".join(reasons)})
        else:
            unchanged += 1
        repo = ent.get("git_repo")
        if repo and ent.get("git_sha") and repo not in git_checked:
            git_checked[repo] = _git(
                ["diff", "--name-only", f"{ent['git_sha']}..HEAD"],
                repo) or ""
    committed = {}
    for repo, names in git_checked.items():
        files = [n for n in names.splitlines() if n]
        if files:
            committed[repo] = files[:MAX_CHANGED]
    status = "drift" if changed else "clean"
    payload = {"status": status, "changed": changed[:MAX_CHANGED],
               "unchanged": unchanged}
    if committed:
        payload["committed_since_stamp"] = committed
    return (1 if changed else 0), payload


def branch_scope(repo_path, base=None):
    repo = Path(repo_path).expanduser()
    if not repo.is_dir():
        return 2, {"error": f"branch-scope: not a directory: {repo_path}"}
    if _git(["rev-parse", "--show-toplevel"], repo) is None:
        return 2, {"error": "branch-scope: not a git repository"}
    if base is None:
        for cand in ("origin/main", "origin/master", "main", "master"):
            if _git(["rev-parse", "--verify", cand], repo):
                base = cand
                break
    if base is None:
        return 2, {"error": "branch-scope: no base branch found "
                            "(tried origin/main, origin/master, main, "
                            "master) — pass --base REF"}
    mb = _git(["merge-base", base, "HEAD"], repo)
    if not mb:
        return 2, {"error": f"branch-scope: no merge-base with {base}"}
    head = _git(["rev-parse", "--short", "HEAD"], repo)
    if _git(["rev-parse", "HEAD"], repo) == mb:
        return 0, {"status": "no-commits-ahead", "base": base,
                   "merge_base": mb[:12], "head": head,
                   "changed_files": [], "importers": {}}
    names = _git(["diff", "--name-only", f"{mb}..HEAD"], repo) or ""
    changed_files = [n for n in names.splitlines() if n]
    tracked = _git(["ls-files"], repo) or ""
    tracked_files = [t for t in tracked.splitlines() if t]
    changed_set = set(changed_files)
    importers = {}
    for rel in changed_files:
        stem = Path(rel).stem
        if stem in GENERIC_STEMS or len(stem) < 3:
            continue
        hits = []
        pat = re.compile(re.escape(stem))
        for other in tracked_files:
            if other in changed_set or len(hits) >= MAX_IMPORTERS_PER_FILE:
                continue
            fp = repo / other
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if pat.search(text):
                hits.append(other)
        if hits:
            importers[rel] = hits
    return 0, {"status": "ok", "base": base, "merge_base": mb[:12],
               "head": head, "changed_files": changed_files,
               "importers": importers}


def _store_path(store):
    return Path(store).expanduser() if store else DEFAULT_STORE


def _load_store(store):
    sp = _store_path(store)
    if not sp.is_file():
        return []
    rows = []
    for line in sp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def rejected(op, item=None, reason=None, project=None, store=None):
    sp = _store_path(store)
    if op == "add":
        if not item or not reason:
            return 2, {"error": 'usage: rejected add "<item>" "<reason>" '
                                "[--project SLUG] [--store PATH]"}
        sp.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "project": project or "", "item": item, "reason": reason}
        with sp.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return 0, {"stored": str(sp), "project": row["project"],
                   "item": item}
    rows = _load_store(store)
    if project:
        rows = [r for r in rows if r.get("project") == project]
    if op == "list":
        return 0, {"count": len(rows), "entries": rows[-MAX_LIST:]}
    if op == "check":
        if not item:
            return 2, {"error": 'usage: rejected check "<text>" '
                                "[--project SLUG] [--store PATH]"}
        words = {w for w in re.findall(r"[a-z0-9]+", item.lower())
                 if len(w) >= 4}
        matches = []
        for r in rows:
            hay = f"{r.get('item', '')} {r.get('reason', '')}".lower()
            hay_words = {w for w in re.findall(r"[a-z0-9]+", hay)
                         if len(w) >= 4}
            shared = words & hay_words
            if len(shared) >= 2:
                matches.append({"item": r.get("item"),
                                "reason": r.get("reason"),
                                "project": r.get("project"),
                                "shared": sorted(shared)})
        matches = matches[:MAX_MATCHES]
        return (0 if matches else 1), {
            "previously_rejected": bool(matches), "matches": matches}
    return 2, {"error": f"rejected: unknown op: {op}"}
