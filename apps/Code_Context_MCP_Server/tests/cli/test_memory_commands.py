"""memory list, consolidate and facts; feedback list, add and reset."""

import re
import uuid

import pytest

from golestan_code_mcp import db, registry
from golestan_code_mcp.cli import entry
from golestan_code_mcp.config import load
from golestan_code_mcp.search import feedback as search_feedback

from cli.helpers import run


def test_memory_list_newest_first(remembered, capsys):
    code, out, _ = run(capsys, "memory", "list", "--repo", remembered)
    rows = out.splitlines()
    assert code == 0 and rows[0].split() == ["RUN", "WHEN", "TOOL", "QUESTION", "CLIENT", "STATUS", "RESULTS", "TOP"]
    tools = [line.split()[3] for line in rows[1:]]
    assert tools == ["get_symbol", "read_wiki", "find_callers", "search_code"]
    assert "no symbol named 'nope'" in rows[1] and "unavailable" in rows[1]
    assert "flask/json src/flask/json" in rows[2] and " - " in rows[2]  # a page's TOP, and no question
    assert "Flask.go app.py:88" in rows[3] and rows[3].count(" - ") >= 1  # a call line's TOP, and no client
    assert "url_for src/h.py:188-246" in rows[4] and "test-client 9.9" in rows[4]


def test_memory_list_limit_and_empty(remembered, capsys, tmp_path):
    code, out, _ = run(capsys, "memory", "list", "--repo", remembered, "--limit", "1")
    assert code == 0 and len(out.splitlines()) == 2
    other = f"t-{uuid.uuid4().hex[:8]}"
    run(capsys, "repo", "add", str(tmp_path / "x"), "--name", other) if (tmp_path / "x").mkdir() is None else None
    assert run(capsys, "memory", "list", "--repo", other)[1].strip() == "no runs recorded"


def test_memory_list_refusals(live, capsys):
    code, _, err = run(capsys, "memory", "list", "--repo", "t-nowhere")
    assert code == 1 and "no repository named 't-nowhere'" in err
    with pytest.raises(SystemExit) as exit_:
        entry.main(["memory", "list", "--limit", "0"])
    assert exit_.value.code == 2


def test_memory_list_shows_used_of_returned(remembered, capsys):
    from golestan_code_mcp.search import feedback as search_feedback

    with db.connect(load()) as conn, conn.cursor() as cur:
        rid = registry.repo_id(conn, remembered)
        search = cur.execute("""select max(r.id) from ccctx_memory_runs r join ccctx_memory_run_repos l
                                 on l.run_id = r.id where l.repo_id = :r and r.tool = 'search_code'""",
                             r=rid).fetchone()[0]
        search_feedback.write_use(cur, {"repo_id": rid, "path": "src/h.py", "name": "url_for", "kind": "function",
                                 "how": "cited", "client": "t", "session": uuid.uuid4().hex, "run_id": search})
        conn.commit()
    code, out, _ = run(capsys, "memory", "list", "--repo", remembered)
    rows = {line.split()[3]: line for line in out.splitlines()[1:]}
    assert code == 0 and " 1/1 " in rows["search_code"]
    assert not re.search(r" \d+/\d+ ", rows["find_callers"])  # the plain count otherwise


def test_memory_consolidate_line_and_rerun(distilled, capsys):
    n, _, _ = distilled
    code, out, _ = run(capsys, "memory", "consolidate", "--repo", n)
    assert code == 0
    assert re.fullmatch(rf"{n}: 3 runs read, 2 created, 1 merged, 0 weakened, 0 stale, 0 re-asked in \d+\.\ds"
                        rf" \(template/1\)", out.strip())
    code, out, _ = run(capsys, "memory", "consolidate", "--repo", n)
    assert re.fullmatch(rf"{n}: 0 runs read, 0 created, 0 merged, 0 weakened, 0 stale, 0 re-asked in \d+\.\ds"
                        rf" \(template/1\)", out.strip())


def test_memory_facts_table(distilled, capsys):
    n, first, second = distilled
    run(capsys, "memory", "consolidate", "--repo", n)
    code, out, _ = run(capsys, "memory", "facts", "--repo", n)
    rows = out.splitlines()
    assert code == 0
    assert rows[0].split() == ["FACT", "REPO", "SUBJECT", "CONFIDENCE", "STATE", "DISTILLER", "RUNS", "TEXT"]
    cells = [line.split() for line in rows[1:]]
    assert [c[2] for c in cells] == [first, second]  # 0.750 before 0.500
    assert [c[3] for c in cells] == ["0.750", "0.500"] and all(len(c[0]) == 8 for c in cells)
    assert cells[0][6].count(",") == 1 and cells[0][6].split(",") == sorted(cells[0][6].split(","), key=int)
    assert all(len(line.split("template/1", 1)[1].split(None, 1)[1]) <= 125 for line in rows[1:])


