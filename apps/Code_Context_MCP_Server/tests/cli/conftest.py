"""Fixtures of the ccctx tests: the database, the model, and ingested, graphed, wiki and remembered
repositories.
"""

import subprocess
import uuid

import pytest

from golestan_code_mcp import db
from golestan_code_mcp.search import model as search_model
from golestan_code_mcp.config import load
from golestan_code_mcp.memory import recall as memory_recall
from golestan_code_mcp.memory import runs

from cli.helpers import a_run, make_repo, make_wiki_repo, run, symbol_run


@pytest.fixture(scope="module")
def live():
    try:
        conn = db.connect(load())
    except Exception as e:  # config missing or database down: skip, never fail
        pytest.skip(f"database unreachable: {type(e).__name__}")
    yield
    with conn.cursor() as cur:
        cur.execute("delete from ccctx_repos where name like 't-%'")
    conn.commit()
    conn.close()


@pytest.fixture
def model(live):
    with db.connect(load()) as conn:
        try:
            search_model.require_model(conn)
        except (search_model.ModelError, Exception) as e:
            pytest.skip(f"embedding model not loaded: {type(e).__name__}")


@pytest.fixture
def ingested(model, capsys, tmp_path):
    n = f"t-{uuid.uuid4().hex[:8]}"
    run(capsys, "repo", "add", str(make_repo(tmp_path / "r")), "--name", n)
    code, out, err = run(capsys, "ingest", n)
    assert code == 0, err
    return n, out


# --- callers, calls, impact (007) ---------------------------------------------------------------------------


@pytest.fixture
def graphed(model, capsys, tmp_path):
    root = tmp_path / "g"
    root.mkdir()
    (root / "g.py").write_text("def a():\n    return 1\n\n\ndef b():\n    return a()\n\n\na()\n")
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root, check=True,
                       capture_output=True)
    n = f"t-{uuid.uuid4().hex[:8]}"
    run(capsys, "repo", "add", str(root), "--name", n)
    assert run(capsys, "ingest", n)[0] == 0
    return n


@pytest.fixture
def wikirepo(model, capsys, tmp_path):
    """An ingested repository with one qualifying directory, src/pkg (the page `pkg`), and its wiki built."""
    n = f"t-{uuid.uuid4().hex[:8]}"
    root = make_wiki_repo(tmp_path / "w")
    run(capsys, "repo", "add", str(root), "--name", n)
    assert run(capsys, "ingest", n)[0] == 0
    code, out, err = run(capsys, "wiki", "build", "--repo", n)
    assert code == 0, err
    return n, root, out, err


@pytest.fixture
def remembered(live, capsys, tmp_path):
    n = f"t-{uuid.uuid4().hex[:8]}"
    assert run(capsys, "repo", "add", str(tmp_path), "--name", n)[0] == 0
    with db.connect(load()) as conn:
        runs.store_runs(conn, [
            a_run("search_code", "where is url_for", n, [{"kind": "function", "repo": n, "name": "url_for",
                                                          "path": "src/h.py", "start_line": 188, "end_line": 246}]),
            a_run("find_callers", "url_for", n, [{"kind": "method", "repo": n, "name": "Flask.go", "path": "app.py",
                                                  "line": 88, "callee": "url_for"}], client=None),
            a_run("read_wiki", None, n, [{"kind": "page", "repo": n, "name": "flask/json", "path": "src/flask/json"}]),
            a_run("get_symbol", "nope", n, status="unavailable", reason="no symbol named 'nope'"),
        ])
    return n


@pytest.fixture
def distilled(ingested, capsys, monkeypatch):
    """An ingested repository with three runs about two of its symbols, not yet consolidated."""
    n, _ = ingested
    monkeypatch.delenv("CCCTX_MEMORY_MODEL", raising=False)
    with db.connect(load()) as conn:
        with conn.cursor() as cur:
            rows = cur.execute("select s.name, f.path, s.kind from ccctx_symbols s join ccctx_files f on"
                               " f.id = s.file_id join ccctx_repos r on r.id = f.repo_id where r.name = :n and"
                               " s.kind in ('function', 'method') order by s.kind, s.name", n=n).fetchall()
        (first, p1, k1), (second, p2, k2) = rows  # a (function), then B.c (method)
        runs.store_runs(conn, [symbol_run(n, "where is the first", first, p1, k1),
                                 symbol_run(n, "where's the first?", first, p1, k1),
                                 symbol_run(n, "and the second", second, p2, k2)])
    yield n, first, second
    with db.connect(load()) as conn:
        memory_recall.forget(conn, n)
