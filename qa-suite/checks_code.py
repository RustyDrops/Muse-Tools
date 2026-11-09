"""Code checker: runs a target's own pytest/unittest and its repo-configured linter.

FAIL lists test names plus the first failure lines per test (by path);
the full log always goes to a file on disk, never into chat output.
Uses the tools-venv python for pytest (system python3 has no pytest).
Never calls any model; never invents a new linter dependency.
"""

import configparser
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS_VENV_PYTHON = "/home/hatch/workspace/tools-venv/bin/python"


def _repo_root(start):
    """Nearest ancestor dir holding a repo/test-config marker."""
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent
    markers = ("pyproject.toml", "setup.cfg", "tox.ini", "setup.py",
               ".flake8", "ruff.toml", "pytest.ini", ".git")
    for d in [p, *p.parents]:
        if any((d / m).exists() for m in markers):
            return d
    return p


def _configured_linter(root):
    """Return ('ruff'|'flake8'|None): only what the target repo configures."""
    root = Path(root)
    if (root / "ruff.toml").exists():
        return "ruff"
    for name in ("pyproject.toml", "setup.cfg", "tox.ini", ".flake8"):
        f = root / name
        if not f.exists():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        if name == "pyproject.toml":
            if "[tool.ruff" in text or "[tool.flake8" in text:
                return "ruff" if "[tool.ruff" in text else "flake8"
        else:
            try:
                cfg = configparser.ConfigParser()
                cfg.read_string(text)
                if cfg.has_section("flake8"):
                    return "flake8"
            except configparser.Error:
                pass
            if "[tool.ruff" in text or "[tool .ruff" in text:
                return "ruff"
    return None


def _run(cmd, cwd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=600, cwd=str(cwd))
    except FileNotFoundError as exc:
        return {"error": f"runner not found: {exc}"}
    except subprocess.TimeoutExpired:
        return {"error": f"timed out: {' '.join(cmd)}"}
    return {"returncode": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr}


def _first_failure_lines(output, limit=6):
    """First few failing/assert lines; never the whole log."""
    lines = []
    for line in output.splitlines():
        s = line.strip()
        if (s.startswith("FAILED") or s.startswith("E  ")
                or "AssertionError" in s or s.startswith("assert ")):
            lines.append(line.rstrip()[:300])
        if len(lines) >= limit:
            break
    return lines


def _parse_pytest_failures(output):
    """Test node ids from pytest short-summary + failure lines."""
    failures = []
    in_summary = False
    for line in output.splitlines():
        if "short test summary info" in line:
            in_summary = True
            continue
        if in_summary:
            m = re.match(r"FAILED\s+(\S+)(?:\s+-\s+(.*))?", line.strip())
            if m:
                failures.append({"test": m.group(1),
                                 "reason": (m.group(2) or "")[:300]})
            elif line.strip() == "" or line.startswith("="):
                if "passed" in line or "failed" in line:
                    break
    return failures


def check_code_file(path, log_dir=None):
    """Run the target's own pytest on path plus the repo-configured linter.

    Returns a verdict dict with pass/failures/measurements/log_path.
    {"error": ...} when the check itself cannot run (exit 2 upstream).
    """
    target = Path(path)
    if not target.exists():
        return {"pass": False, "error": f"target not found: {path}",
                "failures": [], "log_path": None}
    root = _repo_root(target)
    log_path = Path(log_dir) if log_dir else Path(tempfile.gettempdir())
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / "qa_code_check.log"

    failures, measurements = [], {}
    log_chunks = [f"$ {' '.join([TOOLS_VENV_PYTHON, '-m', 'pytest', str(target), '-q'])}"]
    res = _run([TOOLS_VENV_PYTHON, "-m", "pytest", str(target), "-q"], root)
    if "error" in res:
        return {"pass": False, "error": res["error"],
                "failures": [], "log_path": None}
    log_chunks += [res["stdout"], res["stderr"]]
    pytest_ok = res["returncode"] == 0
    measurements["pytest_returncode"] = res["returncode"]
    if not pytest_ok:
        for f in _parse_pytest_failures(res["stdout"] + "\n" + res["stderr"]):
            f["lines"] = _first_failure_lines(res["stdout"])
            f["path"] = str(target)
            failures.append(f)
        if not failures:
            failures.append({"test": str(target), "path": str(target),
                             "reason": f"pytest exit {res['returncode']}",
                             "lines": _first_failure_lines(
                                 res["stdout"] + "\n" + res["stderr"])})
    # Syntax gate: even a collection error gets a precise location.
    syn = _run([sys.executable, "-m", "py_compile", str(target)], root)
    measurements["py_compile_ok"] = syn.get("returncode") == 0
    if syn.get("returncode") != 0 and "error" not in syn:
        failures.append({"test": f"{target}::compile", "path": str(target),
                         "reason": "py_compile failed",
                         "lines": _first_failure_lines(
                             syn.get("stderr", ""))})

    linter = _configured_linter(root)
    measurements["linter"] = linter or "none-configured"
    if linter and shutil.which(linter):
        lres = _run([linter, "check" if linter == "ruff" else "--count",
                     str(target)], root)
        if "error" not in lres and lres["returncode"] != 0:
            failures.append({"test": f"{target}::lint", "path": str(target),
                             "reason": f"{linter} reported issues",
                             "lines": _first_failure_lines(
                                 lres["stdout"] + "\n" + lres["stderr"])})
    elif linter:
        measurements["linter_note"] = (f"{linter} configured but not on PATH; "
                                       "lint skipped, not passed")

    log_file.write_text("\n".join(log_chunks), encoding="utf-8")
    verdict = {"pass": not failures, "failures": failures,
               "measurements": measurements, "log_path": str(log_file)}
    return verdict