def test_memory_facts_empty_and_refusals(live, capsys, tmp_path):
    n = f"t-{uuid.uuid4().hex[:8]}"
    run(capsys, "repo", "add", str(tmp_path), "--name", n)
    assert run(capsys, "memory", "facts", "--repo", n)[1].strip() == "no facts"
    for cmd in ("facts", "consolidate"):
        code, _, err = run(capsys, "memory", cmd, "--repo", "t-nowhere")
        assert code == 1 and "no repository named 't-nowhere'" in err


def test_feedback_add_then_list(ingested, capsys):
    n, _ = ingested
    code, out, _ = run(capsys, "feedback", "add", "a", "--repo", n, "--count", "3", "--days-ago", "30")
    assert code == 0 and out.strip() == f"recorded 3 uses of a (app.py) in {n}, dated 30 days ago"
    assert run(capsys, "feedback", "add", "B.c", "--repo", n, "--path", "app.py")[1].strip() == (
        f"recorded 1 use of B.c (app.py) in {n}, dated 0 days ago")
    code, out, _ = run(capsys, "feedback", "list", "--repo", n)
    header, first, second = out.splitlines()
    assert code == 0 and header.split() == ["KIND", "NAME", "PATH", "USES", "WEIGHT", "BOOST", "LAST", "USED", "INDEXED"]
    assert first.split()[:6] == ["function", "a", "app.py", "3", "1.50", "+6%"] and first.split()[-1] == "yes"
    assert second.split()[:6] == ["method", "B.c", "app.py", "1", "1.00", "+4%"]
    assert re.search(r" \d{4}-\d\d-\d\d \d\d:\d\d:\d\d ", first)


def test_feedback_list_empty_and_unknown(ingested, capsys):
    n, _ = ingested
    assert run(capsys, "feedback", "list", "--repo", n)[1].strip() == f"no feedback recorded for {n}"
    code, _, err = run(capsys, "feedback", "list", "--repo", "t-nowhere")
    assert code == 1 and "no repository named 't-nowhere'" in err


def test_feedback_add_refusals(ingested, capsys, monkeypatch):
    n, _ = ingested
    code, _, err = run(capsys, "feedback", "add", "zz_nothing", "--repo", n)
    assert code == 1 and err.startswith("error: not found: no indexed symbol or page named 'zz_nothing'")
    monkeypatch.setattr(search_feedback, "add", lambda *a, **k: (_ for _ in ()).throw(
        ValueError("'a' is at several paths; pass --path:\nx.py\ny.py")))
    code, _, err = run(capsys, "feedback", "add", "a", "--repo", n)
    assert code == 1 and err == "error: 'a' is at several paths; pass --path:\nx.py\ny.py\n"


@pytest.mark.parametrize("argv", [["--days-ago", "-1"], ["--count", "0"], ["--count", "100001"], ["--count", "x"]])
def test_feedback_add_bad_numbers_exit_2(capsys, argv):
    with pytest.raises(SystemExit) as exit_:
        entry.main(["feedback", "add", "a", "--repo", "flask", *argv])
    assert exit_.value.code == 2


def test_feedback_reset(ingested, capsys, monkeypatch):
    n, _ = ingested
    run(capsys, "feedback", "add", "a", "--repo", n, "--count", "2")
    assert run(capsys, "feedback", "reset", "--repo", n)[1].strip() == f"deleted 2 uses in {n}"
    assert run(capsys, "feedback", "list", "--repo", n)[1].strip() == f"no feedback recorded for {n}"
    seen = []
    monkeypatch.setattr(search_feedback, "reset", lambda conn, repo: seen.append(repo) or 7)
    assert run(capsys, "feedback", "reset", "--all")[1].strip() == "deleted 7 uses in all repositories"
    assert seen == [None]


@pytest.mark.parametrize("argv", [[], ["--repo", "flask", "--all"]])
def test_feedback_reset_needs_exactly_one_scope(capsys, argv):
    with pytest.raises(SystemExit) as exit_:
        entry.main(["feedback", "reset", *argv])
    assert exit_.value.code == 2
