#!/usr/bin/env python
"""
Live integration tests against an Oracle AI Database.

Skipped unless ORAVIZ_TEST_DSN is set. Example for a local 26ai Free container:

    docker run -d --name oraviz-oracle -p 1530:1521 \
      -e ORACLE_PWD=OraViz2026 container-registry.oracle.com/database/free:latest

    export ORAVIZ_TEST_DSN=localhost:1530/FREEPDB1
    export ORAVIZ_TEST_USER=oraviz
    export ORAVIZ_TEST_PASSWORD=OraViz2026
    uv run pytest tests/integration -v
"""

import os

import oracledb
import pytest

from oraviz_mcp import server
oracledb.defaults.program = "devrel-developerhub-oraviz-mcp"

pytestmark = pytest.mark.skipif(
    not os.environ.get("ORAVIZ_TEST_DSN"),
    reason=(
        "Set ORAVIZ_TEST_DSN, ORAVIZ_TEST_USER and ORAVIZ_TEST_PASSWORD to run "
        "the live Oracle integration tests."
    ),
)

TABLE = f"ORAVIZ_IT_{os.getpid()}"
VECTOR_TABLE = f"ORAVIZ_IT_VEC_{os.getpid()}"


@pytest.fixture(scope="module")
def dsn():
    return os.environ["ORAVIZ_TEST_DSN"]


@pytest.fixture(scope="module")
def credentials():
    return (
        os.environ.get("ORAVIZ_TEST_USER", "oraviz"),
        os.environ["ORAVIZ_TEST_PASSWORD"],
    )


@pytest.fixture()
def configured(monkeypatch, dsn, credentials):
    """Point the server config at the test database."""
    user, password = credentials
    monkeypatch.setattr(server.config, "user", user)
    monkeypatch.setattr(server.config, "password", password)
    monkeypatch.setattr(server.config, "dsn", dsn)
    monkeypatch.setattr(server.config, "max_rows", 500)
    monkeypatch.setattr(server.config, "preview_rows", 25)


@pytest.fixture()
def db(configured, dsn, credentials):
    user, password = credentials
    connection = oracledb.connect(user=user, password=password, dsn=dsn)
    with connection.cursor() as cursor:
        cursor.execute(
            f"BEGIN EXECUTE IMMEDIATE 'DROP TABLE {TABLE} PURGE'; "
            "EXCEPTION WHEN OTHERS THEN IF SQLCODE != -942 THEN RAISE; END IF; END;"
        )
        cursor.execute(
            f"CREATE TABLE {TABLE} (id NUMBER PRIMARY KEY, label VARCHAR2(30), "
            "amount NUMBER(10,2), created DATE)"
        )
        cursor.executemany(
            f"INSERT INTO {TABLE} VALUES (:1, :2, :3, DATE '2026-09-14')",
            [(1, "alpha", 10.5), (2, "beta", 20.0), (3, "gamma", 30.25)],
        )
        connection.commit()
    yield TABLE
    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE {TABLE} PURGE")
    connection.close()


def test_execute_query_returns_compact_rows(db):
    text = server.execute_query(f"SELECT label, amount FROM {db} ORDER BY id")
    assert "3 row(s)" in text
    assert "| alpha | 10.5 |" in text


def test_execute_query_rejects_write_statements(db):
    with pytest.raises(ValueError, match="read-only"):
        server.execute_query(f"DELETE FROM {db}")


def test_list_tables_includes_created_table(db):
    assert db in server.list_tables()


def test_table_schema_includes_primary_key(db):
    text = server.get_table_schema(db)
    assert "LABEL" in text
    assert "YES" in text


def test_sample_table_data(db):
    text = server.sample_table_data(db, 2)
    assert "2 row(s)" in text


def test_table_details_exact_count(db):
    details = server.get_table_details(db, exact_row_count=True)
    assert details["object_type"] == "TABLE"
    assert details["exact_row_count"] == 3


def test_profile_table(db):
    profile = server.profile_table(db, columns=["LABEL", "AMOUNT"])
    assert profile["row_count"] == 3
    amounts = next(column for column in profile["columns"] if column["column"] == "AMOUNT")
    assert amounts["non_null"] == 3
    assert amounts["distinct"] == 3
    assert amounts["nulls"] == 0


def test_create_chart_renders_png(db):
    result = server.create_chart(f"SELECT label, amount FROM {db} ORDER BY id", "bar")
    image, summary = result
    assert image.data.startswith(b"\x89PNG")
    assert "Rendered a `bar` chart" in summary


@pytest.fixture()
def vector_db(configured, dsn, credentials):
    user, password = credentials
    connection = oracledb.connect(user=user, password=password, dsn=dsn)
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    f"BEGIN EXECUTE IMMEDIATE 'DROP TABLE {VECTOR_TABLE} PURGE'; "
                    "EXCEPTION WHEN OTHERS THEN IF SQLCODE != -942 THEN RAISE; END IF; END;"
                )
                cursor.execute(
                    f"CREATE TABLE {VECTOR_TABLE} (label VARCHAR2(20), embedding VECTOR(4, FLOAT32))"
                )
                cursor.executemany(
                    f"INSERT INTO {VECTOR_TABLE} VALUES (:1, TO_VECTOR(:2))",
                    [
                        ("v1", "[1.0, 2.0, 3.0, 4.0]"),
                        ("v2", "[4.0, 3.0, 2.0, 1.0]"),
                        ("v3", "[1.5, 1.5, 3.5, 3.5]"),
                    ],
                )
                connection.commit()
            except oracledb.DatabaseError as error:
                pytest.skip(f"VECTOR not supported by this database: {error}")
        yield VECTOR_TABLE
    finally:
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE {VECTOR_TABLE} PURGE")
        except oracledb.DatabaseError:
            pass
        connection.close()


def test_vector_column_is_summarised(vector_db):
    text = server.execute_query(f"SELECT label, embedding FROM {vector_db} ORDER BY label")
    assert "<VECTOR(4)>" in text


def test_create_chart_projects_vectors(vector_db):
    image, summary = server.create_chart(
        f"SELECT label, embedding FROM {vector_db} ORDER BY label",
        "vector",
        title="Embeddings",
    )
    assert image.data.startswith(b"\x89PNG")
    assert "Rendered a `vector` chart" in summary
