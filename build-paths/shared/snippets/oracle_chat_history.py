"""Oracle-backed chat message history for LangChain.

`langchain-oracledb` does not ship a chat-history class as of this writing —
its top-level submodules are only `document_loaders`, `embeddings`,
`retrievers`, `utilities`, `vectorstores`. So we roll a small one ourselves on
top of `oracledb` + LangChain's `BaseChatMessageHistory`.

WORKING DDL (idempotent under Oracle — `CREATE TABLE IF NOT EXISTS` is NOT
valid Oracle syntax; wrap in a PL/SQL block that swallows ORA-00955):

    BEGIN
        EXECUTE IMMEDIATE q'[
            CREATE TABLE __TABLE__ (
                session_id VARCHAR2(120) NOT NULL,
                seq        NUMBER GENERATED ALWAYS AS IDENTITY,
                payload    CLOB CHECK (payload IS JSON),
                created_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                PRIMARY KEY (session_id, seq)
            )
        ]';
    EXCEPTION WHEN OTHERS THEN
        IF SQLCODE != -955 THEN RAISE; END IF;
    END;
    /

JSON COLUMN + ASSM TABLESPACE — IMPORTANT
-----------------------------------------
Oracle's `JSON` validation requires Automatic Segment Space Management (ASSM).
The default `SYSTEM` tablespace lacks ASSM, so connecting as `SYSTEM` and
inserting a JSON CLOB raises ORA-43853. Always run as an app user whose
`DEFAULT TABLESPACE` is `USERS` (or another ASSM tablespace). The
`oracle-aidb-docker-setup` skill creates the app user with `USERS` by default.

USAGE
-----
    history = OracleChatHistory(conn, session_id="user-42")
    history.add_user_message("hi")
    history.add_ai_message("hello")
    print(history.messages)  # reload-safe across kernel restarts

    from langchain_core.runnables.history import RunnableWithMessageHistory
    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda sid: OracleChatHistory(conn, session_id=sid),
        input_messages_key="question",
        history_messages_key="history",
    )
"""

from __future__ import annotations

import json

import oracledb
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict


class OracleChatHistory(BaseChatMessageHistory):
    def __init__(
        self,
        conn: oracledb.Connection,
        session_id: str,
        table_name: str = "chat_history",
    ):
        self.conn = conn
        self.session_id = session_id
        self.table = table_name

    @property
    def messages(self) -> list[BaseMessage]:
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT payload FROM {self.table} "
                f"WHERE session_id = :sid ORDER BY seq",
                sid=self.session_id,
            )
            rows = []
            for (payload,) in cur.fetchall():
                # oracledb 4.x auto-parses IS JSON columns to dict already.
                # Earlier driver modes returned LOB/bytes/str. Cover all four
                # so the same code path works regardless of the installed
                # oracledb version (v3-F-1 from cold-start friction pass).
                if isinstance(payload, dict):
                    rows.append(payload)
                    continue
                raw = payload.read() if hasattr(payload, "read") else payload
                if isinstance(raw, (bytes, bytearray)):
                    raw = raw.decode("utf-8")
                rows.append(json.loads(raw))
        return messages_from_dict(rows)

    def add_message(self, message: BaseMessage) -> None:
        payload = json.dumps(messages_to_dict([message])[0])
        with self.conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.table} (session_id, payload) VALUES (:sid, :p)",
                sid=self.session_id,
                p=payload,
            )
        self.conn.commit()

    def clear(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self.table} WHERE session_id = :sid",
                sid=self.session_id,
            )
        self.conn.commit()


# Migration helper: run once during project bootstrap.
INIT_DDL = """\
BEGIN
    EXECUTE IMMEDIATE q'[
        CREATE TABLE chat_history (
            session_id VARCHAR2(120) NOT NULL,
            seq        NUMBER GENERATED ALWAYS AS IDENTITY,
            payload    CLOB CHECK (payload IS JSON),
            created_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
            PRIMARY KEY (session_id, seq)
        )
    ]';
EXCEPTION WHEN OTHERS THEN
    IF SQLCODE != -955 THEN RAISE; END IF;
END;
"""


def init_table(conn: oracledb.Connection) -> None:
    """Idempotent: create chat_history table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute(INIT_DDL)
    conn.commit()
