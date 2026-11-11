"""Tests for improve_tools (stamp / drift / branch-scope / rejected)."""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import improve_tools


def _git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t",
                    "-c", "user.name=t", *args],
                   capture_output=True, text=True, check=True, timeout=30)


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "orders_api.py").write_text("def list_orders():\n    pass\n")
    (repo / "orders_view.py").write_text("import orders_api\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "base")
    return repo


def test_stamp_and_drift_clean(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello\n")
    stamp = tmp_path / "s.json"
    code, out = improve_tools.stamp(str(stamp), [str(f)])
    assert code == 0 and out["files"] == 1
    code, out = improve_tools.drift(str(stamp))
    assert code == 0 and out["status"] == "clean" and out["unchanged"] == 1


def test_stamp_refuses_overwrite(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    stamp = tmp_path / "s.json"
    assert improve_tools.stamp(str(stamp), [str(f)])[0] == 0
    assert improve_tools.stamp(str(stamp), [str(f)])[0] == 2
    assert improve_tools.stamp(str(stamp), [str(f)], force=True)[0] == 0


def test_drift_detects_content_and_missing(tmp_path):
    f = tmp_path / "a.txt"
    g = tmp_path / "b.txt"
    f.write_text("one")
    g.write_text("two")
    stamp = tmp_path / "s.json"
    improve_tools.stamp(str(stamp), [str(f), str(g)])
    f.write_text("changed")
    g.unlink()
    code, out = improve_tools.drift(str(stamp))
    assert code == 1 and out["status"] == "drift"
    reasons = {c["path"]: c["reason"] for c in out["changed"]}
    assert "content" in reasons[str(f.resolve())]
    assert reasons[str(g.resolve())] == "missing"


def test_drift_records_git_sha(tmp_path):
    repo = _repo(tmp_path)
    stamp = tmp_path / "s.json"
    code, out = improve_tools.stamp(str(stamp),
                                    [str(repo / "orders_api.py")])
    assert code == 0 and out["git_repos"] == [str(repo)]


def test_branch_scope_no_commits_ahead(tmp_path):
    repo = _repo(tmp_path)
    code, out = improve_tools.branch_scope(str(repo))
    assert code == 0 and out["status"] == "no-commits-ahead"


def test_branch_scope_finds_changes_and_importers(tmp_path):
    repo = _repo(tmp_path)
    _git(repo, "checkout", "-b", "feature")
    (repo / "orders_api.py").write_text(
        "def list_orders():\n    return []\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "change api")
    code, out = improve_tools.branch_scope(str(repo), base="main")
    assert code == 0 and out["status"] == "ok"
    assert out["changed_files"] == ["orders_api.py"]
    assert out["importers"]["orders_api.py"] == ["orders_view.py"]


def test_branch_scope_not_a_repo(tmp_path):
    code, _ = improve_tools.branch_scope(str(tmp_path))
    assert code == 2


def test_rejected_add_list_check(tmp_path):
    store = str(tmp_path / "rej.jsonl")
    code, _ = improve_tools.rejected(
        "add", item="https_proxy env var SSRF finding",
        reason="by-design standard proxy convention", store=store)
    assert code == 0
    code, out = improve_tools.rejected("list", store=store)
    assert code == 0 and out["count"] == 1
    code, out = improve_tools.rejected(
        "check", item="proxy environment variable SSRF report",
        store=store)
    assert code == 0 and out["previously_rejected"] is True
    code, out = improve_tools.rejected(
        "check", item="unrelated database indexing problem", store=store)
    assert code == 1 and out["previously_rejected"] is False


def test_rejected_project_filter(tmp_path):
    store = str(tmp_path / "rej.jsonl")
    improve_tools.rejected("add", item="alpha beta gamma", reason="no",
                           project="one", store=store)
    improve_tools.rejected("add", item="alpha beta delta", reason="no",
                           project="two", store=store)
    code, out = improve_tools.rejected("list", project="two", store=store)
    assert code == 0 and out["count"] == 1
