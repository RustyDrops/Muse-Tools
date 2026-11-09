"""Local FastEmbed search over existing code/graphics/templates.

CLI:
  reuse_library.py index --sources reuse_sources.json [--index-dir index]
  reuse_library.py search --query "..." [--kind code|graphic|icon|template|treatment|element|brand]
                         [--index-dir index] [--top 5]

Indexing extracts short text (docstrings/headings/slot names/registry
metadata -- never whole-file dumps), embeds with FastEmbed
(BAAI/bge-small-en-v1.5, 384 dims), stores {path, kind, title, vector}
in a local JSONL/npz index. Search prints path + score + one-line label.
File contents stay on disk. Falls back to deterministic hash vectors when
FastEmbed is unavailable (offline/test), with a keyword-overlap boost so
exact-term queries still rank first.
"""

import argparse
import ast
import glob
import hashlib
import json
import os
import re
import struct
import sys

DIM = 384
MODEL = "BAAI/bge-small-en-v1.5"
# Index lives next to this script, not under the caller's cwd.
DEFAULT_INDEX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "index")
STOP = frozenset(
    "a an the and or of for to in on with by is are was were be as at "
    "it its this that these those from into over under no not card use".split()
)


def _tokens(text):
    return [
        t
        for t in re.findall(r"[a-z0-9]+", text.lower())
        if t not in STOP and len(t) > 1
    ]


