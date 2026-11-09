"""Python tools: syntax, outline, imports, scaffold, diagram, canary. Stdlib only."""

import ast
import importlib.util
import subprocess
import sys
import time
from pathlib import Path

MAX_SYMBOLS = 200
WORKSPACE = Path.home() / "workspace"


def _read(path):
    p = Path(path)
    if not p.is_file():
        return None, (2, {"error": f"file not found: {path}"})
    try:
        return p.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, (2, {"error": f"cannot read: {exc}"})


def syntax(path):
    """Thin ast.parse wrapper. 0 pass, 1 syntax fail, 2 tool error."""
    src, err = _read(path)
    if err:
        return err
    try:
        ast.parse(src)
    except SyntaxError as exc:
        return 1, {"path": str(path), "pass": False,
                   "line": exc.lineno, "col": exc.offset,
                   "message": exc.msg}
    return 0, {"path": str(path), "pass": True}


def _signature(args):
    parts = []
    pos = list(args.posonlyargs) if hasattr(args, "posonlyargs") else []
    plain = list(args.args)
    # defaults align to the tail of posonly+args
    all_pos = pos + plain
    ndef = len(args.defaults)
    defs = [None] * (len(all_pos) - ndef) + list(args.defaults)
    for a, d in zip(all_pos, defs):
        s = a.arg
        if a.annotation is not None:
            try:
                s += ": " + ast.unparse(a.annotation)
            except Exception:
                pass
        if d is not None:
            try:
                s += "=" + ast.unparse(d)
            except Exception:
                s += "=..."
        parts.append(s)
    if pos:
        parts.insert(len(pos), "/")
    if args.vararg is not None:
        parts.append("*" + args.vararg.arg)
    elif args.kwonlyargs:
        parts.append("*")
    for a, d in zip(args.kwonlyargs, args.kw_defaults):
        s = a.arg
        if d is not None:
            try:
                s += "=" + ast.unparse(d)
            except Exception:
                s += "=..."
        parts.append(s)
    if args.kwarg is not None:
        parts.append("**" + args.kwarg.arg)
    return "(" + ", ".join(parts) + ")"


def outline(path):
    """AST classes/functions with signatures + docstring first lines."""
    src, err = _read(path)
    if err:
        return err
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return 2, {"error": f"syntax error: {exc.msg}",
                   "line": exc.lineno, "col": exc.offset}
    syms = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node)
            syms.append({
                "kind": "async_function" if isinstance(
                    node, ast.AsyncFunctionDef) else "function",
                "name": node.name,
                "signature": node.name + _signature(node.args),
                "doc": doc.splitlines()[0][:300] if doc else None,
                "line": node.lineno})
        elif isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node)
            bases = []
            for b in node.bases:
                try:
                    bases.append(ast.unparse(b))
                except Exception:
                    bases.append("?")
            syms.append({"kind": "class", "name": node.name,
                         "bases": bases,
                         "doc": doc.splitlines()[0][:300] if doc else None,
                         "line": node.lineno})
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sdoc = ast.get_docstring(sub)
                    syms.append({
                        "kind": "method", "name": node.name + "." + sub.name,
                        "signature": sub.name + _signature(sub.args),
                        "doc": sdoc.splitlines()[0][:300] if sdoc else None,
                        "line": sub.lineno})
    capped = len(syms) >= MAX_SYMBOLS
    syms = syms[:MAX_SYMBOLS]
    return 0, {"path": str(path), "symbols": syms,
               "count": len(syms), "capped": capped}


def imports(path):
    """AST imports resolved via importlib.util.find_spec (no execution)."""
    src, err = _read(path)
    if err:
        return err
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return 2, {"error": f"syntax error: {exc.msg}",
                   "line": exc.lineno, "col": exc.offset}
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module.split(".")[0])
    seen, found, missing = set(), [], []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError, AttributeError):
            spec = None
        (found if spec is not None else missing).append(name)
    code = 0 if not missing else 1
    return code, {"path": str(path), "found": sorted(found),
                 "missing": sorted(missing)}


