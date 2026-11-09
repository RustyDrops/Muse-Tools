"""Pytest suite for the deterministic toolbox. Stdlib only (pytest runner)."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOLBOX = HERE / "toolbox.py"
FIX = HERE / "fixtures"

sys.path.insert(0, str(HERE))
import draft_tools
import python_tools
import validate_tools


def run_cli(*argv):
    proc = subprocess.run([sys.executable, str(TOOLBOX), *argv],
                          capture_output=True, text=True, timeout=60)
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        payload = {"_raw": proc.stdout}
    return proc.returncode, payload


# ---------- peek ----------

def test_peek_exact_lines():
    code, out = draft_tools.peek(str(FIX / "sample.md"), 1, 3)
    assert code == 0
    assert [l["n"] for l in out["lines"]] == [1, 2, 3]
    assert out["lines"][0]["text"] == "# Title"


def test_peek_missing_and_range():
    assert draft_tools.peek(str(FIX / "nope.md"), 1, 2)[0] == 2
    assert draft_tools.peek(str(FIX / "sample.md"), 0, 2)[0] == 2
    assert draft_tools.peek(str(FIX / "sample.md"), 5, 4)[0] == 2
    assert draft_tools.peek(str(FIX / "sample.md"), 1, 999)[0] == 2


def test_peek_cap_100(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("\n".join(f"line{i}" for i in range(150)),
                 encoding="utf-8")
    code, out = draft_tools.peek(str(f), 1, 150)
    assert code == 0
    assert len(out["lines"]) == 100
    assert out["truncated"] is True


def test_peek_line_truncation(tmp_path):
    f = tmp_path / "wide.txt"
    f.write_text("x" * 500, encoding="utf-8")
    _, out = draft_tools.peek(str(f), 1, 1)
    assert len(out["lines"][0]["text"]) == 300


# ---------- grep ----------

def test_grep_found_and_missed():
    code, out = draft_tools.grep(str(FIX / "sample.md"), "Section")
    assert code == 0 and out["found"] and out["count"] == 2
    code, out = draft_tools.grep(str(FIX / "sample.md"), "absent-zzz")
    assert code == 1 and out["found"] is False


def test_grep_regex_and_ignore_case():
    code, out = draft_tools.grep(str(FIX / "sample.md"), "^## ",
                                 regex=True)
    assert code == 0 and out["count"] == 2
    code, out = draft_tools.grep(str(FIX / "sample.md"), "section",
                                 ignore_case=True)
    assert code == 0 and out["found"] is True
    assert draft_tools.grep(str(FIX / "sample.md"), "([", regex=True)[0] == 2


def test_grep_cap_50(tmp_path):
    f = tmp_path / "many.txt"
    f.write_text("\n".join("hit %d" % i for i in range(80)),
                 encoding="utf-8")
    code, out = draft_tools.grep(str(f), "hit")
    assert code == 0 and len(out["matches"]) == 50


def test_grep_dir_rejected():
    code, out = run_cli("grep", "--dir", "x", "y")
    assert code == 2


# ---------- diff ----------

def test_diff_identical_and_changed(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("x\ny\n", encoding="utf-8")
    b.write_text("x\ny\n", encoding="utf-8")
    code, out = draft_tools.diff(str(a), str(b))
    assert code == 0 and out["identical"] is True
    b.write_text("x\nz\n", encoding="utf-8")
    code, out = draft_tools.diff(str(a), str(b))
    assert code == 1 and out["identical"] is False
    assert any(l.startswith(("+", "-", "@@")) for l in out["diff"])
    assert draft_tools.diff(str(a), str(tmp_path / "missing"))[0] == 2


def test_diff_cap_200(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("\n".join("a%d" % i for i in range(300)),
                 encoding="utf-8")
    b.write_text("\n".join("b%d" % i for i in range(300)),
                 encoding="utf-8")
    _, out = draft_tools.diff(str(a), str(b))
    assert len(out["diff"]) == 200 and out["truncated"] is True


# ---------- stats ----------

def test_stats_matches_sha256():
    code, out = draft_tools.stats(str(FIX / "sample.md"))
    assert code == 0
    raw = (FIX / "sample.md").read_bytes()
    assert out["sha256"] == hashlib.sha256(raw).hexdigest()
    assert out["bytes"] == len(raw)
    assert out["est_tokens"] == round(len(raw.decode()) / 4)
    assert "content" not in out and "text" not in out
    assert draft_tools.stats(str(FIX / "nope"))[0] == 2


# ---------- outline ----------

def test_outline_good():
    code, out = python_tools.outline(str(FIX / "good.py"))
    assert code == 0
    names = [s["name"] for s in out["symbols"]]
    assert "Greeter" in names and "add" in names
    assert "Greeter.hello" in names
    sig = next(s["signature"] for s in out["symbols"]
               if s["name"] == "add")
    assert "b=2" in sig
    doc = next(s["doc"] for s in out["symbols"] if s["name"] == "Greeter")
    assert doc == "Greets people politely."  # first line only
    assert python_tools.outline(str(FIX / "bad.py"))[0] == 2


# ---------- strip ----------

def test_strip_counts_and_write(tmp_path):
    code, out = draft_tools.strip(str(FIX / "good.py"))
    assert code == 0 and out["tokens_saved"] > 0
    assert out["stripped_bytes"] < out["orig_bytes"]
    assert out["stripped_lines"] <= out["orig_lines"]
    dest = tmp_path / "stripped.py"
    code, out = draft_tools.strip(str(FIX / "good.py"), out=str(dest))
    assert code == 0 and out["written"] is True and dest.exists()
    assert draft_tools.strip(str(FIX / "bad.py"))[0] == 2


def test_strip_never_prints_code(capsys):
    code, out = draft_tools.strip(str(FIX / "good.py"))
    assert code == 0
    assert "Greets people" not in json.dumps(out)


# ---------- toc ----------

def test_toc_headings():
    code, out = draft_tools.toc(str(FIX / "sample.md"))
    assert code == 0 and out["count"] == 4
    assert out["headings"][0] == {"level": 1, "text": "Title", "offset": 0}
    assert all(h["offset"] >= 0 for h in out["headings"])


def test_toc_cap_200(tmp_path):
    f = tmp_path / "big.md"
    f.write_text("".join("# H%d\n\n" % i for i in range(250)),
                 encoding="utf-8")
    _, out = draft_tools.toc(str(f))
    assert len(out["headings"]) == 200


# ---------- syntax ----------

def test_syntax_good_and_bad():
    assert python_tools.syntax(str(FIX / "good.py")) == (
        0, {"path": str(FIX / "good.py"), "pass": True})
    code, out = python_tools.syntax(str(FIX / "bad.py"))
    assert code == 1 and out["pass"] is False
    assert out["line"] == 1 and isinstance(out["col"], int)
    assert python_tools.syntax(str(FIX / "nope.py"))[0] == 2


# ---------- imports ----------

def test_imports_found_missing():
    code, out = python_tools.imports(str(FIX / "with_imports.py"))
    assert code == 1
    assert "os" in out["found"]
    assert "definitely_missing_module_xyz" in out["missing"]
    code, out = python_tools.imports(str(FIX / "good.py"))
    assert code == 0 and out["missing"] == []


# ---------- validate ----------

def test_validate_pass_and_fail(tmp_path):
    code, out = validate_tools.validate(str(FIX / "sample.json"),
                                        str(FIX / "schema.json"))
    assert code == 0 and out["pass"] is True
    bad = tmp_path / "bad.json"
    bad.write_text('{"name": 5}', encoding="utf-8")
    code, out = validate_tools.validate(str(bad), str(FIX / "schema.json"))
    assert code == 1 and out["pass"] is False
    assert 1 <= len(out["errors"]) <= 10
    assert all("path" in e for e in out["errors"])
    assert validate_tools.validate(str(tmp_path / "x"), str(FIX /
                                                             "schema.json"))[0] == 2


def test_validate_error_cap_10(tmp_path):
    schema = {"type": "object",
              "required": ["f%d" % i for i in range(30)]}
    s = tmp_path / "s.json"
    d = tmp_path / "d.json"
    s.write_text(json.dumps(schema), encoding="utf-8")
    d.write_text("{}", encoding="utf-8")
    _, out = validate_tools.validate(str(d), str(s))
    assert len(out["errors"]) == 10


# ---------- scaffold / diagram ----------

def test_scaffold_dry_run_and_write(tmp_path):
    code, out = python_tools.scaffold(str(FIX / "good.py"))
    assert code == 0 and out["dry_run"] is True
    assert out["classes"] == 1 and out["functions"] == 1
    dest = tmp_path / "good_test.py"
    code, out = python_tools.scaffold(str(FIX / "good.py"), out=str(dest))
    assert code == 0 and dest.exists()
    assert python_tools.scaffold(str(FIX / "good.py"),
                                 out=str(dest))[0] == 2  # no overwrite
    code, _ = python_tools.scaffold(str(FIX / "good.py"), out=str(dest),
                                    force=True)
    assert code == 0


def test_diagram_dry_run_and_write(tmp_path):
    code, out = python_tools.diagram(str(FIX / "good.py"))
    assert code == 0 and out["dry_run"] is True and out["classes"] == 1
    dest = tmp_path / "d.mmd"
    code, out = python_tools.diagram(str(FIX / "good.py"), out=str(dest))
    assert code == 0 and "classDiagram" in dest.read_text(encoding="utf-8")


# ---------- canary ----------

def test_canary_ok_truncates_to_6():
    code, out = python_tools.canary(str(FIX / "canary_ok.py"), timeout=10)
    assert code == 0 and out["returncode"] == 0
    assert len(out["lines"]) == 6 and out["truncated"] is True


def test_canary_fail_and_refusals(tmp_path):
    code, out = python_tools.canary(str(FIX / "canary_fail.py"), timeout=10)
    assert code == 1 and out["returncode"] == 3
    outside = tmp_path / "evil.py"
    outside.write_text("print(1)", encoding="utf-8")
    # tmp_path is outside ~/workspace only when /tmp is used; skip if inside
    import python_tools as pt
    ws = pt.WORKSPACE.resolve()
    resolved_out = outside.resolve()
    if resolved_out != ws and ws not in resolved_out.parents:
        assert python_tools.canary(str(outside))[0] == 2
    assert python_tools.canary(__file__.replace(".py", ".txt"))[0] == 2


# ---------- check-url ----------

def test_check_url_rejects_non_http():
    code, out = validate_tools.check_url("ftp://example.com/x")
    assert code == 2 and out["error"]


def test_check_url_success_mocked(monkeypatch):
    class FakeResp:
        status = 200

        def geturl(self):
            return "https://example.com/"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeOpener:
        def open(self, req, timeout=None):
            assert timeout == 3
            return FakeResp()

    monkeypatch.setattr("urllib.request.build_opener",
                        lambda *a, **k: FakeOpener())
    code, out = validate_tools.check_url("https://example.com")
    assert code == 0 and out["status"] == 200
    assert out["elapsed_ms"] >= 0


def test_check_url_timeout_is_clean_exit_2(monkeypatch):
    import urllib.error as ue

    class FakeOpener:
        def open(self, req, timeout=None):
            raise ue.URLError("timed out")

    monkeypatch.setattr("urllib.request.build_opener",
                        lambda *a, **k: FakeOpener())
    code, out = validate_tools.check_url("https://example.com")
    assert code == 2 and out["error"] and out["status"] is None


# ---------- health ----------

def test_health_never_exit_2():
    code, out = validate_tools.health()
    assert code == 0
    assert set(out) >= {"mem_kb", "loadavg", "disk", "cgroup_max"}


# ---------- estimate-cost ----------

def test_estimate_cost_null_without_rates():
    code, out = validate_tools.estimate_cost(str(FIX / "sample.md"))
    assert code == 0 and out["cost_usd"] is None and out["note"]
    assert out["input_tokens"] == round(
        len((FIX / "sample.md").read_text(encoding="utf-8")) / 4)


def test_estimate_cost_with_rates(tmp_path):
    r = tmp_path / "rates.json"
    r.write_text(json.dumps({"input_per_1k": 1.0, "output_per_1k": 2.0}),
                 encoding="utf-8")
    code, out = validate_tools.estimate_cost(str(FIX / "sample.md"),
                                             output_tokens=1000, rates=str(r))
    assert code == 0
    assert out["cost_usd"] == round(out["input_tokens"] / 1000 * 1.0
                                   + 1000 / 1000 * 2.0, 6)


# ---------- CLI ----------

def test_cli_one_json_object():
    code, payload = run_cli("stats", str(FIX / "sample.md"))
    assert code == 0 and payload["command"] == "stats" and payload["ok"] is True


def test_cli_exit_codes():
    assert run_cli("grep", str(FIX / "sample.md"), "absent-zzz")[0] == 1
    assert run_cli("peek", str(FIX / "nope"), "1", "2")[0] == 2
    assert run_cli("bogus")[0] == 2
