#!/usr/bin/env python3
"""Hallmark pack — the useful mechanics of Nutlope/hallmark, as code.

Adapted 2026-11-12 for our tools (Hallmark is MIT; this is an original
implementation of its ideas, scoped by surface — its web-only bans do
NOT apply to social cards, where e.g. a badge pill is legitimate).

snapshot   Inventory a page/card BEFORE a redesign (--before record):
           links, ids, headings, images, form fields, handlers, test
           hooks, plus a SHA-256 per file.
kept       Compare a target against a snapshot (--kept): anything the
           original had and the new one lost is FAIL (links, fields,
           handlers, ids, hooks) or WARN (headings, images), unless it
           is recorded as dropped with a reason.
words      Word-budget lint. Budgets per surface (Hallmark gate 58:
           ~80 words per screen on the web; far less on a card).
gatecheck  Tiered gates. Floor = never waivable, ships nothing.
           Reflex = a model default; waivable on the record with guard
           evidence + a specific reason (>=24 chars; waiving a Floor
           gate is rejected). Finish = craft detail, answered, never
           blocks. Waivers/answers are read from the file itself or a
           --stamp file:  waive <gate> | <guard> | <reason>
deal       Deal 3 themes from a themes dir, clearing the recent
           rotation log. A theme is a MATERIAL (one file, <=8 KB),
           never a plan; a build reads exactly one.
rotation   Rotation log: check a candidate entry against the last 3
           builds (mirror test) or append it. Same gate waived in 3
           consecutive entries is flagged as a house style.
brief      The Picks block + decision stamp: material inventory
           (real / pictures / absent — absent must be DECLARED, facts
           are never inferred), shape, theme, signature, the hero-first
           stage plan with a fresh-context review between stages, and
           the pre-emit critique (P/H/E/S/R/V, <3 triggers revision).
           Written as the first lines of the stamp file.

Stdlib only. Every function returns (exit_code, payload_dict).
Exit codes: 0 pass, 1 fail, 2 tool error.
"""

import hashlib
import json
import re
import time
from pathlib import Path

MAX_ITEMS = 400
MAX_SECTIONS = 60

SURFACES = ("web", "tool", "card", "social", "glance")
# words budgets: per-section, total, first-section (hero)
BUDGETS = {
    "web":    {"section": 80,  "total": 450, "hero": 30},
    "tool":   {"section": 120, "total": 900, "hero": 40},
    "card":   {"section": 30,  "total": 30,  "hero": 30},
    "social": {"section": 35,  "total": 60,  "hero": 35},
    "glance": {"section": 20,  "total": 20,  "hero": 20},
}
FAIL_KINDS = {"link", "field", "handler", "id", "hook"}
WARN_KINDS = {"heading", "image"}

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
WORD_RE = re.compile(r"[A-Za-z0-9'’\-]+")


# ---------- shared parsing ----------

def _read(path):
    p = Path(path).expanduser()
    if not p.is_file():
        return None, f"not a file: {path}"
    return p.read_text(encoding="utf-8", errors="ignore"), None


def _targets(path):
    p = Path(path).expanduser()
    if p.is_file():
        return [p]
    if p.is_dir():
        out = [f for f in sorted(p.rglob("*"))
               if f.is_file() and f.suffix.lower()
               in (".html", ".htm", ".md", ".txt", ".json")]
        return out
    return []


def _strip_html(text):
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<!--.*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _visible_text(path, text):
    suf = path.suffix.lower()
    if suf in (".html", ".htm"):
        return _strip_html(text)
    if suf == ".json":
        try:
            doc = json.loads(text)
        except ValueError:
            return text
        vals = []

        def walk(o):
            if isinstance(o, str):
                vals.append(o)
            elif isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(doc)
        return " ".join(vals)
    return text


