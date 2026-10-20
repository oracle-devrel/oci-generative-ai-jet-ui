"""callers, calls, impact and eval: their tables, flags, depths and refusals."""

import pytest

from golestan_code_mcp.cli import entry
from golestan_code_mcp.graph import queries
from golestan_code_mcp.search import evaluation

from cli.helpers import run


def test_graph_tables(graphed, capsys):
    n = graphed
    code, out, _ = run(capsys, "callers", "a", "--repo", n)
    header, *rows = out.splitlines()
    assert code == 0 and header.split() == ["CALLER", "KIND", "REPO", "PATH", "LINE", "CALLS"]
    assert [r.split() for r in rows] == [["b", "function", n, "g.py", "6", "a"], ["(module)", "file", n, "g.py", "9", "a"]]

    code, out, _ = run(capsys, "calls", "b", "--repo", n)
    header, *rows = out.splitlines()
    assert code == 0 and header.split() == ["FROM", "LINE", "CALLEE", "KIND", "REPO", "PATH", "LINES"]
    assert [r.split() for r in rows] == [["b", "6", "a", "function", n, "g.py", "1-2"]]

    code, out, _ = run(capsys, "impact", "a", "--repo", n, "--depth", "1")
    header, *rows = out.splitlines()
    assert code == 0 and header.split() == ["HOPS", "NAME", "KIND", "REPO", "PATH", "LINES"]
    assert [r.split() for r in rows] == [["1", "b", "function", n, "g.py", "5-6"]]


@pytest.mark.parametrize(("argv", "message"), [
    (["callers", "b"], "no callers of 'b'"),
    (["calls", "a"], "'a' calls no indexed symbols"),
    (["impact", "b"], "nothing calls 'b'"),
])
def test_graph_empty_results(graphed, capsys, argv, message):
    code, out, _ = run(capsys, *argv, "--repo", graphed)
    assert code == 0 and out.strip() == message


@pytest.mark.parametrize("command", ["callers", "calls", "impact"])
def test_graph_unknown_name_exits_1(graphed, capsys, command):
    code, out, err = run(capsys, command, "zzz_missing", "--repo", graphed)
    assert code == 1 and out == "" and "error: no symbol named 'zzz_missing'" in err


def test_graph_repo_flags_and_default_depth(live, capsys, monkeypatch):
    seen = []
    monkeypatch.setattr(queries, "callers", lambda conn, name, repos=None: seen.append(("callers", repos)) or [])
    monkeypatch.setattr(queries, "calls", lambda conn, name, repos=None: seen.append(("calls", repos)) or [])
    monkeypatch.setattr(queries, "impact", lambda conn, name, depth=3, repos=None: seen.append((depth, repos)) or [])
    run(capsys, "callers", "x", "--repo", "t-a", "--repo", "t-a,t-b")
    run(capsys, "calls", "x")
    run(capsys, "impact", "x", "--repo", "t-a")
    run(capsys, "impact", "x", "--depth", "5")
    assert seen == [("callers", ["t-a", "t-b"]), ("calls", None), (3, ["t-a"]), (5, None)]


@pytest.mark.parametrize("depth", ["0", "6", "-1", "x", "2.5"])
def test_bad_depth_refused_before_connecting(capsys, monkeypatch, depth):
    monkeypatch.setenv("DB_PORT", "1")
    code, out, err = run(capsys, "impact", "url_for", "--depth", depth)
    assert code == 1 and out == "" and err.strip() == "error: depth must be between 1 and 5"


@pytest.mark.parametrize("command", ["callers", "calls", "impact"])
def test_graph_empty_name_refused_before_connecting(capsys, monkeypatch, command):
    monkeypatch.setenv("DB_PORT", "1")
    code, out, err = run(capsys, command, " ")
    assert code == 1 and out == "" and err.strip() == "error: the name is empty"


# --- ccctx eval (specs/011-usage-feedback contracts/cli.md) -----------------------------------------------------


def test_eval_prints_questions_recall_and_misses(live, capsys, monkeypatch, tmp_path):
    gold = tmp_path / "gold.json"
    gold.write_text("{}", encoding="utf-8")
    seen = []
    monkeypatch.setattr(evaluation, "load_gold", lambda path, conn: seen.append(path) or ["q"] * 3)
    monkeypatch.setattr(evaluation, "evaluate", lambda conn, g, with_feedback, limit: seen.append((with_feedback, limit))
                        or evaluation.Evaluation(3, 2, ["how does gin bind a JSON request body?"]))
    code, out, _ = run(capsys, "eval", "--gold", str(gold))
    assert code == 0 and out.splitlines() == ["Questions: 3", "recall@10: 0.67 (2/3)",
                                              "missed: how does gin bind a JSON request body?"]
    code, out, _ = run(capsys, "eval", "--gold", str(gold), "--with-feedback", "--limit", "5")
    assert out.splitlines()[1] == "recall@5: 0.67 (2/3)"
    assert seen == [str(gold), (False, 10), str(gold), (True, 5)]


def test_eval_gold_errors_exit_1(live, capsys, tmp_path):
    code, _, err = run(capsys, "eval", "--gold", str(tmp_path / "none.json"))
    assert code == 1 and err.startswith("error: gold file not found: ")
    (tmp_path / "bad.json").write_text('{"version": 1, "questions": [{"question": "x", "paths": []}]}')
    code, _, err = run(capsys, "eval", "--gold", str(tmp_path / "bad.json"))
    assert code == 1 and err.strip() == "error: gold file: question 1 has no paths"


@pytest.mark.parametrize("limit", ["0", "51", "x"])
def test_eval_bad_limit_exits_2(capsys, limit):
    with pytest.raises(SystemExit) as exit_:
        entry.main(["eval", "--gold", "gold.json", "--limit", limit])
    assert exit_.value.code == 2
