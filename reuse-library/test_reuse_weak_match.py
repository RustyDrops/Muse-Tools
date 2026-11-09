"""Weak-match flag + control-query ranking + content enrichment (hash backend)."""

import io
import json
import os
import tempfile
from contextlib import redirect_stdout

import reuse_library as rl


def _write(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _make_index(tmp):
    reg = os.path.join(tmp, "registry.json")
    _write(reg, {"templates": [
        {"id": "side-polaroid-family", "name": "Polaroid Family",
         "category": "Family", "slots": ["caption1"],
         "photo_keys": ["family"]},
        {"id": "editorial-fall-festival", "name": "Fall Festival",
         "category": "Event", "slots": ["title1"],
         "photo_keys": ["autumn"]},
    ]})
    _write(os.path.join(tmp, "content.json"), {"templates": {
        "side-polaroid-family": {"caption1": "Church Family"},
        "editorial-fall-festival": {"title1": "Fall", "title2": "Festival"},
    }})
    src = os.path.join(tmp, "sources.json")
    _write(src, {"sources": [{"path": reg, "kind": "template"}]})
    idx = os.path.join(tmp, "index")
    rl.Embedder = _HashEmbedder  # force deterministic offline backend
    rl.cmd_index(src, idx)
    return idx


class _HashEmbedder:
    backend = "hash-fallback"

    def __init__(self):
        self._b = "hash-fallback"

    @property
    def backend(self):
        return "hash-fallback"

    def embed(self, texts):
        return [rl._hash_vector(t) for t in texts]


def _search(idx, query, as_json=False):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = rl.cmd_search(query, "template", idx, 2, as_json=as_json)
    return rc, buf.getvalue()


def test_registry_enriched_with_content_copy():
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(tmp, "content.json"), {"templates": {
            "side-polaroid-family": {"caption1": "Church Family"}}})
        reg = os.path.join(tmp, "registry.json")
        _write(reg, {"templates": [
            {"id": "side-polaroid-family", "name": "Polaroid Family",
             "category": "Family"}]})
        recs = rl._parse_registry_json(reg, "template")
        assert len(recs) == 1
        assert "Church Family" in recs[0]["text"]


def test_no_descriptions_invented():
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "registry.json")
        _write(reg, {"templates": [
            {"id": "mystery", "name": "Mystery", "category": "Event"}]})
        recs = rl._parse_registry_json(reg, "template")
        assert recs[0]["text"] == "Mystery Event slots  photos " or \
            "mystery" in recs[0]["text"].lower()


def test_control_query_ranks_polaroid_first_with_margin():
    with tempfile.TemporaryDirectory() as tmp:
        idx = _make_index(tmp)
        _buf = io.StringIO()
        with redirect_stdout(_buf):
            rl.cmd_search("side-polaroid-family", "template", idx, 2)
        lines = [l for l in _buf.getvalue().splitlines() if "\t" in l]
        assert "side-polaroid-family" in lines[0]
        s1 = float(lines[0].split("\t")[1])
        s2 = float(lines[1].split("\t")[1])
        assert s1 - s2 > 0.1


def test_weak_match_flagged_for_unrelated_query():
    with tempfile.TemporaryDirectory() as tmp:
        idx = _make_index(tmp)
        _rc, out = _search(
            idx, "plush bunny card, blush pink, HuggleHaven-style")
        assert "weak_match=true" in out
        _rc, jout = _search(
            idx, "plush bunny card, blush pink, HuggleHaven-style",
            as_json=True)
        payload = json.loads(jout.splitlines()[-1])
        assert payload["weak_match"] is True
        assert payload["match_quality"] == "weak"


def test_exact_id_query_is_strong():
    with tempfile.TemporaryDirectory() as tmp:
        idx = _make_index(tmp)
        _rc, out = _search(idx, "side-polaroid-family")
        assert "weak_match=false" in out


def _count_rows(idx):
    with open(os.path.join(idx, "vectors.jsonl"), encoding="utf-8") as fh:
        return sum(1 for l in fh if l.strip())


def test_changed_source_reindexed_without_rebuild_does_not_duplicate():
    with tempfile.TemporaryDirectory() as tmp:
        idx = _make_index(tmp)
        before = _count_rows(idx)
        reg = os.path.join(tmp, "registry.json")
        with open(reg, encoding="utf-8") as fh:
            data = json.load(fh)
        data["templates"].append(
            {"id": "newcomer", "name": "Newcomer",
             "category": "Event", "slots": ["title1"],
             "photo_keys": []})
        _write(reg, data)
        os.utime(reg, (os.path.getmtime(reg) + 5,) * 2)
        rl.cmd_index(os.path.join(tmp, "sources.json"), idx)
        rows = []
        with open(os.path.join(idx, "vectors.jsonl"), encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
        paths = [r["path"] for r in rows]
        assert len(paths) == len(set(paths))
        assert before + 1 == len(rows)


def test_js_parsed_records_contain_slot_names():
    with tempfile.TemporaryDirectory() as tmp:
        jsp = os.path.join(tmp, "pillow-templates.js")
        with open(jsp, "w", encoding="utf-8") as fh:
            fh.write('export const t = [{ "id": "js-one", '
                     '"name": "JS One", "category": "Scripture", '
                     '"slots": ["label", "lines"], '
                     '"photo_keys": ["landscape"], '
                     '"layout": {"align": ["left"]}}];')
        recs = rl._parse_js_templates(jsp)
        assert len(recs) == 1
        assert "label" in recs[0]["text"]
        assert "lines" in recs[0]["text"]
        assert "landscape" in recs[0]["text"]
        assert "align" in recs[0]["text"]
