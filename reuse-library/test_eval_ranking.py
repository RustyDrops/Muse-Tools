"""Chunk B ranking tests: bounded hybrid scoring on indexed text (hash backend)."""

import io
import json
import os
import tempfile
from contextlib import redirect_stdout

import reuse_library as rl


def _write(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


class _HashEmbedder:
    def __init__(self):
        self._b = "hash-fallback"

    @property
    def backend(self):
        return "hash-fallback"

    def embed(self, texts):
        return [rl._hash_vector(t) for t in texts]


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
    src = os.path.join(tmp, "sources.json")
    _write(src, {"sources": [{"path": reg, "kind": "template"}]})
    idx = os.path.join(tmp, "index")
    rl.Embedder = _HashEmbedder  # force deterministic offline backend
    rl.cmd_index(src, idx)
    return idx


def _search(idx, query, top=2, kind="template"):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = rl.cmd_search(query, kind, idx, top, as_json=True)
    lines = buf.getvalue().splitlines()
    payload = json.loads(lines[-1])
    return rc, [l for l in lines if "\t" in l], payload


def test_scores_bounded():
    with tempfile.TemporaryDirectory() as tmp:
        idx = _make_index(tmp)
        _rc, hits, _p = _search(idx, "side-polaroid-family")
        for h in hits:
            s = float(h.split("\t")[1])
            assert s <= 1.0 + rl.KEYWORD_WEIGHT + rl.EXACT_ID_BONUS


def test_keyword_overlap_uses_indexed_text_not_path():
    with tempfile.TemporaryDirectory() as tmp:
        idx = _make_index(tmp)
        _rc, hits, _p = _search(idx, "autumn harvest festival")
        assert "editorial-fall-festival" in hits[0]


def test_exact_id_bonus_capped_and_separate():
    assert rl.EXACT_ID_BONUS <= 0.15
    assert rl.KEYWORD_WEIGHT <= 0.5
    assert rl._id_tokens("x#side-polaroid-family") == {
        "side", "polaroid", "family"}
    assert rl._id_tokens("plain.py") == set()


def test_json_keeps_weak_match_fields():
    with tempfile.TemporaryDirectory() as tmp:
        idx = _make_index(tmp)
        _rc, _hits, payload = _search(idx, "polaroid family")
        assert "weak_match" in payload
        assert "match_quality" in payload
        assert payload["match_quality"] in ("strong", "weak")


def _make_mixed_index(tmp):
    """Fixture index with a template pool plus one element record whose
    text is template-like (shares the query's terms)."""
    reg = os.path.join(tmp, "registry.json")
    _write(reg, {"templates": [
        {"id": "side-polaroid-family", "name": "Polaroid Family",
         "category": "Family", "slots": ["caption1"],
         "photo_keys": ["family"]},
    ]})
    parts = os.path.join(tmp, "design-elements.js")
    with open(parts, "w", encoding="utf-8") as fh:
        fh.write("define('polaroid-frame', 'Polaroid Frame', 'frames', "
                 "'polaroid family photo mat window', 'showcase portrait');\n")
    src = os.path.join(tmp, "sources.json")
    _write(src, {"sources": [{"path": reg, "kind": "template"},
                             {"path": parts, "kind": "element"}]})
    idx = os.path.join(tmp, "index")
    rl.Embedder = _HashEmbedder  # force deterministic offline backend
    rl.cmd_index(src, idx)
    return idx


def test_kind_isolation_template_search_returns_no_element():
    with tempfile.TemporaryDirectory() as tmp:
        idx = _make_mixed_index(tmp)
        _rc, hits, _p = _search(idx, "polaroid family photo", kind="template")
        assert hits, "expected the template record to hit"
        assert all("#polaroid-frame" not in h for h in hits)


def test_part_positive_ranks_first_in_own_kind():
    with tempfile.TemporaryDirectory() as tmp:
        idx = _make_mixed_index(tmp)
        _rc, hits, payload = _search(idx, "polaroid family photo mat",
                                     kind="element")
        assert hits and "polaroid-frame" in hits[0]
        assert not payload["weak_match"]


def test_dedupe_canonical_registry_wins_over_js_mirror():
    gaps = []
    canon = {"path": "/x/template-registry/registry.json#t1", "kind": "template",
             "title": "T", "text": "t"}
    mirror = {"path": "/y/pillow-templates.js#t1", "kind": "template",
              "title": "T", "text": "t"}
    out = rl._dedupe_recs([mirror, canon], gaps)
    assert out[0]["path"] == canon["path"]
    assert any("pillow-templates.js#t1" in g for g in gaps)


def test_negative_is_weak_in_every_kind():
    with tempfile.TemporaryDirectory() as tmp:
        idx = _make_mixed_index(tmp)
        for kind in ("template", "element"):
            _rc, _hits, payload = _search(
                idx, "Kubernetes YAML deployment manifest", kind=kind)
            assert payload["weak_match"], "strong in kind %s" % kind
