"""Fixtures of the wiki tests: a repository with its wiki built, and a fresh one per test."""

import pytest

from wiki.helpers import make_repo


@pytest.fixture(scope="module")
def built(conn, tmp_path_factory):
    """A repository whose wiki is built once and never changed: read-only tests share it."""
    return make_repo(conn, tmp_path_factory.mktemp("w") / "repo")


@pytest.fixture
def fresh(conn, tmp_path):
    """(name, root) of a repository with a built wiki that a test may change."""
    root = tmp_path / "repo"
    return make_repo(conn, root), root