def scaffold(path, out=None, force=False):
    """Write a unittest skeleton to out. Dry-run without out."""
    src, err = _read(path)
    if err:
        return err
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return 2, {"error": f"syntax error: {exc.msg}",
                   "line": exc.lineno, "col": exc.offset}
    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    funcs = [n.name for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    methods = {}
    for n in tree.body:
        if isinstance(n, ast.ClassDef):
            methods[n.name] = [
                s.name for s in n.body
                if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))]
    stem = Path(path).stem
    if out is None:
        return 0, {"path": str(path), "classes": len(classes),
                   "functions": len(funcs), "dry_run": True, "out": None,
                   "class_names": classes, "function_names": funcs}
    dest = Path(out)
    if dest.exists() and not force:
        return 2, {"error": f"refuses to overwrite: {out} (use --force)"}
    import_list = classes + [f for f in funcs if f.isidentifier()]
    lines = ["\"\"\"Tests for %s. Generated skeleton — fill in TODOs.\"\"\"",
             "import unittest", ""]
    lines[0] = lines[0] % Path(path).name
    if import_list:
        lines.append("from %s import %s" % (stem, ", ".join(import_list)))
        lines.append("")
    if not classes and not funcs:
        lines += ["class TestModule(unittest.TestCase):",
                  "    def test_placeholder(self):",
                  "        raise NotImplementedError(\"TODO\")", ""]
    for c in classes:
        lines.append("class Test%s(unittest.TestCase):" % c)
        ms = methods.get(c, [])
        if not ms:
            lines += ["    def test_placeholder(self):",
                      "        raise NotImplementedError(\"TODO\")"]
        for m in ms:
            if m.startswith("_") and m != "__init__":
                continue
            lines += ["    def test_%s(self):" % m,
                      "        raise NotImplementedError(\"TODO\")"]
        lines.append("")
    for f in funcs:
        if f.startswith("_"):
            continue
        lines += ["class Test%s(unittest.TestCase):" % f,
                  "    def test_%s(self):" % f,
                  "        raise NotImplementedError(\"TODO\")", ""]
    lines += ["if __name__ == \"__main__\":", "    unittest.main()", ""]
    try:
        dest.write_text("\n".join(lines), encoding="utf-8")
    except OSError as exc:
        return 2, {"error": f"cannot write: {exc}"}
    return 0, {"path": str(path), "out": str(dest),
               "classes": len(classes), "functions": len(funcs),
               "dry_run": False}


def diagram(path, out=None):
    """Mermaid classDiagram from outline. Dry-run without out."""
    src, err = _read(path)
    if err:
        return err
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return 2, {"error": f"syntax error: {exc.msg}",
                   "line": exc.lineno, "col": exc.offset}
    klasses = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    lines = ["classDiagram"]
    arrows = 0
    for k in klasses:
        lines.append("    class %s" % k.name)
        for sub in k.body:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lines.append("    %s : %s()" % (k.name, sub.name))
        for b in k.bases:
            try:
                bname = ast.unparse(b)
            except Exception:
                continue
            if bname.isidentifier():
                lines.append("    %s --|> %s" % (k.name, bname))
                arrows += 1
    payload = {"path": str(path), "classes": len(klasses),
               "arrows": arrows, "dry_run": out is None, "out": None}
    if out is None:
        payload["mermaid_lines"] = len(lines)
        return 0, payload
    try:
        Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as exc:
        return 2, {"error": f"cannot write: {exc}"}
    payload["out"] = str(out)
    return 0, payload


def canary(path, timeout=10):
    """Run a workspace-only .py file in a subprocess with a timeout.

    Returns returncode + first 6 output lines only.
    """
    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        return 2, {"error": "timeout must be an integer"}
    p = Path(path)
    if p.suffix != ".py":
        return 2, {"error": f"canary runs .py files only: {path}"}
    try:
        resolved = p.resolve()
    except OSError as exc:
        return 2, {"error": f"cannot resolve: {exc}"}
    try:
        ws = WORKSPACE.resolve()
    except OSError:
        ws = WORKSPACE
    if resolved != ws and ws not in resolved.parents:
        return 2, {"error": f"refused: outside workspace: {path}"}
    if not resolved.is_file():
        return 2, {"error": f"file not found: {path}"}
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(resolved)], capture_output=True,
            text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 2, {"path": str(path), "error": f"timed out after {timeout}s",
                   "timeout_s": timeout}
    except OSError as exc:
        return 2, {"error": f"cannot run: {exc}"}
    elapsed = int((time.monotonic() - t0) * 1000)
    combined = ((proc.stdout or "") + (proc.stderr or "")).splitlines()
    out = [l[:300] for l in combined[:6]]
    code = 0 if proc.returncode == 0 else 1
    return code, {"path": str(path), "returncode": proc.returncode,
                  "elapsed_ms": elapsed, "lines": out,
                  "truncated": len(combined) > 6}
