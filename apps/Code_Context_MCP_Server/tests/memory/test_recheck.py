"""Re-checking facts after an ingest: removed, moved and edited code, and consolidation on every ingest."""

from golestan_code_mcp.memory import consolidate
from golestan_code_mcp.memory import recall
from golestan_code_mcp import registry
from golestan_code_mcp.indexing import ingest as indexing_ingest

from memory.helpers import ENV, OTHER, WIDGETS, ask, change, facts_of, run_count, seed


def test_removed_code_makes_its_fact_stale_and_halves_it(ready, repo):
    name, root = repo
    seed(ready, name, [("turn_helper", "what turns", 1)])
    summary = change(ready, name, root, {"pkg/widgets.py": WIDGETS.replace("return turn_helper(w)", "return w")
                                         .replace("def turn_helper(w):\n    return w\n\n\n", "")})
    assert summary.memory.stale == 1
    f = facts_of(ready, name)["turn_helper"]
    assert (f.state, f.stale_reason, f.confidence) == ("stale", "`turn_helper` was removed", 0.25)


def test_moved_code_is_repointed_without_a_re_ask(ready, repo):
    name, root = repo
    seed(ready, name, [("use_widget", "who uses widgets", 1)])
    summary = change(ready, name, root, {"pkg/moved.py": OTHER}, remove=["pkg/other.py"])
    assert (summary.memory.stale, summary.memory.reasked) == (0, 0)
    f = facts_of(ready, name)["use_widget"]
    assert (f.state, f.sources[0]["path"]) == ("fresh", "pkg/moved.py") and "`pkg/moved.py`" in f.text


def test_edited_code_answered_the_same_way_stays_fresh(ready, repo):
    name, root = repo
    ask("get_symbol", name="spin_widget", repo=name)
    consolidate.consolidate(ready, name)
    before = run_count(ready)
    edited = WIDGETS.replace('    """Spin a widget once."""\n', '    """Spin a widget once."""\n    w = w or 0\n')
    summary = change(ready, name, root, {"pkg/widgets.py": edited})
    assert (summary.memory.stale, summary.memory.reasked) == (0, 1)
    assert run_count(ready) == before  # a re-ask is not a run
    f = facts_of(ready, name)["spin_widget"]
    assert f.state == "fresh" and f.sources[0]["end_line"] == 7 and f.confidence == 0.5


def test_edited_code_answered_by_other_code_goes_stale(ready, repo):
    name, root = repo
    ask("get_symbol", name="spin_widget", repo=name)
    consolidate.consolidate(ready, name)
    renamed = WIDGETS.replace("def spin_widget(w):", "def spin_widget_old(w):").replace(
        "return spin_widget(self)", "return spin_widget_old(self)")
    summary = change(ready, name, root, {"pkg/widgets.py": renamed,
                                         "pkg/other.py": OTHER.replace("from pkg.widgets import spin_widget\n", "")
                                         + "\n\ndef spin_widget(w):\n    return 2\n"})
    assert summary.memory.stale == 1 and summary.memory.reasked == 1
    f = next(f for f in recall.facts(ready, name, 50) if f.sources[0]["name"] == "spin_widget" and f.state == "stale")
    assert f.stale_reason == 're-asked "spin_widget": now answered by `spin_widget` in `pkg/other.py`'
    assert f.confidence == 0.25


def test_stale_facts_wait_for_a_run_and_consolidation_is_idempotent(ready, repo):
    name, root = repo
    seed(ready, name, [("turn_helper", "what turns", 1)])
    change(ready, name, root, {"pkg/widgets.py": WIDGETS.replace("def turn_helper(w):", "def turn_helper2(w):")})
    [c] = consolidate.consolidate(ready, name)
    assert (c.stale, c.reasked, c.runs) == (0, 0, 0)  # stale facts are not re-checked
    change(ready, name, root, {"pkg/widgets.py": WIDGETS})
    assert facts_of(ready, name)["turn_helper"].state == "stale"  # code is back, but no run confirmed it
    seed(ready, name, [("turn_helper", "what turns now", 1)])
    assert facts_of(ready, name)["turn_helper"].state == "fresh"


def test_every_ingestion_consolidates_even_when_current(ready, repo):
    name, _ = repo
    ask("get_symbol", name="spin_widget", repo=name)
    summary = indexing_ingest.ingest(ready, name, ENV)
    assert summary.mode == "current" and summary.memory.runs == 1 and summary.memory.created == 1
    again = indexing_ingest.ingest(ready, name, ENV)
    assert (again.memory.runs, again.memory.created, again.memory.stale, again.memory.reasked) == (0, 0, 0, 0)


def test_a_consolidation_failure_never_undoes_the_ingestion(ready, repo, monkeypatch):
    name, root = repo

    def broken(*_, **__):
        raise RuntimeError("memory down")

    monkeypatch.setattr(consolidate, "consolidate", broken)
    summary = change(ready, name, root, {"pkg/new.py": "def brand_new():\n    return 1\n"})
    assert summary.memory == "memory down"
    with ready.cursor() as cur:
        assert cur.execute("select count(*) from ccctx_symbols s join ccctx_files f on f.id = s.file_id where"
                           " f.repo_id = :r and s.name = 'brand_new'", r=registry.repo_id(ready, name)).fetchone()[0]
