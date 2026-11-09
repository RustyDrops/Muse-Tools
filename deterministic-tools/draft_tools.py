"""Draft tools: peek, grep, diff, stats, toc, strip. Stdlib only."""

import ast
import difflib
import hashlib
import io
import tokenize
from pathlib import Path

TRUNC = 300
MAX_PEEK_LINES = 100
MAX_GREP_MATCHES = 50
MAX_DIFF_LINES = 200
MAX_TOC_HEADINGS = 200


def _trunc(s):
    s = str(s)
    return s if len(s) <= TRUNC else s[:TRUNC]


def peek(path, start, end):
    """Lines [start, end] inclusive, 1-based, with line numbers."""
    p = Path(path)
    if not p.is_file():
        return 2, {"error": f"file not found: {path}"}
    try:
        start, end = int(start), int(end)
    except (TypeError, ValueError):
        return 2, {"error": "start/end must be integers"}
    if start < 1 or end < start:
        return 2, {"error": f"out of range: [{start},{end}]"}
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        return 2, {"error": f"cannot read: {exc}"}
    lines = text.splitlines()
    if start > len(lines) or end > len(lines):
        return 2, {"error": f"out of range: file has {len(lines)} lines"}
    wanted = lines[start - 1:end]
    truncated = False
    if len(wanted) > MAX_PEEK_LINES:
        wanted = wanted[:MAX_PEEK_LINES]
        truncated = True
    return 0, {
        "path": str(path),
        "start": start,
        "end": end,
        "total_lines": len(lines),
        "truncated": truncated,
        "lines": [
            {"n": n, "text": _trunc(t)}
            for n, t in zip(range(start, start + len(wanted)), wanted)
        ],
    }


def grep(path, pattern, ignore_case=False, regex=False):
    """Line search in a single file. Default: literal substring."""
    import re

    p = Path(path)
    if not p.is_file():
        return 2, {"error": f"file not found: {path}"}
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        return 2, {"error": f"cannot read: {exc}"}
    flags = re.IGNORECASE if ignore_case else 0
    rx = None
    if regex:
        try:
            rx = re.compile(pattern, flags)
        except re.error as exc:
            return 2, {"error": f"bad regex: {exc}"}
    needle = pattern if regex else (pattern.lower() if ignore_case else pattern)
    matches = []
    for n, line in enumerate(text.splitlines(), 1):
        hit = bool(rx.search(line)) if rx else (
            needle in line.lower() if ignore_case else needle in line)
        if hit:
            matches.append({"n": n, "text": _trunc(line)})
            if len(matches) >= MAX_GREP_MATCHES:
                break
    if not matches:
        return 1, {"path": str(path), "pattern": pattern,
                   "matches": [], "count": 0, "found": False}
    # truncated flag: true if we stopped at the cap and more may exist
    capped = len(matches) >= MAX_GREP_MATCHES
    return 0, {"path": str(path), "pattern": pattern, "matches": matches,
               "count": len(matches), "found": True, "capped": capped}


def diff(old, new):
    """Unified diff via difflib. Returns counts + diff lines only."""
    a, b = Path(old), Path(new)
    for label, q in (("old", a), ("new", b)):
        if not q.is_file():
            return 2, {"error": f"{label} file not found: {q}"}
    try:
        a_lines = a.read_text(encoding="utf-8").splitlines()
        b_lines = b.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return 2, {"error": f"cannot read: {exc}"}
    raw = list(difflib.unified_diff(
        a_lines, b_lines, fromfile=str(old), tofile=str(new), lineterm=""))
    truncated = False
    if len(raw) > MAX_DIFF_LINES:
        raw = raw[:MAX_DIFF_LINES]
        truncated = True
    identical = len(raw) == 0
    payload = {"old": str(old), "new": str(new),
               "old_lines": len(a_lines), "new_lines": len(b_lines),
               "identical": identical,
               "truncated": truncated,
               "diff": [_trunc(l) for l in raw]}
    return (0 if identical else 1), payload


