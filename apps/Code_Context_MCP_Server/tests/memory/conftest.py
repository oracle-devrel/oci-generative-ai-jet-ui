"""Fixtures of the memory tests: a connection that needs the model, and a fresh indexed repository."""

import pytest

from golestan_code_mcp.memory import store
from golestan_code_mcp.search import model

from memory.helpers import make_repo


@pytest.fixture(scope="module")
def ready(conn):
    try:
        model.require_model(conn)
    except model.ModelError:
        pytest.skip("embedding model not loaded: run `ccctx model load`")
    yield conn
    with conn.cursor() as cur:
        names = [r[0] for r in cur.execute("select name from ccctx_repos where name like 't-%'")]
    mem = store.client(conn)
    for name in names:
        mem.delete_user(name, cascade=True)
    with conn.cursor() as cur:
        cur.execute("delete from ccctx_repos where name like 't-%'")
    conn.commit()


@pytest.fixture
def repo(ready, tmp_path):
    """(name, root) of a fresh indexed repository with no memory yet."""
    root = tmp_path / "repo"
    return make_repo(ready, root), root