def _sections(path, text):
    """Split into (name, visible text) sections."""
    suf = path.suffix.lower()
    if suf in (".html", ".htm"):
        parts = re.split(r"(?i)(?=<h[12]\b|<section\b|<article\b|<header\b)",
                         text)
        out = []
        for i, part in enumerate(parts):
            vis = _strip_html(part)
            if not vis:
                continue
            m = re.search(r"(?is)<h[12][^>]*>(.*?)</h[12]>", part)
            name = _strip_html(m.group(1))[:40] if m else f"section-{i + 1}"
            out.append((name, vis))
        return out or [("page", _strip_html(text))]
    if suf == ".json":
        return [("layout", _visible_text(path, text))]
    parts = re.split(r"(?m)(?=^#{1,2}\s)", text)
    out = []
    for i, part in enumerate(parts):
        vis = part.strip()
        if not vis:
            continue
        first = vis.splitlines()[0].lstrip("# ").strip()
        out.append((first[:40] or f"section-{i + 1}", vis))
    return out or [("page", text)]


def _inventory_file(path, text):
    items = []

    def add(kind, value):
        value = re.sub(r"\s+", " ", str(value)).strip()
        if value:
            items.append(f"{kind}:{value}")
    suf = path.suffix.lower()
    if suf in (".html", ".htm"):
        for m in re.finditer(r"""href\s*=\s*["']([^"']+)["']""", text):
            add("link", m.group(1))
        for m in re.finditer(r"""\bid\s*=\s*["']([^"']+)["']""", text):
            add("id", m.group(1))
        for m in re.finditer(r"(?is)<h[1-6][^>]*>(.*?)</h[1-6]>", text):
            add("heading", _strip_html(m.group(1)).lower())
        for m in re.finditer(r"""<img[^>]+src\s*=\s*["']([^"']+)["']""",
                             text):
            add("image", m.group(1))
        for tag in re.finditer(
                r"(?is)<(input|select|textarea)\b([^>]*)>", text):
            attrs = tag.group(2)
            nm = re.search(r"""name\s*=\s*["']([^"']+)["']""", attrs)
            tp = re.search(r"""type\s*=\s*["']([^"']+)["']""", attrs)
            add("field", f"{nm.group(1) if nm else '?'}:"
                         f"{tp.group(1) if tp else tag.group(1)}")
        for m in re.finditer(r"""\s(on\w+)\s*=\s*["']""", text):
            add("handler", m.group(1).lower())
        for m in re.finditer(
                r"""data-testid\s*=\s*["']([^"']+)["']""", text):
            add("hook", m.group(1))
    else:
        for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
            add("link", m.group(1))
        for m in re.finditer(r"(?m)^#{1,6}\s+(.*)$", text):
            add("heading", m.group(1).strip().lower())
        for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text):
            add("image", m.group(1))
    return items


# ---------- snapshot / kept ----------

