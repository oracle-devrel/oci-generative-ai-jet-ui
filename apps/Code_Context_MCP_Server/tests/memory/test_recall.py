"""Recall, facts in search, and forgetting."""

import subprocess
import sys
import time

import pytest

from golestan_code_mcp import db
from golestan_code_mcp.memory import consolidate
from golestan_code_mcp.memory import recall
from golestan_code_mcp.memory import runs as memory_runs
from golestan_code_mcp.memory import store
from golestan_code_mcp.config import load
from golestan_code_mcp.search import query

from memory.helpers import facts_of, hit, make_repo, seed, synthetic


def test_recall_without_topic_is_fresh_then_confident(ready, repo):
    name, _ = repo
    seed(ready, name, [("spin_widget", "spin", 1), ("turn_helper", "turn", 2), ("use_widget", "use", 3)])
    r = recall.recall(ready, name)
    assert [f.subject for f in r.facts] == ["use_widget", "turn_helper", "spin_widget"] and r.total == 3
    assert [f.sources[0]["path"] for f in r.facts] == ["pkg/other.py", "pkg/widgets.py", "pkg/widgets.py"]
    assert r.runs and len(r.runs) <= 10 and all(x.tool != "recall" for x in r.runs)


def test_recall_by_topic_puts_the_related_fact_first(ready, repo):
    name, _ = repo
    seed(ready, name, [("turn_helper", "how is a widget turned", 3), ("spin_widget", "how do widgets spin", 1)])
    assert recall.recall(ready, name, "spinning widgets").facts[0].subject == "spin_widget"
    assert recall.recall(ready, name, None).facts[0].subject == "turn_helper"


def test_recall_without_a_repository_covers_every_one(ready, repo, tmp_path):
    name, _ = repo
    other = make_repo(ready, tmp_path / "o")
    seed(ready, name, [("spin_widget", "spin", 1)])
    seed(ready, other, [("turn_helper", "turn", 1)])
    found = {(f.repo, f.subject) for f in recall.recall(ready, None, limit=50).facts}
    assert {(name, "spin_widget"), (other, "turn_helper")} <= found
    assert {(name, "spin_widget"), (other, "turn_helper")} <= {
        (f.repo, f.subject) for f in recall.recall(ready, None, "spin turn", limit=50).facts}


def test_recall_size_does_not_grow_with_the_log(ready, repo):
    name, _ = repo
    seed(ready, name, [("spin_widget", "spin", 1)])
    small = recall.recall(ready, name)
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [synthetic(name, "search_code", f"q{i}", []) for i in range(2000)])
    started = time.monotonic()
    big = recall.recall(ready, name)
    assert time.monotonic() - started < 2  # SC-007
    assert (len(big.facts), len(big.runs), big.total) == (len(small.facts), 10, small.total)


def test_recall_unknown_repository(ready):
    with pytest.raises(ValueError, match="no repository named 't-nowhere'"):
        recall.recall(ready, "t-nowhere")


# --- facts in search (T026, FR-021) ---


def test_fresh_facts_are_search_hits_below_definitions(ready, repo):
    name, _ = repo
    seed(ready, name, [("spin_widget", "how do widgets spin", 2)])
    hits = query.search(ready, "spin_widget", [name])
    assert hits[0].kind == "function" and hits[0].name == "spin_widget"  # the definition stays first
    [fact] = [h for h in hits if h.kind == "fact"]
    assert (fact.name, fact.path, fact.language, fact.state) == ("spin_widget", "pkg/widgets.py", "python", "fresh")
    assert fact.start_line and fact.snippet.startswith("`spin_widget` is a function") and fact.keyword_rank is None
    assert len(query.search(ready, "how do widgets spin", [name], limit=2)) == 2  # facts count toward the limit


def test_fact_hits_follow_filters_and_skip_stale(ready, repo, tmp_path):
    name, _ = repo
    other = make_repo(ready, tmp_path / "o")
    seed(ready, name, [("spin_widget", "how do widgets spin", 1)])
    assert not [h for h in query.search(ready, "how do widgets spin", [other]) if h.kind == "fact"]
    assert not [h for h in query.search(ready, "how do widgets spin", [name], language="go") if h.kind == "fact"]
    mem = store.client(ready)
    [rec] = mem.list_memories(user_id=name, agent_id=store.AGENT, limit=None)
    from oracleagentmemory.apis.records import RecordStatus
    mem.update_memory(rec.id, metadata=rec.metadata | {"state": "stale"}, status=RecordStatus.INVALID)
    assert not [h for h in query.search(ready, "how do widgets spin", [name]) if h.kind == "fact"]


def test_search_without_facts_never_loads_the_package(ready, repo):
    name, _ = repo
    code = ("import sys; from golestan_code_mcp import db; from golestan_code_mcp.search import query; "
            "from golestan_code_mcp.config import load; "
            f"c = db.connect(load()); query.search(c, 'spin', ['{name}']); print('oracleagentmemory' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
    assert out.endswith("False")


def test_a_fact_hit_run_confirms_its_fact(ready, repo):
    name, _ = repo
    seed(ready, name, [("spin_widget", "how do widgets spin", 1)])
    run = synthetic(name, "search_code", "what spins", [{"kind": "fact", "repo": name, "name": "spin_widget",
                                                         "path": "pkg/widgets.py", "start_line": 4, "end_line": 6}])
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [run])
    consolidate.consolidate(ready, name)
    assert facts_of(ready, name)["spin_widget"].confidence == 0.75


def test_forget_removes_only_that_repository(ready, repo, tmp_path):
    name, _ = repo
    other = make_repo(ready, tmp_path / "o")
    seed(ready, name, [("spin_widget", "spin", 1)])
    seed(ready, other, [("spin_widget", "spin", 1)])
    recall.forget(ready, name)
    assert recall.facts(ready, name) == [] and len(recall.facts(ready, other)) == 1


def test_runs_only_a_removed_repository_held_go_with_it(ready, repo, tmp_path):
    name, _ = repo
    other = make_repo(ready, tmp_path / "o")
    shared = synthetic(name, "search_code", "spin", [hit(name, "spin_widget")])
    shared["repos"] = [name, other]
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [shared, synthetic(name, "search_code", "only here", [hit(name, "spin_widget")])])
    recall.forget(ready, name)
    with ready.cursor() as cur:
        cur.execute("delete from ccctx_repos where name = :n", n=name)
    ready.commit()
    consolidate.consolidate(ready, other)
    with ready.cursor() as cur:
        assert cur.execute("select count(*) from ccctx_memory_runs where question = 'only here'").fetchone()[0] == 0
        assert cur.execute("select count(*) from ccctx_memory_runs r join ccctx_memory_run_repos l on"
                           " l.run_id = r.id join ccctx_repos p on p.id = l.repo_id where p.name = :o",
                           o=other).fetchone()[0] == 1