def _hash_vector(text, dim=DIM):
    toks = _tokens(text)
    vec = [0.0] * dim
    for t in toks:
        h = int(hashlib.sha256(t.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    n = sum(v * v for v in vec) ** 0.5
    if n:
        vec = [v / n for v in vec]
    return vec


class Embedder:
    def __init__(self):
        self._model = None
        try:
            # FastEmbed/HF Hub chokes on bracketed IPv6 entries in no_proxy
            # (e.g. "[::1]") under this VM's proxy env ("Invalid port: ':1]'");
            # strip bracketed entries before constructing the model.
            for _k in ("no_proxy", "NO_PROXY"):
                _v = os.environ.get(_k)
                if _v:
                    os.environ[_k] = ",".join(
                        p for p in _v.split(",") if "[" not in p)
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=MODEL)
        except Exception:
            self._model = None

    @property
    def backend(self):
        return "fastembed" if self._model is not None else "hash-fallback"

    def embed(self, texts):
        texts = list(texts)
        if self._model is not None:
            out = list(self._model.embed(texts))
            return [[float(v) for v in vec] for vec in out]
        return [_hash_vector(t) for t in texts]


# ---------------- parsers: one per kind, metadata only ----------------

def _parse_code(path):
    """AST: module docstring + function/class names + their docstrings."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            tree = ast.parse(fh.read())
    except Exception:
        return []
    doc = ast.get_docstring(tree) or ""
    recs = []
    if doc:
        recs.append((path, doc.splitlines()[0][:120]))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            d = ast.get_docstring(node) or ""
            label = "%s: %s" % (node.name, d.splitlines()[0][:100] if d else "no docstring")
            recs.append(("%s::%s" % (path, node.name), label))
    if not recs:
        recs.append((path, os.path.basename(path)))
    out = []
    for ident, label in recs:
        out.append({"path": ident, "kind": "code",
                    "title": label, "text": label})
    return out


def _content_texts_from_file(content_path):
    """content.json copy keyed by template id. Only real copy is returned;
    nothing is invented for templates with no entry."""
    try:
        with open(content_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return {}
    templates = data.get("templates", data)
    if not isinstance(templates, dict):
        return {}
    out = {}
    for tid, entry in templates.items():
        if not isinstance(entry, dict):
            continue
        vals = []

        def _collect(v):
            if isinstance(v, str):
                v = v.strip()
                if v:
                    vals.append(v)
            elif isinstance(v, list):
                for i in v:
                    _collect(i)
        for v in entry.values():
            _collect(v)
        if vals:
            out[str(tid)] = " ".join(vals)
    return out


def _content_texts_for(path):
    """Sibling content.json (same dir) descriptive copy keyed by template id.

    Returns {} when absent/unreadable. Only real copy is returned; nothing
    is invented for templates with no entry.
    """
    content_path = os.path.join(os.path.dirname(path), "content.json")
    if os.path.abspath(content_path) == os.path.abspath(path):
        return {}
    return _content_texts_from_file(content_path)


def _parse_registry_json(path, kind):
    """registry/content/photos JSON: id + name + category + slots + content copy."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return []
    items = data.get("templates", data.get("records",
                         data if isinstance(data, list) else []))
    if isinstance(items, dict):
        items = [{"id": k, **(v if isinstance(v, dict) else {})}
                 for k, v in items.items()]
    content_texts = _content_texts_for(path)
    # Canonical registry records carry a `sources` list pointing at the real
    # registries. Their sibling content.json does not exist next to the
    # canonical file, so pull each record's descriptive copy from its own
    # sources instead — otherwise canonical records index thinner than the
    # records they replace and eval scores drop.
    source_texts = {}
    if isinstance(data, dict) and "records" in data:
        for t in items:
            if not isinstance(t, dict):
                continue
            tid = str(t.get("id", "?"))
            for src in t.get("sources", []) or []:
                spath = src.get("path", "") if isinstance(src, dict) else ""
                if not spath:
                    continue
                if os.path.basename(spath) == "content.json":
                    merged = _content_texts_from_file(spath)
                else:
                    merged = _content_texts_for(spath)
                if tid in merged:
                    source_texts.setdefault(tid, merged[tid])
    out = []
    for t in items:
        if not isinstance(t, dict):
            continue
        tid = t.get("id", "?")
        parts = [str(t.get("name", tid)), str(t.get("category", "")),
                 "slots " + ",".join(t.get("slots", []) or []),
                 "photos " + ",".join(t.get("photo_keys", []) or [])]
        if str(tid) in content_texts:
            parts.append(content_texts[str(tid)])
        if str(tid) in source_texts:
            parts.append(source_texts[str(tid)])
        text = " ".join(p for p in parts if p.strip())
        out.append({"path": "%s#%s" % (path, tid), "kind": kind,
                    "title": "%s (%s)" % (t.get("name", tid),
                                          t.get("category", kind)),
                    "text": text})
    return out


def _parse_icons(path):
    """icons.js: exported iconNames/styles only, one record per icon."""
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
    except Exception:
        return []
    names = re.search(r"iconNames\s*=\s*Object\.freeze\(\[(.*?)\]\)", src, re.S)
    styles = re.search(r"iconStyles\s*=\s*Object\.freeze\(\[(.*?)\]\)", src, re.S)
    if not names:
        return [{"path": path, "kind": "icon",
                 "title": "code-drawn icon set", "text": "code-drawn icons"}]
    icons = re.findall(r"'([^']+)'", names.group(1))
    st = ", ".join(re.findall(r"'([^']+)'", styles.group(1))) if styles else ""
    return [{"path": "%s#%s" % (path, n), "kind": "icon",
             "title": "icon: %s (styles: %s)" % (n, st),
             "text": "code-drawn vector icon %s styles %s" % (n, st)}
            for n in icons]


def _parse_js_templates(path):
    """Node/pillow template registries: id + name + category + slots +
    photo_keys + layout keys per entry."""
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
    except Exception:
        return []
    recs = []
    for m in re.finditer(
            r"""['"]id['"]\s*:\s*['"]([^'"]+)['"]""", src):
        tid = m.group(1)
        window = src[m.start():m.start() + 2500]
        nm = re.search(r"""['"]name['"]\s*:\s*['"]([^'"]+)['"]""", window)
        cat = re.search(r"""['"]category['"]\s*:\s*['"]([^'"]+)['"]""", window)
        label = nm.group(1) if nm else tid
        cat_s = cat.group(1) if cat else ""
        slots_m = re.search(r"""['"]slots['"]\s*:\s*\[(.*?)\]""",
                            window, re.S)
        slots = ",".join(re.findall(r"""['"]([^'"]+)['"]""",
                                     slots_m.group(1))) if slots_m else ""
        photos_m = re.search(
            r"""['"]photo_keys['"]\s*:\s*\[(.*?)\]""", window, re.S)
        if photos_m is None:
            photos_m = re.search(
                r"""['"]photoKeys['"]\s*:\s*\[(.*?)\]""", window, re.S)
        photos = ",".join(re.findall(r"""['"]([^'"]+)['"]""",
                                      photos_m.group(1))) if photos_m else ""
        layout_m = re.search(r"""['"]layout['"]\s*:\s*\{(.*?)\}""",
                             window, re.S)
        layout = ",".join(re.findall(r"""['"]([^'"]+)['"]\s*:""",
                                      layout_m.group(1))) if layout_m else ""
        text = "%s %s %s template slots %s photos %s layout %s" % (
            tid, label, cat_s, slots, photos, layout)
        recs.append({"path": "%s#%s" % (path, tid), "kind": "template",
                     "title": "%s (%s)" % (label, cat_s or "template"),
                     "text": text})
    if not recs:
        recs.append({"path": path, "kind": "template",
                     "title": os.path.basename(path),
                     "text": os.path.basename(path)})
    seen, out = set(), []
    for r in recs:  # dedupe repeated id mentions
        if r["path"] not in seen:
            seen.add(r["path"])
            out.append(r)
    return out


def _parse_js_design_parts(path):
    """Item 5 parser: treatment tuples, element define() calls, brand records.

    Handles three real shapes the generic JS-template parser misses (it only
    matches `'id': '...'` object entries):
    - design-treatments.js: registry([['id', 'name', 'purpose', req?], ...])
    - design-elements.js: define('id','name','category','desc','purpose',...)
    - brands.js: demoBrands() entries + their directions[N] style/fonts.
    Only real file copy is emitted; nothing is invented.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
    except Exception:
        return []
    base = os.path.basename(path)
    out = []
    if base == "design-treatments.js":
        for m in re.finditer(
                r"(\w+)Treatments\s*=\s*registry\(\[(.*?)\]\)", src, re.S):
            group, body = m.group(1), m.group(2)
            for e in re.finditer(
                    r"\[\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'"
                    r"\s*(?:,\s*(true|false))?\s*\]", body):
                tid, name, purpose = e.group(1), e.group(2), e.group(3)
                req = e.group(4) == "true"
                text = "%s %s %s treatment %s requiresPhoto %s" % (
                    tid, name, purpose, group,
                    "true" if req else "false")
                out.append({"path": "%s#%s" % (path, tid), "kind": "treatment",
                            "title": "%s (%s treatment)" % (name, group),
                            "text": text})
    elif base == "design-elements.js":
        for m in re.finditer(
                r"define\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'"
                r"\s*,\s*'([^']+)'\s*,\s*'([^']+)'", src):
                tid, name, cat, desc, purpose = m.groups()
                text = "%s %s %s %s %s design element" % (
                    tid, name, cat, desc, purpose)
                out.append({"path": "%s#%s" % (path, tid), "kind": "element",
                            "title": "%s (%s)" % (name, cat),
                            "text": text})
    elif base == "brands.js":
        directions = []
        dm = re.search(r"const directions\s*=\s*\[(.*?)\];", src, re.S)
        if dm:
            for e in re.finditer(
                    r"\{\s*name:\s*'([^']+)'\s*,\s*style:\s*'([^']+)'"
                    r"\s*,\s*colors:\s*\{(.*?)\}\s*,\s*fonts:\s*\{(.*?)\}"
                    r"\s*,\s*radius:\s*(\d+)", dm.group(1), re.S):
                fonts = " ".join(re.findall(r":\s*'([^']+)'", e.group(4)))
                directions.append((e.group(1), e.group(2), fonts))
        for m in re.finditer(
                r"\.\.\.directions\[(\d)\]\s*,\s*id:\s*'([^']+)'"
                r"\s*,\s*name:\s*'([^']+)'\s*,\s*description:\s*'([^']*)'"
                r"\s*,\s*industry:\s*'([^']*)'\s*,\s*voice:\s*'([^']*)'",
                src):
            idx, tid, name, desc, industry, voice = m.groups()
            extra = ""
            try:
                dname, dstyle, dfonts = directions[int(idx)]
                extra = "%s %s %s" % (dname, dstyle, dfonts)
            except (IndexError, ValueError):
                pass
            text = "%s %s %s %s %s brand %s" % (
                tid, name, desc, industry, voice, extra)
            out.append({"path": "%s#%s" % (path, tid), "kind": "brand",
                        "title": "%s (brand)" % name,
                        "text": text})
    seen, uniq = set(), []
    for r in out:  # same-file dedupe; cross-file handled by _dedupe_recs
        if r["path"] not in seen:
            seen.add(r["path"])
            uniq.append(r)
    return uniq


# Basenames routed to the Item 5 parser instead of _parse_js_templates.
DESIGN_PART_FILES = frozenset(
    {"design-treatments.js", "design-elements.js", "brands.js"})

PARSERS = {"code": _parse_code, "icon": _parse_icons,
           "template": None, "treatment": None, "element": None,
           "brand": None, "graphic": _parse_code}


def parse_source(path, kind):
    if os.path.basename(path) in DESIGN_PART_FILES:
        # Design-part files always yield their own kind (treatment /
        # element / brand), whatever kind the source entry declares.
        return _parse_js_design_parts(path)
    if kind == "template" and path.endswith(".json"):
        return _parse_registry_json(path, kind)
    if kind == "template" and path.endswith(".js"):
        return _parse_js_templates(path)
    if kind == "icon":
        return _parse_icons(path)
    return _parse_code(path)


# ---------------- index store (JSONL + manifest, mtime incremental) ----------------

def _index_paths(index_dir):
    return (os.path.join(index_dir, "vectors.jsonl"),
            os.path.join(index_dir, "manifest.json"))


def load_manifest(index_dir):
    mp = _index_paths(index_dir)[1]
    try:
        with open(mp, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"sources": {}, "backend": None, "gaps": []}


def save_manifest(index_dir, manifest):
    with open(_index_paths(index_dir)[1], "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)


def _rec_key(rec):
    """Dedupe key: (kind, id) for `#id` records, else None (never deduped)."""
    if "#" in rec["path"]:
        return (rec["kind"], rec["path"].split("#")[-1])
    return None


def _source_rank(path):
    """Lower wins: canonical template-registry/registry.json first,
    then other registry.json files, other JSON, JS mirrors."""
    base = os.path.basename(path.split("#")[0])
    if "template-registry" in path.split("#")[0]:
        return -1
    if base == "registry.json":
        return 0
    if base.endswith(".json"):
        return 1
    if base.endswith(".js"):
        return 2
    return 3


def _dedupe_recs(recs, gaps):
    """Dedupe by (kind, id), preferring registry.json. Logs drops as gaps."""
    best = {}
    order = []
    for rec in recs:
        key = _rec_key(rec)
        if key is None:
            order.append(rec)
            continue
        rank = _source_rank(rec["path"])
        if key not in best:
            best[key] = (rank, rec)
            order.append(rec)
        elif rank < best[key][0]:
            dropped = best[key][1]
            g = "dedupe dropped duplicate: %s (kept %s)" % (
                dropped["path"], rec["path"])
            if g not in gaps:
                gaps.append(g)
            order[order.index(dropped)] = rec
            best[key] = (rank, rec)
        else:
            g = "dedupe dropped duplicate: %s (kept %s)" % (
                rec["path"], best[key][1]["path"])
            if g not in gaps:
                gaps.append(g)
    return order


def cmd_index(sources_path, index_dir, rebuild=False):
    with open(sources_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    vec_path, _ = _index_paths(index_dir)
    os.makedirs(index_dir, exist_ok=True)
    if rebuild:
        manifest = {"sources": {}, "backend": None, "gaps": []}
        if os.path.exists(vec_path):
            os.remove(vec_path)
    else:
        manifest = load_manifest(index_dir)
    emb = Embedder()
    gaps = list(spec.get("gaps", []))
    for g in manifest.get("gaps", []):
        if g not in gaps:
            gaps.append(g)
    new_recs, changed = [], False
    changed_sources = set()
    # Expand glob sources (e.g. ".../*.py") to the files they match.
    expanded = []
    for src in spec.get("sources", []):
        p = src["path"]
        if "*" in p or "?" in p:
            expanded.extend({"path": m, "kind": src["kind"]}
                            for m in sorted(glob.glob(p)))
        else:
            expanded.append(src)
    for src in expanded:
        path, kind = src["path"], src["kind"]
        if not os.path.exists(path):
            g = "missing: %s" % path
            if g not in gaps:
                gaps.append(g)
            continue
        mtime = os.path.getmtime(path)
        if not rebuild and manifest["sources"].get(path) == mtime:
            continue  # unchanged: never re-embed
        for rec in parse_source(path, kind):
            new_recs.append(rec)
        manifest["sources"][path] = mtime
        changed_sources.add(path)
        changed = True
    if new_recs:
        # Replace rows belonging to changed sources instead of stacking
        # new vectors alongside stale ones; then dedupe by (kind, id).
        kept = []
        if not rebuild and os.path.exists(vec_path):
            with open(vec_path, encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    base = r["path"].split("#")[0].split("::")[0]
                    if base not in changed_sources:
                        kept.append(r)
        new_recs = _dedupe_recs(new_recs, gaps)
        if not rebuild and kept:
            # Dedupe changed-source recs against untouched rows: the
            # better-ranked source wins and the loser is logged as a gap.
            keep_keys = {}
            for r in kept:
                k = ((r["kind"], r["path"].split("#")[-1])
                     if "#" in r["path"] else None)
                if k is not None:
                    keep_keys[k] = r
            final_new = []
            for rec in new_recs:
                key = _rec_key(rec)
                if key is not None and key in keep_keys:
                    old = keep_keys[key]
                    if _source_rank(rec["path"]) < _source_rank(old["path"]):
                        g = ("dedupe dropped duplicate: %s (kept %s)" %
                             (old["path"], rec["path"]))
                        if g not in gaps:
                            gaps.append(g)
                        kept.remove(old)
                        keep_keys[key] = {"path": rec["path"]}
                        final_new.append(rec)
                    else:
                        g = ("dedupe dropped duplicate: %s (kept %s)" %
                             (rec["path"], old["path"]))
                        if g not in gaps:
                            gaps.append(g)
                else:
                    final_new.append(rec)
            new_recs = final_new
        texts = [r["text"] for r in new_recs]
        batch = 16  # small batches: 4 CPU / 7.7 GB VM, one model at a time
        vecs = []
        for i in range(0, len(texts), batch):
            vecs.extend(emb.embed(texts[i:i + batch]))
        new_rows = [{"path": rec["path"], "kind": rec["kind"],
                     "title": rec["title"], "vector": vec}
                    for rec, vec in zip(new_recs, vecs)]
        if rebuild:
            kept = []
            mode = "w"
        else:
            # rewrite: kept rows (changed sources removed above) + new rows
            mode = "w"
            new_rows = kept + new_rows
        with open(vec_path, mode, encoding="utf-8") as fh:
            for r in new_rows:
                fh.write(json.dumps(r) + "\n")
        changed = True
    # drop stale rows pointing at moved files
    if os.path.exists(vec_path):
        with open(vec_path, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
        live = [
            r for r in rows
            if r["path"].split("#")[0].split("::")[0] in manifest["sources"]
            and os.path.exists(r["path"].split("#")[0].split("::")[0])
        ]
        for r in rows:
            base = r["path"].split("#")[0].split("::")[0]
            if base not in manifest["sources"] or not os.path.exists(base):
                g = "stale index entry, source moved: %s" % r["path"]
                if g not in gaps:
                    gaps.append(g)
        if len(live) != len(rows):
            with open(vec_path, "w", encoding="utf-8") as fh:
                for r in live:
                    fh.write(json.dumps(r) + "\n")
    manifest["backend"] = emb.backend
    manifest["gaps"] = gaps
    save_manifest(index_dir, manifest)
    print(json.dumps({"indexed_new": len(new_recs), "backend": emb.backend,
                      "gaps": gaps}))


def _cos(a, b):
    n = (sum(x * x for x in a) ** 0.5) * (sum(x * x for x in b) ** 0.5)
    if not n:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / n


def _indexed_texts(index_dir, rows):
    """Map index path -> indexed text by re-parsing manifest sources.

    Index rows carry only {path, kind, title, vector} (format unchanged),
    so keyword overlap is computed against the re-parsed record text --
    the same text that was embedded -- never just path + title.
    """
    base_kind = {}
    for r in rows:
        base = r["path"].split("#")[0].split("::")[0]
        base_kind.setdefault(base, r.get("kind", "template"))
    texts = {}
    for base, kind in base_kind.items():
        if not os.path.exists(base):
            continue
        try:
            recs = parse_source(base, kind)
        except Exception:
            continue
        for rec in recs:
            texts.setdefault(rec["path"], rec.get("text", ""))
    return texts


def _idf_weights(texts):
    """Inverse-frequency weights over indexed texts: 1 + (N - df) / N."""
    df = {}
    toks = {}
    for p, t in texts.items():
        ts = set(_tokens(t))
        toks[p] = ts
        for tok in ts:
            df[tok] = df.get(tok, 0) + 1
    n = max(len(texts), 1)
    return toks, {t: 1.0 + (n - c) / n for t, c in df.items()}


def _id_tokens(path):
    frag = path.split("#")[-1] if "#" in path else ""
    if not frag:
        return set()
    return set(_tokens(frag.replace("-", " ").replace("_", " ")))


# Hybrid scoring, calibrated 2026-11-08 from reuse-library/eval_queries.json
# via `run_eval.py --grid` (FastEmbed backend): smallest passing weight
# 0.05, margin 0.2141 (min positive 0.7709 pastor-quote, max negative
# 0.5568 plush-bunny); threshold is the measured midpoint (0.7709+0.5568)/2
# = 0.6639, frozen as 0.66.
# score = cosine + min(KEYWORD_WEIGHT * idf_overlap, KEYWORD_WEIGHT)
#         + (EXACT_ID_BONUS iff the record id's tokens are all in the query).
# Bounded: cosine in [-1, 1], keyword part in [0, KEYWORD_WEIGHT],
# exact-id bonus in {0, EXACT_ID_BONUS}; max score 1 + 0.05 + 0.10 = 1.15.
KEYWORD_WEIGHT = 0.05
EXACT_ID_BONUS = 0.10
WEAK_MATCH_THRESHOLD = 0.66


def match_quality(top_score):
    return "strong" if top_score >= WEAK_MATCH_THRESHOLD else "weak"


def cmd_search(query, kind, index_dir, top, as_json=False):
    vec_path, _ = _index_paths(index_dir)
    if not os.path.exists(vec_path):
        print(json.dumps({"error": "no index; run index first"}))
        return 1
    with open(vec_path, encoding="utf-8") as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    if kind:
        rows = [r for r in rows if r["kind"] == kind]
    emb = Embedder()
    qvec = emb.embed([query])[0]
    qtok = set(_tokens(query))
    texts = _indexed_texts(index_dir, rows)
    rtok_map, idf = _idf_weights(texts) if texts else ({}, {})
    q_den = sum(idf.get(t, 0.0) for t in qtok) or 1.0
    scored = []
    for r in rows:
        base = _cos(qvec, r["vector"])
        rtok = rtok_map.get(r["path"])
        if rtok is None:  # source vanished: fall back to the title
            rtok = set(_tokens(r.get("title", "")))
        overlap = sum(idf.get(t, 0.0) for t in (qtok & rtok)) / q_den
        kw = min(KEYWORD_WEIGHT * overlap, KEYWORD_WEIGHT)
        idt = _id_tokens(r["path"])
        bonus = EXACT_ID_BONUS if idt and idt <= qtok else 0.0
        scored.append((base + kw + bonus, r))
    scored.sort(key=lambda s: -s[0])
    top_hits = scored[:top]
    top_score = top_hits[0][0] if top_hits else 0.0
    weak = top_score < WEAK_MATCH_THRESHOLD
    for score, r in top_hits:
        # path + score + one-line label only; contents stay on disk
        print("%s\t%.4f\t%s" % (r["path"], score, r["title"]))
    if as_json:
        print(json.dumps({
            "results": [{"path": r["path"], "score": round(s, 4),
                         "label": r["title"]} for s, r in top_hits],
            "top_score": round(top_score, 4),
            "weak_match": weak,
            "match_quality": match_quality(top_score),
        }))
    else:
        print("weak_match=%s top_score=%.4f match_quality=%s"
              % (str(weak).lower(), top_score, match_quality(top_score)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reuse_library.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("index")
    pi.add_argument("--sources", required=True)
    pi.add_argument("--index-dir", default=DEFAULT_INDEX_DIR)
    pi.add_argument("--rebuild", action="store_true",
                    help="rewrite vectors.jsonl from scratch")
    ps = sub.add_parser("search")
    ps.add_argument("--query", required=True)
    ps.add_argument("--kind", default=None,
                    choices=["code", "graphic", "icon", "template",
                             "treatment", "element", "brand"])
    ps.add_argument("--index-dir", default=DEFAULT_INDEX_DIR)
    ps.add_argument("--top", type=int, default=5)
    ps.add_argument("--json", action="store_true",
                    help="append a machine-readable weak-match summary line")
    a = ap.parse_args(argv)
    if a.cmd == "index":
        cmd_index(a.sources, a.index_dir, rebuild=a.rebuild)
        return 0
    return cmd_search(a.query, a.kind, a.index_dir, a.top, as_json=a.json)


if __name__ == "__main__":
    sys.exit(main())