def snapshot(target, out_path, force=False):
    files = _targets(target)
    if not files:
        return 2, {"error": f"snapshot: no readable target: {target}"}
    out = Path(out_path).expanduser()
    if out.exists() and not force:
        return 2, {"error": f"snapshot: {out} exists — pass --force"}
    items, hashes = [], {}
    for f in files:
        text, err = _read(f)
        if err:
            return 2, {"error": err}
        hashes[str(f)] = hashlib.sha256(
            f.read_bytes()).hexdigest()[:16]
        items.extend(_inventory_file(f, text))
    items = sorted(set(items))[:MAX_ITEMS]
    doc = {"created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "target": str(target), "files": hashes, "items": items}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    kinds = {}
    for it in items:
        kinds[it.split(":", 1)[0]] = kinds.get(it.split(":", 1)[0], 0) + 1
    return 0, {"snapshot": str(out), "files": len(hashes),
               "items": len(items), "kinds": kinds}


def kept(before_path, target, dropped=None):
    bp = Path(before_path).expanduser()
    if not bp.is_file():
        return 2, {"error": f"kept: snapshot not found: {before_path}"}
    try:
        doc = json.loads(bp.read_text(encoding="utf-8"))
        before_items = doc["items"]
    except (ValueError, KeyError, TypeError):
        return 2, {"error": "kept: not a valid snapshot file"}
    files = _targets(target)
    if not files:
        return 2, {"error": f"kept: no readable target: {target}"}
    now = set()
    for f in files:
        text, err = _read(f)
        if err:
            return 2, {"error": err}
        now.update(_inventory_file(f, text))
    dropped = {d.strip() for d in (dropped or []) if d.strip()}
    missing_fail, missing_warn, dropped_found = [], [], []
    kept_counts, total_counts = {}, {}
    for it in before_items:
        kind = it.split(":", 1)[0]
        total_counts[kind] = total_counts.get(kind, 0) + 1
        if it in now:
            kept_counts[kind] = kept_counts.get(kind, 0) + 1
        elif it in dropped or any(it.startswith(d + ":") or
                                  it == d for d in dropped):
            dropped_found.append(it)
        elif kind in WARN_KINDS:
            missing_warn.append(it)
        else:
            missing_fail.append(it)
    summary = {k: f"{kept_counts.get(k, 0)}/{n}"
               for k, n in sorted(total_counts.items())}
    payload = {"kept": summary, "missing_fail": missing_fail[:50],
               "missing_warn": missing_warn[:50],
               "dropped_recorded": dropped_found[:50],
               "verdict": "FAIL" if missing_fail else "PASS"}
    return (1 if missing_fail else 0), payload


# ---------- words ----------

def words(target, surface="web", budget=None, total_budget=None):
    if surface not in BUDGETS:
        return 2, {"error": f"words: surface must be one of {SURFACES}"}
    files = _targets(target)
    if not files:
        return 2, {"error": f"words: no readable target: {target}"}
    b = dict(BUDGETS[surface])
    if budget:
        b["section"] = int(budget)
    if total_budget:
        b["total"] = int(total_budget)
    sections, total = [], 0
    for f in files:
        text, err = _read(f)
        if err:
            return 2, {"error": err}
        for name, vis in _sections(f, text):
            n = len(WORD_RE.findall(vis))
            total += n
            sections.append({"name": name, "words": n,
                             "over": n > b["section"]})
    over = [s for s in sections if s["over"]]
    hero = sections[0]["words"] if sections else 0
    payload = {"surface": surface, "total_words": total,
               "total_budget": b["total"],
               "section_budget": b["section"],
               "hero_words": hero, "hero_budget": b["hero"],
               "sections": sections[:MAX_SECTIONS],
               "over_sections": len(over),
               "total_over": total > b["total"],
               "hero_over": hero > b["hero"]}
    bad = bool(over) or payload["total_over"]
    payload["verdict"] = "FAIL" if bad else "PASS"
    return (1 if bad else 0), payload


# ---------- gatecheck ----------

# gate id -> tier per surface group. "skip" = not applicable.
def _tier(gate, surface):
    table = {
        "lorem":       {"*": "floor"},
        "words":       {"tool": "reflex", "*": "floor"},
        "gradient-pb": {"web": "floor", "tool": "floor",
                        "*": "reflex"},
        "transition-all": {"web": "floor", "tool": "floor",
                           "*": "skip"},
        "caps-label":  {"web": "floor", "tool": "floor",
                        "*": "reflex"},
        "emoji-icon":  {"*": "reflex"},
        "literal-color": {"web": "reflex", "tool": "reflex",
                          "*": "skip"},
    }
    row = table[gate]
    return row.get(surface, row.get("*", "reflex"))


def _waivers(text):
    waived, answered = {}, {}
    pat = re.compile(
        r"(?im)^[^\n]*?\b(waive|answered)\s+([A-Za-z0-9\-]+)\s*"
        r"(?:\||·|;)\s*(.*?)\s*(?:(?:\||·|;)\s*(.*))?$")
    for m in pat.finditer(text):
        kind, gate = m.group(1).lower(), m.group(2).lower()
        if kind == "waive":
            guard = (m.group(3) or "").strip()
            reason = (m.group(4) or "").strip()
            waived[gate] = {"guard": guard, "reason": reason}
        else:
            answered[gate] = (m.group(3) or "").strip()
    return waived, answered


def gatecheck(target, surface="web", stage=None, stamp_path=None):
    if surface not in BUDGETS:
        return 2, {"error": f"gatecheck: surface must be {SURFACES}"}
    files = _targets(target)
    if not files:
        return 2, {"error": f"gatecheck: no readable target: {target}"}
    raw, visible = "", ""
    for f in files:
        text, err = _read(f)
        if err:
            return 2, {"error": err}
        raw += "\n" + text
        visible += "\n" + _visible_text(f, text)
    waiver_text = raw
    if stamp_path:
        st, err = _read(stamp_path)
        if err:
            return 2, {"error": err}
        waiver_text += "\n" + st
    waived, answered = _waivers(waiver_text)

    findings = []  # (gate, evidence)

    if re.search(r"(?i)lorem ipsum|dolor sit amet", raw):
        findings.append(("lorem", "placeholder latin in the file"))
    grads = re.findall(r"(?is)(?:linear|radial)-gradient\([^)]*\)", raw)
    purple = ("purple", "violet", "#8b5cf6", "#a855f7", "#7c3aed",
              "#9333ea")
    blue = ("blue", "#3b82f6", "#2563eb", "#6366f1", "#60a5fa")
    if any(any(p in g.lower() for p in purple) and
           any(b in g.lower() for b in blue) for g in grads):
        findings.append(("gradient-pb", "purple-to-blue gradient"))
    if re.search(r"transition\s*:\s*all\b", raw):
        findings.append(("transition-all", "transition: all"))
    caps = []
    for m in re.finditer(
            r"(?is)<(h[1-6]|button|label|th)[^>]*>(.*?)</\1>", raw):
        t = _strip_html(m.group(2))
        if len(WORD_RE.findall(t)) >= 3 and t.upper() == t \
                and re.search(r"[A-Z]{3}", t):
            caps.append(t)
    if not caps:
        for ln in raw.splitlines():
            t = _strip_html(ln).strip()
            if len(WORD_RE.findall(t)) >= 3 and t.upper() == t \
                    and re.search(r"[A-Z]{3}", t) \
                    and not ln.strip().startswith(("//", "/*", "*")):
                caps.append(t)
    if caps:
        findings.append(("caps-label",
                         f"tracked/all-caps label: {caps[0][:60]}"))
    emo = EMOJI_RE.search(visible)
    if emo:
        findings.append(("emoji-icon",
                         f"emoji used as content/icon: {emo.group(0)}"))
    style = "\n".join(re.findall(r"(?is)<style[^>]*>(.*?)</style>", raw))
    css = style if style else (raw if target.endswith(".css") else "")
    if css:
        roots = re.findall(r"(?is):root\s*\{[^}]*\}", css)
        outside = css
        for r in roots:
            outside = outside.replace(r, " ")
        hexes = re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b",
                           outside)
        if hexes:
            findings.append(("literal-color",
                             f"{len(hexes)} literal colour(s) outside "
                             "the token block"))
    # words gate (reuse the sections of the first file set)
    if stage == "hero":
        code_w, wpay = words(target, surface=surface)
        if wpay.get("hero_over"):
            findings.append(
                ("words", f"hero {wpay['hero_words']} words > "
                          f"budget {wpay['hero_budget']}"))
    else:
        code_w, wpay = words(target, surface=surface)
        if code_w == 1:
            findings.append(
                ("words", f"total {wpay['total_words']}/"
                          f"{wpay['total_budget']}, "
                          f"{wpay['over_sections']} section(s) over "
                          f"{wpay['section_budget']}"))

    results, blocked = [], False
    seen = set()
    for gate, evidence in findings:
        seen.add(gate)
        tier = _tier(gate, surface)
        if tier == "skip":
            results.append({"gate": gate, "tier": "n/a",
                            "status": "NOTE", "evidence": evidence})
            continue
        w = waived.get(gate)
        if tier == "floor":
            status = "FAIL"
            if w:
                status = "FAIL (waiver rejected: Floor never waives)"
            blocked = True
        elif w:
            if len(w["reason"]) >= 24 and w["guard"]:
                status = "WAIVED"
            else:
                status = "REFLEX (waiver invalid: needs guard + a "
                status += "specific reason of 24+ chars)"
                blocked = True
        else:
            status = "REFLEX"
            blocked = True
        results.append({"gate": gate, "tier": tier, "status": status,
                        "evidence": evidence})
    # Finish checks: answered, never blocking
    finish = []
    ctas = len(re.findall(
        r"(?i)\b(buy now|sign up|get started|subscribe now)\b", visible))
    finish.append({"check": "finish:cta-count", "found": ctas,
                   "status": "ANSWERED" if "finish:cta-count" in answered
                   else "OPEN"})
    if surface == "web" and "<footer" not in raw.lower() \
            and not target.endswith((".md", ".txt", ".json")):
        finish.append({"check": "finish:footer", "found": 0,
                       "status": "ANSWERED" if "finish:footer" in answered
                       else "OPEN"})
    payload = {"surface": surface, "stage": stage or "full",
               "findings": results, "finish": finish,
               "floor_fail": sum(1 for r in results
                                 if r["status"].startswith("FAIL")),
               "reflex_open": sum(1 for r in results
                                  if r["status"].startswith("REFLEX")),
               "waived": sum(1 for r in results
                             if r["status"] == "WAIVED"),
               "verdict": "FAIL" if blocked else "PASS"}
    return (1 if blocked else 0), payload


