"""Consolidation: merging, confidence, weakening, contradictions, idempotence and scale."""

import time
import json

from golestan_code_mcp import db
from golestan_code_mcp.memory import consolidate
from golestan_code_mcp.memory import distill
from golestan_code_mcp.memory import recall
from golestan_code_mcp.memory import runs as memory_runs
from golestan_code_mcp.config import load
from golestan_code_mcp import registry

from memory.helpers import ask, facts_of, hit, synthetic


# --- consolidation (T015) ---


def test_near_identical_questions_merge_into_one_fact(ready, repo):
    name, _ = repo
    ask("search_code", query="where is spin_widget defined", repo=name)
    ask("search_code", query="where's spin_widget defined?", repo=name)
    ask("get_symbol", name="spin_widget", repo=name)
    ask("find_callers", name="spin_widget", repo=name)
    [c] = consolidate.consolidate(ready, name)
    assert (c.runs, c.created, c.merged, c.weakened, c.stale) == (4, 1, 3, 0, 0)
    facts = facts_of(ready, name)
    assert list(facts) == ["spin_widget"]
    f = facts["spin_widget"]
    assert f.confidence == 0.938 and f.state == "fresh" and len(f.runs) == 4
    assert f.questions[:2] == ["spin_widget", "where's spin_widget defined?"]
    assert "where is spin_widget defined" in f.questions
    assert f.distiller == distill.TEMPLATE and f.consolidator == distill.CONSOLIDATOR
    assert f.text.startswith("`spin_widget` is a function in `pkg/widgets.py`.")
    assert "It is called by" in f.text and 'Asked as "spin_widget"' in f.text
    with ready.cursor() as cur:
        assert {r for (r,) in cur.execute("select id from ccctx_memory_runs where id in (select column_value from"
                                          " json_table(:j, '$[*]' columns (column_value number path '$')))",
                                          j=json.dumps(f.runs))} == set(f.runs)


def test_confidence_rises_with_agreeing_runs(ready, repo):
    name, _ = repo
    seen = []
    for question in ("spin one", "spin two", "spin three"):
        with db.connect(load()) as c:
            memory_runs.store_runs(c, [synthetic(name, "search_code", question, [hit(name, "spin_widget")])])
        consolidate.consolidate(ready, name)
        seen.append(facts_of(ready, name)["spin_widget"].confidence)
    assert seen == [0.5, 0.75, 0.875]


def test_a_wording_that_moves_weakens_the_old_fact_and_links_them(ready, repo):
    name, _ = repo
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [synthetic(name, "search_code", "Who turns it?", [hit(name, "spin_widget")]),
                              synthetic(name, "search_code", "spin widgets", [hit(name, "spin_widget")])])
    consolidate.consolidate(ready, name)
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [synthetic(name, "search_code", "who turns it", [hit(name, "turn_helper")])])

    def links():
        with ready.cursor() as cur:
            return cur.execute("select count(*) from ccctx_mem_memory_link").fetchone()[0]

    before = links()
    [c] = consolidate.consolidate(ready, name)
    facts = facts_of(ready, name)
    assert (c.created, c.weakened) == (1, 1)
    assert facts["spin_widget"].confidence == 0.375 and "Who turns it?" not in facts["spin_widget"].questions
    assert facts["turn_helper"].questions == ["who turns it"]
    assert links() == before + 1  # turn_helper's fact contradicts spin_widget's


def test_an_aspect_that_changes_value_is_a_contradiction(ready, repo):
    name, _ = repo
    callers = [{"kind": "function", "repo": name, "name": "use_widget", "path": "pkg/other.py", "line": 5,
                "callee": "spin_widget"}]
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [synthetic(name, "find_callers", "spin_widget", callers, {"name": "spin_widget"})])
    consolidate.consolidate(ready, name)
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [synthetic(name, "find_callers", "spin_widget", callers * 2, {"name": "spin_widget"})])
    [c] = consolidate.consolidate(ready, name)
    assert c.weakened == 1 and facts_of(ready, name)["spin_widget"].confidence == 0.375


