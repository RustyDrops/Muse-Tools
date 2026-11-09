"""Table-driven tests for the deterministic model router."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_router import pick, load_rules

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTER = os.path.join(HERE, "model_router.py")

CASES = [
    # (task_type, size, complexity, low_failed, expected_model, expected_effort)
    ("draft", "s", "routine", False, "gpt-6-luna", "low"),
    ("draft", "m", "routine", False, "gpt-6-luna", "low"),
    ("draft", "s", "routine", True, "gpt-6-luna", "medium"),
    ("draft", "m", "hard", False, "gpt-6-luna", "medium"),
    ("planning", "l", "routine", False, "wonder-muse-code", "planning"),
    ("grilling", "m", "routine", False, "spark-muse-code", "medium"),
    ("implementing", "m", "routine", False, "spark-muse-code", "medium"),
    ("file-tool", "s", "routine", False, "spark-muse-code", "medium"),
    ("final-qa", "l", "hard", False, "spark-muse-code", "high"),
    ("lint", "s", "routine", False, "script", "none"),
    ("test-run", "s", "routine", False, "script", "none"),
    ("file-exists", "s", "routine", False, "script", "none"),
    ("format-check", "s", "routine", False, "script", "none"),
]


@pytest.mark.parametrize(
    "task_type,size,complexity,low_failed,exp_model,exp_effort", CASES
)
def test_rule_cases(task_type, size, complexity, low_failed, exp_model, exp_effort):
    got = pick(task_type, size, complexity, low_failed)
    assert got["model"] == exp_model
    assert got["effort"] == exp_effort
    assert isinstance(got["reason"], str) and got["reason"]
    assert "est_cost_usd" in got


@pytest.mark.parametrize("trivial", ["lint", "test-run", "file-exists",
                                     "format-check", "trivial-check"])
def test_trivial_never_wonder(trivial):
    got = pick(trivial, "s", "routine")
    assert got["model"] != "wonder-muse-code"
    assert got["model"] == "script"
    assert got["est_cost_usd"] == 0.0


def test_default_table_has_no_terra_or_gemini():
    rules = load_rules()
    blob = json.dumps(rules["rules"])
    assert "terra" not in blob.lower()
    assert "gemini" not in blob.lower()


def test_deny_reasons():
    assert pick("terra", "m", "routine")["reason"] == "backup-only"
    assert pick("gemini", "m", "routine")["reason"] == "retired-reliability"


def _write(path, obj):
    with open(path, "w") as f:
        f.write(json.dumps(obj) + "\n")


def _tracker_summary(path, calls=1, cost_usd=0.0012):
    summary = {"calls": calls, "openai_budget_usd": 5.0,
               "openai": {"calls": calls, "prompt_tokens": 25000,
                          "completion_tokens": 13000, "cost_usd": cost_usd},
               "gemini": {"calls": 0, "prompt_tokens": 0,
                          "completion_tokens": 0, "cost_usd": 0.0}}
    with open(path, "w") as f:
        json.dump(summary, f)


def test_reconcile_fills_actual_keeps_estimate(tmp_path):
    log = str(tmp_path / "router_log.jsonl")
    _write(log, {"model": "gpt-6-luna", "effort": "low",
                 "reason": "routine small draft — Luna low",
                 "est_cost_usd": 0.001, "actual_cost_usd": None,
                 "logged_at": "2026-11-08T00:00:00+00:00"})
    summary = str(tmp_path / "tracker_summary.json")
    _tracker_summary(summary, calls=1, cost_usd=0.0012)
    out = subprocess.run(
        [sys.executable, ROUTER, "reconcile",
         "--tracker-summary", summary, "--log", log],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    with open(log) as f:
        (row,) = [json.loads(line) for line in f if line.strip()]
    assert row["actual_cost_usd"] == pytest.approx(0.0012)
    assert row["est_cost_usd"] == 0.001


def test_reconcile_never_overwrites_estimate(tmp_path):
    log = str(tmp_path / "router_log.jsonl")
    _write(log, {"model": "gpt-6-luna", "effort": "low",
                 "reason": "routine small draft — Luna low",
                 "est_cost_usd": 0.001, "actual_cost_usd": 0.0009,
                 "logged_at": "2026-11-08T00:00:00+00:00"})
    with open(log, "a") as f:
        f.write(json.dumps({"model": "gpt-6-luna", "effort": "medium",
                            "reason": "hard complexity — Luna medium",
                            "est_cost_usd": 0.003, "actual_cost_usd": None,
                            "logged_at": "2026-11-08T00:01:00+00:00"}) + "\n")
    with open(log, "a") as f:
        f.write(json.dumps({"model": "script", "effort": "none",
                            "reason": "trivial check — deterministic $0 script",
                            "est_cost_usd": 0.0, "actual_cost_usd": None,
                            "logged_at": "2026-11-08T00:02:00+00:00"}) + "\n")
    summary = str(tmp_path / "tracker_summary.json")
    _tracker_summary(summary, calls=2, cost_usd=0.0049)
    out = subprocess.run(
        [sys.executable, ROUTER, "reconcile",
         "--tracker-summary", summary, "--log", log],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    with open(log) as f:
        rows = [json.loads(line) for line in f if line.strip()]
    assert [r["est_cost_usd"] for r in rows] == [0.001, 0.003, 0.0]
    assert rows[0]["actual_cost_usd"] == pytest.approx(0.0009)
    assert rows[1]["actual_cost_usd"] == pytest.approx(0.004)
    assert rows[2]["actual_cost_usd"] is None


def test_reconcile_drift_exits_2_without_writing(tmp_path):
    log = str(tmp_path / "router_log.jsonl")
    _write(log, {"model": "gpt-6-luna", "effort": "low",
                 "reason": "routine small draft — Luna low",
                 "est_cost_usd": 0.001, "actual_cost_usd": None,
                 "logged_at": "2026-11-08T00:00:00+00:00"})
    with open(log, "rb") as f:
        before = f.read()
    bad = str(tmp_path / "tracker_summary.json")
    with open(bad, "w") as f:
        json.dump({"calls": 1, "gemini": {"calls": 0}}, f)
    out = subprocess.run(
        [sys.executable, ROUTER, "reconcile",
         "--tracker-summary", bad, "--log", log],
        capture_output=True, text=True,
    )
    assert out.returncode == 2
    assert "tracker-format-drift" in out.stderr
    with open(log, "rb") as f:
        assert f.read() == before


def test_cli_dry_run_writes_log(tmp_path=None):
    log = os.path.join(HERE, "router_log.jsonl")
    before = os.path.getsize(log) if os.path.exists(log) else 0
    out = subprocess.run(
        [sys.executable, ROUTER, "route", "--task-type", "draft",
         "--size", "s", "--complexity", "routine", "--dry-run"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(out.stdout)
    assert data == {"model": "gpt-6-luna", "effort": "low",
                    "reason": data["reason"],
                    "est_cost_usd": data["est_cost_usd"]}
    assert data["model"] == "gpt-6-luna" and data["effort"] == "low"
    assert os.path.getsize(log) > before
