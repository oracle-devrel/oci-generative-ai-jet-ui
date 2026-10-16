"""Opt-in live permission tests with isolated users in a local Oracle container.

Set ORAVIZ_SECURITY_CONTAINER to the disposable development container and
ORAVIZ_TEST_DSN to its FREEPDB1 listener. Provisioning uses local OS auth inside
that container, never application credentials. Only generated OVSEC_* users
and their synthetic tables are removed during cleanup.
"""

import os
import secrets
import subprocess
import uuid

import oracledb
import pytest

from oraviz_mcp import server
oracledb.defaults.program = "devrel-developerhub-oraviz-mcp"

pytestmark = pytest.mark.skipif(
    not (os.environ.get("ORAVIZ_SECURITY_CONTAINER") and os.environ.get("ORAVIZ_TEST_DSN")),
    reason="Requires an explicitly selected local Oracle security-test container and DSN",
)


@pytest.fixture(scope="module")
def security_accounts():
    suffix = uuid.uuid4().hex[:12].upper()
    owner, reader = f"OVSEC_O_{suffix}", f"OVSEC_R_{suffix}"
    password = "Ov" + secrets.token_hex(20)
    created = []

    def provision(sql):
        result = subprocess.run(
            ["docker", "exec", "-i", os.environ["ORAVIZ_SECURITY_CONTAINER"],
             "sqlplus", "-s", "/", "as", "sysdba"],
            input="WHENEVER SQLERROR EXIT FAILURE\nSET ECHO OFF\n"
                  "ALTER SESSION SET CONTAINER = FREEPDB1;\n" + sql + "\nEXIT\n",
            text=True, capture_output=True, timeout=60,
        )
        if result.returncode:
            pytest.fail("Oracle security fixture provisioning failed (SQL and credentials withheld)")

    try:
        for user in (owner, reader):
            provision(f'CREATE USER {user} IDENTIFIED BY "{password}";')
            created.append(user)
            provision(f"GRANT CREATE SESSION TO {user};")
        provision(f"ALTER USER {owner} QUOTA 1M ON USERS;\n"
                  f"CREATE TABLE {owner}.ALLOWED_DATA (id NUMBER, label VARCHAR2(30), document CLOB);\n"
                  f"INSERT INTO {owner}.ALLOWED_DATA VALUES (1, 'synthetic', 'private large object');\n"
                  f"CREATE TABLE {owner}.FORBIDDEN_DATA (secret VARCHAR2(30));\n"
                  f"INSERT INTO {owner}.FORBIDDEN_DATA VALUES ('not granted');\n"
                  f"COMMIT;\nGRANT READ ON {owner}.ALLOWED_DATA TO {reader};")
        # Confirm the supplied listener points at the provisioned PDB.
        with oracledb.connect(user=reader, password=password, dsn=os.environ["ORAVIZ_TEST_DSN"]) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT label FROM {owner}.ALLOWED_DATA")
                assert cursor.fetchone() == ("synthetic",)
        yield owner, reader, password
    finally:
        for user in reversed(created):
            provision(f"DROP USER {user} CASCADE;")


@pytest.fixture()
def reader_config(security_accounts, monkeypatch):
    owner, reader, password = security_accounts
    monkeypatch.setattr(server.config, "user", reader)
    monkeypatch.setattr(server.config, "password", password)
    monkeypatch.setattr(server.config, "dsn", os.environ["ORAVIZ_TEST_DSN"])
    return owner, reader


def test_reader_queries_approved_data_without_materializing_lob(reader_config):
    owner, _ = reader_config
    result = server.execute_query(f"SELECT id, label, document FROM {owner}.ALLOWED_DATA")
    assert "synthetic" in result and "<LOB>" in result
    assert "private large object" not in result


@pytest.mark.parametrize("statement", [
    "DELETE FROM {owner}.ALLOWED_DATA",
    "UPDATE {owner}.ALLOWED_DATA SET label = 'changed'",
    "SELECT * FROM {owner}.ALLOWED_DATA FOR UPDATE",
    "SELECT * FROM {owner}.FORBIDDEN_DATA",
    "CREATE TABLE UNAUTHORIZED_TABLE (id NUMBER)",
])
def test_database_rejects_operations_even_without_connector_guard(reader_config, statement):
    owner, _ = reader_config
    with server.get_oracle_connection() as connection:
        with connection.cursor() as cursor:
            with pytest.raises(oracledb.DatabaseError) as error:
                cursor.execute(statement.format(owner=owner))
            # 26ai reports missing object privileges as ORA-41900.
            assert error.value.args[0].code in {942, 1031, 41900}


def test_reader_can_use_table_tools(reader_config):
    owner, _ = reader_config
    table = f"{owner}.ALLOWED_DATA"
    assert "ALLOWED_DATA" in server.list_tables(owner)
    assert "LABEL" in server.get_table_schema(table)
    assert "synthetic" in server.sample_table_data(table)
    assert server.get_table_details(table, exact_row_count=True)["exact_row_count"] == 1
    assert server.profile_table(table, columns=["ID", "LABEL"])["row_count"] == 1
