"""Fixtures of the server tests: a repository with wiki pages, recorded runs, and a used repository with a
fresh session.
"""

import uuid

import pytest

from golestan_code_mcp import db, registry, schema
from golestan_code_mcp.server import app
from golestan_code_mcp.config import load
from golestan_code_mcp.memory import runs

from server.helpers import ready, wiki_repo


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    conn = ready()
    with conn:
        schema.migrate(conn)
        names = [wiki_repo(conn, tmp_path_factory.mktemp("w")), wiki_repo(conn, tmp_path_factory.mktemp("w"))]
        yield names
        with conn.cursor() as cur:
            cur.executemany("delete from ccctx_repos where name = :n", [{"n": n} for n in names])
        conn.commit()


@pytest.fixture
def recorded(real_recording, monkeypatch):
    """(conn, newest run id before the test). Runs are read back after memory.flush(). Records for real.

    Starts with no results returned: other tests' flask searches must not turn this test's reads into uses."""
    monkeypatch.setattr(app, "_returned", {})
    try:
        conn = db.connect(load())
    except Exception:
        pytest.skip("database unreachable")
    schema.migrate(conn)
    with conn.cursor() as cur:
        before = cur.execute("select nvl(max(id), 0) from ccctx_memory_runs").fetchone()[0]
    yield conn, before
    runs.flush()  # the runs these tests make are artifacts: never let them reach a repository's facts
    with conn.cursor() as cur:
        cur.execute("delete from ccctx_memory_runs where id > :b", b=before)
    conn.commit()
    conn.close()


@pytest.fixture(scope="module")
def used_repo(tmp_path_factory):
    """A `t-` repository with one wiki page, `pkg`, and its symbols post0 to post9 in src/pkg/core.py."""
    conn = ready()
    with conn:
        schema.migrate(conn)
        name = wiki_repo(conn, tmp_path_factory.mktemp("u"))
        yield name
        with conn.cursor() as cur:
            cur.execute("delete from ccctx_repos where name = :n", n=name)
        conn.commit()


@pytest.fixture
def fresh_session(recorded, used_repo, monkeypatch):
    """A new server session over the `t-` repository: no results returned yet, its own session id, no uses."""
    conn, _ = recorded
    monkeypatch.setattr(app, "_returned", {})
    monkeypatch.setattr(app, "SESSION", uuid.uuid4().hex)
    with conn.cursor() as cur:
        cur.execute("delete from ccctx_feedback where repo_id = :r", r=registry.repo_id(conn, used_repo))
    conn.commit()
    return used_repo