def stats(path):
    """Line count, byte size, SHA-256, estimated tokens. No content."""
    p = Path(path)
    if not p.is_file():
        return 2, {"error": f"file not found: {path}"}
    try:
        raw = p.read_bytes()
    except OSError as exc:
        return 2, {"error": f"cannot read: {exc}"}
    try:
        text = raw.decode("utf-8")
        chars = len(text)
        lines = len(text.splitlines())
    except UnicodeDecodeError:
        chars = len(raw)
        lines = raw.count(b"\n") + (1 if raw and not raw.endswith(b"\n") else 0)
    return 0, {"path": str(path), "lines": lines, "bytes": len(raw),
               "sha256": hashlib.sha256(raw).hexdigest(),
               "est_tokens": round(chars / 4)}


def toc(path):
    """Markdown headings with level, text, char offset."""
    import re

    p = Path(path)
    if not p.is_file():
        return 2, {"error": f"file not found: {path}"}
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        return 2, {"error": f"cannot read: {exc}"}
    pat = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
    heads, offset = [], 0
    for line in text.splitlines(keepends=True):
        m = pat.match(line.rstrip("\n"))
        if m:
            heads.append({"level": len(m.group(1)),
                          "text": _trunc(m.group(2)), "offset": offset})
            if len(heads) >= MAX_TOC_HEADINGS:
                break
        offset += len(line)
    if not heads:
        return 1, {"path": str(path), "headings": [], "count": 0,
                   "found": False}
    return 0, {"path": str(path), "headings": heads,
               "count": len(heads), "found": True,
               "capped": len(heads) >= MAX_TOC_HEADINGS}


def _docstring_ranges(tree):
    """(start, end) 1-based line ranges of module/class/def docstrings."""
    out = []

    def add(node):
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            seg = node.body[0]
            out.append((seg.lineno, seg.end_lineno or seg.lineno))

    add(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            add(node)
    return out


def strip(path, out=None):
    """Strip comments/docstrings via tokenize. Writes ONLY to out.

    Without out: dry-run returning counts. Never prints stripped code.
    """
    p = Path(path)
    if not p.is_file():
        return 2, {"error": f"file not found: {path}"}
    try:
        src = p.read_text(encoding="utf-8")
    except OSError as exc:
        return 2, {"error": f"cannot read: {exc}"}
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return 2, {"error": f"syntax error: {exc.msg}",
                   "line": exc.lineno, "col": exc.offset}
    doc_ranges = _docstring_ranges(tree)
    kept = []
    try:
        toks = tokenize.generate_tokens(io.StringIO(src).readline)
        for tok in toks:
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type == tokenize.STRING:
                s, e = tok.start[0], tok.end[0]
                if any(a <= s and e <= b for a, b in doc_ranges):
                    continue
            kept.append(tok)
        stripped = tokenize.untokenize(kept)
        if isinstance(stripped, bytes):
            stripped = stripped.decode("utf-8")
    except (tokenize.TokenError, SyntaxError, IndentationError) as exc:
        return 2, {"error": f"tokenize failed: {exc}"}
    orig_lines = len(src.splitlines())
    new_lines = len(stripped.splitlines())
    orig_tok = round(len(src) / 4)
    new_tok = round(len(stripped) / 4)
    payload = {"path": str(path),
               "orig_lines": orig_lines, "stripped_lines": new_lines,
               "orig_bytes": len(src.encode("utf-8")),
               "stripped_bytes": len(stripped.encode("utf-8")),
               "orig_tokens": orig_tok, "stripped_tokens": new_tok,
               "tokens_saved": orig_tok - new_tok, "written": False,
               "out": None}
    if out is None:
        return 0, payload
    try:
        Path(out).write_text(stripped, encoding="utf-8")
    except OSError as exc:
        return 2, {"error": f"cannot write: {exc}"}
    payload["written"] = True
    payload["out"] = str(out)
    return 0, payload
