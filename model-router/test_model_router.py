"""Table-driven tests for the generic deterministic model router."""
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
    ("draft", "s", "routine", False, "light", "low"),
    ("draft", "m", "routine", False, "light", "low"),
    ("draft", "s", "routine", True, "standard", "medium"),
    ("draft", "m", "hard", False, "standard", "medium"),
    ("planning", "l", "routine", False, "planner", "planning"),
    ("grilling", "m", "routine", False, "worker", "medium"),
    ("implementing", "m", "routine", False, "worker", "medium"),
    ("file-tool", "s", "routine", False, "worker", "medium"),
    ("final-qa", "l", "hard", False, "worker", "high"),
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
def test_trivial_uses_script(trivial):
    got = pick(trivial, "s", "routine")
    assert got["model"] == "script"
    assert got["model"] != "planner"
    assert got["est_cost_usd"] == 0.0


def _parity_cases():
    with open(os.path.join(HERE, "parity_fixture.json")) as f:
        return json.load(f)["cases"]


@pytest.mark.parametrize("case", _parity_cases(),
                         ids=[f"case{i}" for i in range(len(_parity_cases()))])
def test_parity_with_before_refactor_fixture(case):
    """Decisions identical to pick() before the single-source refactor."""
    i = case["input"]
    got = pick(i["task_type"], i["size"], i["complexity"], i["low_failed"])
    assert got == case["expected"]


def test_models_are_generic_slots_only():
    rules = load_rules()
    allowed = {"light", "standard", "planner", "worker", "script"}
    assert rules["defaults"]["model"] in allowed
    for rule in rules["rules"]:
        assert rule["model"] in allowed, \
            f"non-generic model in rules: {rule['model']}"


def test_cli_dry_run_writes_log(tmp_path=None):
    log = os.path.join(HERE, "router_log.jsonl")
    before = os.path.getsize(log) if os.path.exists(log) else 0
    out = subprocess.run(
        [sys.executable, ROUTER, "route", "--task-type", "draft",
         "--size", "s", "--complexity", "routine", "--dry-run"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(out.stdout)
    assert data == {"model": "light", "effort": "low",
                    "reason": data["reason"],
                    "est_cost_usd": data["est_cost_usd"]}
    assert data["model"] == "light" and data["effort"] == "low"
    assert os.path.getsize(log) > before
