"""Fixtures of the schema tests: a throwaway repository row."""

import uuid

import pytest

from schema.helpers import insert


@pytest.fixture
def repo_id(conn):
    """A throwaway repository, removed (with everything under it) after the test."""
    name = f"t-{uuid.uuid4().hex[:8]}"
    with conn.cursor() as cur:
        rid = insert(cur, "insert into ccctx_repos (name, path) values (:n, :p)", n=name, p=f"/tmp/{name}")
    conn.commit()
    yield rid
    with conn.cursor() as cur:
        cur.execute("delete from ccctx_repos where id = :i", i=rid)
    conn.commit()
