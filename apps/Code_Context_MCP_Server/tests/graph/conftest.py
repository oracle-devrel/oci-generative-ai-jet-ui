"""Fixtures of the graph tests: the ingested repositories, built once per test file that asks for them."""

import uuid

import pytest

from golestan_code_mcp import registry
from golestan_code_mcp.indexing import ingest as indexing_ingest

from graph.helpers import DEFS, ENV, EXT, GO, PY, language_repo, make


@pytest.fixture(scope="module")
def repos(conn, tmp_path_factory):
    names = []
    for files in (PY, GO):
        name = f"t-{uuid.uuid4().hex[:8]}"
        registry.add_repo(conn, make(tmp_path_factory.mktemp("g"), files), name)
        indexing_ingest.ingest(conn, name, ENV)
        names.append(name)
    return names


@pytest.fixture(scope="module")
def defs(conn, tmp_path_factory):
    name = f"t-{uuid.uuid4().hex[:8]}"
    registry.add_repo(conn, make(tmp_path_factory.mktemp("d"), DEFS), name)
    indexing_ingest.ingest(conn, name, {})  # the default file size limit, so big.py is indexed
    return name


@pytest.fixture(scope="module")
def ext(conn, tmp_path_factory):
    name = f"t-{uuid.uuid4().hex[:8]}"
    registry.add_repo(conn, make(tmp_path_factory.mktemp("x"), EXT), name)
    indexing_ingest.ingest(conn, name, ENV)
    return name


@pytest.fixture(scope="module")
def csharp(conn, tmp_path_factory):
    return language_repo(conn, tmp_path_factory.mktemp("cs") / "repo", "csharp")


@pytest.fixture(scope="module")
def us2(conn, tmp_path_factory):
    return language_repo(conn, tmp_path_factory.mktemp("us2") / "repo", "typescript", "tsx", "c", "cpp")


@pytest.fixture(scope="module")
def us4(conn, tmp_path_factory):
    return language_repo(conn, tmp_path_factory.mktemp("us4") / "repo", "java", "kotlin", "rust")


@pytest.fixture(scope="module")
def us5(conn, tmp_path_factory):
    return language_repo(conn, tmp_path_factory.mktemp("us5") / "repo", "php", "ruby", "swift")
