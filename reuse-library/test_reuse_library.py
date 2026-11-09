"""Fixture test: known query returns the known path first (paths only)."""

import json
import os
import subprocess
import sys
import tempfile

LIB = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(LIB, "reuse_library.py")


def _run(*args):
    return subprocess.run([sys.executable, PY] + list(args),
                          capture_output=True, text=True, cwd=LIB)


def test_known_query_returns_known_path_first():
    with tempfile.TemporaryDirectory() as td:
        corpus = os.path.join(td, "corpus")
        os.makedirs(corpus)
        reg = {"templates": [
            {"id": "side-polaroid-family", "name": "Polaroid Church Family",
             "category": "Photo", "slots": ["caption1", "caption2"],
             "photo_keys": ["photo1", "photo2"]},
            {"id": "clean-bible-verse-image", "name": "Bible Verse with Image",
             "category": "Scripture", "slots": ["label", "lines"],
             "photo_keys": ["landscape"]},
        ]}
        reg_path = os.path.join(corpus, "registry.json")
        with open(reg_path, "w", encoding="utf-8") as fh:
            json.dump(reg, fh)
        src = os.path.join(td, "sources.json")
        with open(src, "w", encoding="utf-8") as fh:
            json.dump({"gaps": [], "sources": [
                {"kind": "template", "path": reg_path, "verified": True}]}, fh)
        idx = os.path.join(td, "index")
        r = _run("index", "--sources", src, "--index-dir", idx)
        assert r.returncode == 0, r.stderr
        rows = open(os.path.join(idx, "vectors.jsonl"), encoding="utf-8").read()
        assert "side-polaroid-family" in rows
        r = _run("search", "--query", "polaroid family photo card",
                 "--kind", "template", "--index-dir", idx, "--top", "3")
        assert r.returncode == 0, r.stderr
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        assert lines, "search returned no hits"
        assert "side-polaroid-family" in lines[0], lines[0]
        for line in lines:  # labels only: no file contents in stdout
            assert len(line) < 500, line


def test_missing_source_recorded_as_gap():
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "sources.json")
        with open(src, "w", encoding="utf-8") as fh:
            json.dump({"gaps": [], "sources": [
                {"kind": "code", "path": os.path.join(td, "nope.py"),
                 "verified": False}]}, fh)
        idx = os.path.join(td, "index")
        r = _run("index", "--sources", src, "--index-dir", idx)
        assert r.returncode == 0, r.stderr
        assert "missing" in r.stdout