# ---------- deal / rotation ----------

def _load_log(log_path):
    if not log_path:
        return []
    p = Path(log_path).expanduser()
    if not p.is_file():
        return []
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
        return doc if isinstance(doc, list) else doc.get("entries", [])
    except ValueError:
        return []


def deal(themes_dir, log_path=None, prompt=""):
    d = Path(themes_dir).expanduser()
    if not d.is_dir():
        return 2, {"error": f"deal: not a directory: {themes_dir}"}
    themes = []
    for f in sorted(d.glob("*.md")):
        themes.append({"slug": f.stem, "kb": round(f.stat().st_size / 1024, 1),
                       "over_8kb": f.stat().st_size > 8192})
    if len(themes) < 3:
        return 2, {"error": "deal: need at least 3 theme files (*.md)"}
    recent = [e.get("theme") for e in _load_log(log_path)[-3:]]
    pool = [t for t in themes if t["slug"] not in recent] or themes
    pool.sort(key=lambda t: hashlib.sha256(
        (prompt + "|" + t["slug"]).encode()).hexdigest())
    dealt = pool[:3]
    return 0, {"dealt": dealt, "cleared_recent": [r for r in recent if r],
               "pool": len(pool),
               "note": "themes are materials, not plans; "
                       "the build reads exactly one"}


