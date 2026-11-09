"""Chunk B eval harness: runs eval_queries.json, prints PASS/FAIL per line.

Kind-taxonomy rules (Phase 3 Item 1): each positive declares its `kind`
and is searched in its own kind pool; each negative runs against EVERY
kind present in the index and must be `weak_match` in all of them (a
negative that is strong in any kind is a FAIL -- the invoice->overlay
failure mode). Per-kind margin = min positive top score in that kind
minus max negative top score in that kind; every kind with positives
must clear MARGIN_GOAL.

Usage:
  ~/workspace/tools-venv/bin/python reuse-library/run_eval.py [--grid]

--grid tries KEYWORD_WEIGHT over {0.05, 0.1, 0.2, 0.35, 0.5} and reports
the smallest weight meeting the margin test ( positives rank expected id
or acceptable set in-kind, every per-kind margin >= 0.20, negatives weak
in every kind ).
Exit 0 iff every line PASSes and every per-kind margin >= 0.20.
"""

import io
import json
import os
import sys
from contextlib import redirect_stdout

LIB = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, LIB)
import reuse_library as rl  # noqa: E402

EVAL_PATH = os.path.join(LIB, "eval_queries.json")
INDEX_DIR = os.path.join(LIB, "index")
GRID = (0.05, 0.1, 0.2, 0.35, 0.5)
MARGIN_GOAL = 0.20


def _search(query, kind="template", top=5):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = rl.cmd_search(query, kind, INDEX_DIR, top, as_json=True)
    lines = [l for l in buf.getvalue().splitlines() if l.strip()]
    hits = [l for l in lines if "\t" in l]
    payload = json.loads(lines[-1])
    return rc, hits, payload


def _top_id(hits):
    return hits[0].split("\t")[0].split("#")[-1] if hits else None


def _scores(hits):
    return [float(h.split("\t")[1]) for h in hits]


def _index_kinds():
    """Every kind present in the built index (negatives run in each)."""
    vec_path = os.path.join(INDEX_DIR, "vectors.jsonl")
    kinds = set()
    try:
        with open(vec_path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    kinds.add(json.loads(line).get("kind", "template"))
    except Exception:
        pass
    return sorted(kinds)


def run_once():
    with open(EVAL_PATH, encoding="utf-8") as fh:
        spec = json.load(fh)
    manifest = rl.load_manifest(INDEX_DIR)
    backend = manifest.get("backend")
    assert backend == "fastembed", (
        "eval requires FastEmbed backend, manifest says %r" % (backend,))
    results = []
    for case in spec["positives"]:
        kind = case.get("kind", "template")
        _rc, hits, payload = _search(case["query"], kind=kind)
        s = _scores(hits)
        top = _top_id(hits)
        ok = top in case["acceptable"]
        results.append({"id": case["id"], "kind": "positive",
                        "pool": kind, "top": top,
                        "top_score": s[0] if s else 0.0,
                        "margin": (s[0] - s[1]) if len(s) > 1 else 0.0,
                        "pass": ok and not payload["weak_match"],
                        "note": "" if ok else
                        "expected one of %s" % (case["acceptable"],)})
    neg_kinds = _index_kinds() or ["template"]
    for case in spec["negatives"]:
        for kind in neg_kinds:
            _rc, hits, payload = _search(case["query"], kind=kind)
            s = _scores(hits)
            rid = "%s@%s" % (case["id"], kind)
            results.append({"id": rid, "kind": "negative",
                            "pool": kind, "top": _top_id(hits),
                            "top_score": s[0] if s else 0.0,
                            "margin": (s[0] - s[1]) if len(s) > 1 else 0.0,
                            "pass": bool(payload["weak_match"]),
                            "note": "" if payload["weak_match"] else
                            "expected weak_match=true in kind %s" % kind})
    margins = {}
    for kind in sorted({c.get("kind", "template")
                        for c in spec["positives"]}):
        pos = [r["top_score"] for r in results
               if r["kind"] == "positive" and r["pool"] == kind]
        neg = [r["top_score"] for r in results
               if r["kind"] == "negative" and r["pool"] == kind]
        margins[kind] = min(pos) - max(neg) if pos and neg else 0.0
    overall = min(margins.values()) if margins else 0.0
    return results, margins, overall


def main(argv):
    grid = "--grid" in argv[1:]
    weights = GRID if grid else (rl.KEYWORD_WEIGHT,)
    best = None
    for w in weights:
        rl.KEYWORD_WEIGHT = w
        results, margins, overall = run_once()
        all_pass = all(r["pass"] for r in results)
        margins_ok = all(m >= MARGIN_GOAL for m in margins.values())
        for r in results:
            print("%s\t%s\t%s\t%.4f\t%.4f\t%s\t%s" % (
                r["id"], r["kind"], r["top"], r["top_score"],
                r["margin"], "PASS" if r["pass"] else "FAIL", r["note"]))
        for kind in sorted(margins):
            print("margin[%s]=%.4f" % (kind, margins[kind]))
        print("weight=%.2f all_pass=%s margins_ok=%s overall=%.4f" % (
            w, all_pass, margins_ok, overall))
        if grid and all_pass and margins_ok and best is None:
            best = (w, overall)
    if grid:
        print("GRID_BEST=%s" % (repr(best),))
        return 0 if best is not None else 1
    ok = (all(r["pass"] for r in results)
          and all(m >= MARGIN_GOAL for m in margins.values()))
    print("SUMMARY all_pass=%s margins=%s overall=%.4f goal=%.2f" % (
        all(r["pass"] for r in results),
        ",".join("%s:%.4f" % kv for kv in sorted(margins.items())),
        overall, MARGIN_GOAL))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
