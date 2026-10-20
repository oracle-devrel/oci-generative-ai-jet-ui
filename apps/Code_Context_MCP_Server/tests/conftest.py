"""Shared test setup: the database connection, and keeping the suite's tool calls out of the real repositories' memory.

- `conn`: a migrated connection to the configured database, one per test file. A file whose tests need the
  embedding model says so with `pytestmark = pytest.mark.needs_model`, and `conn` then requires it too. A missing
  database or model skips the file's tests, never fails them. At the file's end the `t-` repositories it left are
  removed.
- Plain helpers (git, files) are in support.py, imported by the files that use them.
"""

import pytest

from golestan_code_mcp import db, schema
from golestan_code_mcp.config import load
from golestan_code_mcp.memory import runs as memory_runs
from golestan_code_mcp.search import model


@pytest.fixture(scope="module")
def conn(request):
    try:
        conn = db.connect(load())
    except Exception as e:  # config missing or database down: skip, never fail
        pytest.skip(f"database unreachable: {type(e).__name__}")
    schema.migrate(conn)
    if request.node.get_closest_marker("needs_model"):
        try:
            model.require_model(conn)
        except model.ModelError:
            conn.close()
            pytest.skip("embedding model not loaded: run `ccctx model load`")
    yield conn
    with conn.cursor() as cur:
        cur.execute("delete from ccctx_repos where name like 't-%'")
    conn.commit()
    conn.close()


@pytest.fixture
def real_recording():
    """Request this to record every run, including those about real repositories (flask, gin)."""


@pytest.fixture(autouse=True)
def _keep_real_repositories_out_of_memory(request, monkeypatch):
    """Many tests call tools against flask and gin. Their runs would be consolidated into those repositories' facts
    (a test's synthetic caller count, 40 timing calls), so they are dropped, and so are their uses, which would boost
    flask results in later searches. Throwaway `t-` repositories still record."""
    if "real_recording" in request.fixturenames:
        return
    record = memory_runs.record

    def real(item):
        return [item["use"]["repo"]] if "use" in item else item["repos"]

    monkeypatch.setattr(memory_runs, "record",
                        lambda item: None if any(not r.startswith("t-") for r in real(item)) else record(item))
