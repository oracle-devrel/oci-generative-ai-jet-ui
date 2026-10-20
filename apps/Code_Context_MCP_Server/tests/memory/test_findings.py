"""Findings: what one run says about its subject, per tool and per repository."""

import pytest

from golestan_code_mcp import db
from golestan_code_mcp.memory import findings
from golestan_code_mcp.memory import runs as memory_runs
from golestan_code_mcp.config import load
from golestan_code_mcp import registry
from golestan_code_mcp.wiki import build

from memory.helpers import FILES, ask, hit, make_repo, synthetic


# --- findings (T014) ---


def test_search_hit_finding_is_about_the_top_symbol(ready, repo):
    name, _ = repo
    ask("search_code", query="spin_widget", repo=name)
    with ready.cursor() as cur:
        [run] = findings.pending(cur, registry.repo_id(ready, name))
        f = findings.finding(cur, registry.repo_id(ready, name), name, run)
    assert f.subject_key == "symbol:pkg/widgets.py:spin_widget:function" and f.subject == "spin_widget"
    assert (f.aspect, f.tool, f.question, f.run_id) == ("defined", "search_code", "spin_widget", run["id"])
    assert f.refs[0]["role"] == "subject" and f.refs[0]["content_hash"]


@pytest.mark.parametrize(("tool", "arguments", "subject", "aspect"), [
    ("get_symbol", {"name": "spin_widget"}, "spin_widget", "defined"),
    ("find_callers", {"name": "spin_widget"}, "spin_widget", "callers"),
    ("find_callees", {"name": "spin_widget"}, "spin_widget", "callees"),
    ("impact_of", {"name": "spin_widget", "depth": 2}, "spin_widget", "impact"),
])
def test_graph_and_symbol_findings(ready, repo, tool, arguments, subject, aspect):
    name, _ = repo
    ask(tool, repo=name, **arguments)
    with ready.cursor() as cur:
        [run] = findings.pending(cur, registry.repo_id(ready, name))
        f = findings.finding(cur, registry.repo_id(ready, name), name, run)
    assert (f.subject, f.aspect, f.tool) == (subject, aspect, tool)
    if aspect in ("callers", "callees", "impact"):
        assert f.value["count"] >= 1 and f.value["names"]


def test_page_finding_from_read_wiki(ready, tmp_path):
    files = dict(FILES) | {f"pkg/m{i}.py": f"def f{i}():\n    return {i}\n" for i in range(10)}
    name = make_repo(ready, tmp_path / "w", files)
    build.build(ready, name)
    ask("read_wiki", page="pkg", repo=name)
    with ready.cursor() as cur:
        [run] = findings.pending(cur, registry.repo_id(ready, name))
        f = findings.finding(cur, registry.repo_id(ready, name), name, run)
    assert (f.subject_key, f.aspect, f.kind) == ("page:pkg", "module", "page") and f.value["summary"]


@pytest.mark.parametrize("make", [
    lambda n: synthetic(n, "search_code", "nothing", []),
    lambda n: synthetic(n, "list_repositories", None, [{"kind": "repository", "name": n}], {}),
    lambda n: synthetic(n, "read_wiki", None, [{"kind": "page", "repo": n, "name": "pkg", "state": "fresh"}], {}),
    lambda n: synthetic(n, "recall", None, [{"kind": "fact", "repo": n, "name": "spin_widget"}], {"repo": n}),
    lambda n: synthetic(n, "search_code", "gone", [hit(n, "no_such_symbol")]),
    lambda n: dict(synthetic(n, "search_code", "x", [hit(n, "spin_widget")]), status="unavailable"),
])
def test_runs_that_give_no_finding(ready, repo, make):
    name, _ = repo
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [make(name)])
    with ready.cursor() as cur:
        [run] = findings.pending(cur, registry.repo_id(ready, name))
        assert findings.finding(cur, registry.repo_id(ready, name), name, run) is None


def test_a_run_over_two_repositories_gives_each_its_own_top(ready, repo, tmp_path):
    name, _ = repo
    other = make_repo(ready, tmp_path / "o")
    run = synthetic(name, "search_code", "spin", [hit(other, "turn_helper"), hit(name, "spin_widget")], {"query": "spin"})
    run["repos"] = [name, other]
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [run])
    with ready.cursor() as cur:
        for repo_name, subject in ((name, "spin_widget"), (other, "turn_helper")):
            rid = registry.repo_id(ready, repo_name)
            [r] = findings.pending(cur, rid)
            assert findings.finding(cur, rid, repo_name, r).subject == subject