AXES = ("theme", "shape", "hero", "nav", "footer", "signature")


def rotation(op, log_path, entry=None):
    p = Path(log_path).expanduser()
    entries = _load_log(log_path)
    if op == "add":
        if not entry or not entry.get("theme"):
            return 2, {"error": "rotation add: entry needs a theme"}
        kept_entry = {k: entry.get(k, "") for k in AXES}
        if entry.get("waived"):
            kept_entry["waived"] = entry["waived"]
        entry = kept_entry
        entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        entries.append(entry)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(entries, indent=1), encoding="utf-8")
        return 0, {"logged": str(p), "entries": len(entries),
                   "entry": entry}
    if op == "check":
        if not entry:
            return 2, {"error": "rotation check: no candidate entry"}
        worst = None
        for prev in entries[-3:]:
            shared = [a for a in AXES
                      if entry.get(a) and entry.get(a) == prev.get(a)]
            if worst is None or len(shared) > len(worst[0]):
                worst = (shared, prev)
        shared = worst[0] if worst else []
        # house style: same gate waived in last 3 entries
        recent_waives = [e.get("waived", "") for e in entries[-3:]]
        house = [g for g in set(recent_waives)
                 if g and recent_waives.count(g) >= 3]
        mirror_fail = len(shared) >= 4
        payload = {"shared_axes_with_recent": shared,
                   "mirror_test": "FAIL" if mirror_fail else "PASS",
                   "house_style_gates": house,
                   "note": "change one decision when the mirror "
                           "test fails"}
        return (1 if mirror_fail else 0), payload
    if op == "list":
        return 0, {"entries": entries[-10:], "count": len(entries)}
    return 2, {"error": f"rotation: unknown op: {op}"}