def test_consolidation_is_idempotent_and_skips_counted_runs(ready, repo):
    name, _ = repo
    ask("get_symbol", name="spin_widget", repo=name)
    consolidate.consolidate(ready, name)
    before = {f.id: (f.text, f.confidence, f.runs) for f in recall.facts(ready, name)}
    [c] = consolidate.consolidate(ready, name)
    assert (c.runs, c.created, c.merged, c.weakened, c.stale, c.reasked) == (0, 0, 0, 0, 0, 0)
    with ready.cursor() as cur:  # a crash after the facts were written: the links read as unconsolidated again
        cur.execute("update ccctx_memory_run_repos set consolidated = false where repo_id = :r",
                    r=registry.repo_id(ready, name))
    ready.commit()
    [c] = consolidate.consolidate(ready, name)
    assert (c.runs, c.created, c.merged) == (1, 0, 0)
    assert {f.id: (f.text, f.confidence, f.runs) for f in recall.facts(ready, name)} == before


def test_two_consolidations_at_once_count_each_run_once(ready, repo):
    import threading
    name, _ = repo
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [synthetic(name, "search_code", f"q{i}", [hit(name, "spin_widget")]) for i in range(6)])
    errors = []

    def work():
        try:
            with db.connect(load()) as c:
                consolidate.consolidate(c, name)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=work) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    [f] = recall.facts(ready, name)
    assert len(f.runs) == 6 and f.confidence == round(1 - 0.5 ** 6, 3)


def test_consolidation_logs_counts_never_text(ready, repo, caplog):
    import logging
    name, _ = repo
    ask("search_code", query="where is spin_widget secretly", repo=name)
    with caplog.at_level(logging.INFO, logger="golestan_code_mcp.memory"):
        consolidate.consolidate(ready, name)
    [record] = [json.loads(r.getMessage()) for r in caplog.records if '"consolidate"' in r.getMessage()]
    assert set(record) == {"event", "repo", "runs", "created", "merged", "weakened", "stale", "reasked", "distillers",
                           "seconds"}
    assert "secretly" not in caplog.text


# --- scale (T036, SC-004) ---


def test_a_thousand_runs_consolidate_within_a_minute(ready, repo):
    name, _ = repo
    subjects = [("spin_widget", "function", "pkg/widgets.py"), ("turn_helper", "function", "pkg/widgets.py"),
                ("Widget", "class", "pkg/widgets.py"), ("Widget.run", "method", "pkg/widgets.py"),
                ("use_widget", "function", "pkg/other.py")]
    runs_ = [synthetic(name, "search_code", f"question {i}", [hit(name, s, p, k)])
             for i in range(1000) for s, k, p in [subjects[i % len(subjects)]]]
    with db.connect(load()) as c:
        memory_runs.store_runs(c, runs_)
    started = time.monotonic()
    [c] = consolidate.consolidate(ready, name)
    assert time.monotonic() - started < 60 and (c.runs, c.created) == (1000, 5)
    before = {f.id: (f.text, f.confidence, len(f.runs)) for f in recall.facts(ready, name)}
    [again] = consolidate.consolidate(ready, name)
    assert (again.runs, again.created, again.merged) == (0, 0, 0)
    assert {f.id: (f.text, f.confidence, len(f.runs)) for f in recall.facts(ready, name)} == before


def test_the_same_words_to_another_tool_are_not_a_contradiction(ready, repo):
    name, _ = repo
    defs = [hit(name, "Widget.run", kind="method")]
    callers = [{"kind": "method", "repo": name, "name": "Widget.run", "path": "pkg/widgets.py", "line": 17,
                "callee": "spin_widget"}]
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [synthetic(name, "get_symbol", "run", defs, {"name": "run"}),
                              synthetic(name, "find_callers", "run", callers, {"name": "run"})])
    [c] = consolidate.consolidate(ready, name)
    assert (c.created, c.weakened) == (2, 0)
    assert {s: f.confidence for s, f in facts_of(ready, name).items()} == {"Widget.run": 0.5, "spin_widget": 0.5}