# ---------- brief (Picks block + decision stamp) ----------

def brief(out_path, surface, job, shape, theme, signature,
          real, pictures, absent, critique="", theme_file=None,
          waivers=None, force=False):
    if surface not in BUDGETS:
        return 2, {"error": f"brief: surface must be one of {SURFACES}"}
    missing = [k for k, v in (("job", job), ("shape", shape),
                              ("theme", theme),
                              ("signature", signature),
                              ("real", real), ("pictures", pictures),
                              ("absent", absent)) if not v]
    if missing:
        return 2, {"error": "brief: material must be declared, "
                           f"missing: {', '.join(missing)} "
                           "(write 'none' for absent when there is "
                           "nothing absent)"}
    out = Path(out_path).expanduser()
    if out.exists() and not force:
        return 2, {"error": f"brief: {out} exists — pass --force"}
    theme_note = theme
    theme_over = False
    if theme_file:
        tf = Path(theme_file).expanduser()
        if not tf.is_file():
            return 2, {"error": f"brief: theme file not found: "
                                f"{theme_file}"}
        kb = tf.stat().st_size / 1024
        theme_over = tf.stat().st_size > 8192
        theme_note = f"{theme} (file {tf.name}, {kb:.1f} KB, "
        theme_note += "OVER the 8 KB material cap)" if theme_over \
            else f"{theme} (file {tf.name}, {kb:.1f} KB)"
    scores = {}
    for tok in re.findall(r"([PHESRV])\s*[:=]?\s*([1-5])",
                          (critique or "").upper()):
        scores[tok[0]] = int(tok[1])
    weakest = min(scores, key=scores.get) if scores else None
    revision = any(v < 3 for v in scores.values())
    lines = [
        "/* Hallmark-pack · v1 · decision stamp — this block is the "
        "record",
        f"   surface: {surface} · job: {job}",
        f"   shape: {shape} · theme: {theme_note} (material only, "
        "never a plan; the build reads exactly this one)",
        f"   signature: {signature}",
        f"   material · real: {real}",
        f"   material · pictures: {pictures}",
        f"   material · absent: {absent} (declared; never inferred "
        "or invented)",
        "   stages · 1 hero/first-card only -> gatecheck --stage hero "
        "-> fresh-context review (reviewer gets the last word)",
        "   stages · 2 the rest -> gatecheck full -> snapshot/kept "
        "if this is a redesign",
        f"   pre-emit critique: {critique or 'not scored'}"
        + (f" · weakest: {weakest}" if weakest else "")
        + (" · REVISION REQUIRED before build (a score under 3)"
           if revision else ""),
    ]
    for w in (waivers or []):
        lines.append(f"   waive {w}")
    lines.append("*/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = {"stamp": str(out), "surface": surface,
               "critique": scores, "weakest": weakest,
               "revision_required": revision,
               "theme_over_8kb": theme_over,
               "verdict": "REVISE" if revision or theme_over
                          else "READY"}
    return (1 if revision or theme_over else 0), payload
