"""Layer 5: demo conversation memory.

This is a small, demo-safe memory layer used until the Oracle Agent Memory
package is wired in. Before migration, chat turns are stored in MongoDB. During
migration, those turns are imported into an Oracle table so the target-side
agent can recover the conversation after the data move.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

from data_migration_harness import source_config
from data_migration_harness.environment import oracle_pool

DEFAULT_THREAD_ID = "demo-thread"

Role = Literal["user", "assistant"]


def _now() -> datetime:
    return datetime.now(UTC)


def save_mongo_message(
    role: Role,
    content: str,
    *,
    thread_id: str = DEFAULT_THREAD_ID,
    tool_calls: list | None = None,
) -> None:
    source_config.database().chat_history.insert_one(
        {
            "thread_id": thread_id,
            "side": "mongo",
            "role": role,
            "content": content,
            "tool_calls": tool_calls or [],
            "created_at": _now(),
        }
    )


def get_mongo_thread(thread_id: str = DEFAULT_THREAD_ID, limit: int = 200) -> list[dict]:
    docs = list(
        source_config.database()
        .chat_history.find({"thread_id": thread_id})
        .sort("created_at", 1)
        .limit(limit)
    )
    for doc in docs:
        doc["_id"] = str(doc.get("_id"))
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat()
    return docs


def count_mongo_messages(thread_id: str = DEFAULT_THREAD_ID) -> int:
    return source_config.database().chat_history.count_documents({"thread_id": thread_id})


def clear_mongo_thread(thread_id: str = DEFAULT_THREAD_ID) -> None:
    source_config.database().chat_history.delete_many({"thread_id": thread_id})


def init_oracle_memory() -> None:
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            BEGIN
              EXECUTE IMMEDIATE '
                CREATE TABLE agent_chat_memory (
                    memory_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    thread_id VARCHAR2(100) NOT NULL,
                    source_side VARCHAR2(20) NOT NULL,
                    role VARCHAR2(20) NOT NULL,
                    content CLOB NOT NULL,
                    tool_calls CLOB CHECK (tool_calls IS JSON),
                    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
                )';
            EXCEPTION
              WHEN OTHERS THEN
                IF SQLCODE != -955 THEN RAISE; END IF;
            END;
            """
        )
        conn.commit()


def save_oracle_message(
    role: Role,
    content: str,
    *,
    thread_id: str = DEFAULT_THREAD_ID,
    source_side: str = "oracle",
    tool_calls: list | None = None,
) -> None:
    init_oracle_memory()
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO agent_chat_memory (thread_id, source_side, role, content, tool_calls)
            VALUES (:thread_id, :source_side, :role, :content, :tool_calls)
            """,
            {
                "thread_id": thread_id,
                "source_side": source_side,
                "role": role,
                "content": content,
                "tool_calls": json.dumps(tool_calls or []),
            },
        )
        conn.commit()


def import_mongo_thread(thread_id: str = DEFAULT_THREAD_ID) -> int:
    """Copy Mongo chat_history rows into Oracle memory.

    Existing imported rows for the same thread/source are removed first so a
    rehearsal can be rerun without duplicating the same conversation.
    """
    init_oracle_memory()
    messages = get_mongo_thread(thread_id=thread_id, limit=500)
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM agent_chat_memory WHERE thread_id = :thread_id AND source_side = 'mongo'",
            {"thread_id": thread_id},
        )
        rows = [
            {
                "thread_id": m["thread_id"],
                "source_side": "mongo",
                "role": m["role"],
                "content": m["content"],
                "tool_calls": json.dumps(m.get("tool_calls") or []),
            }
            for m in messages
        ]
        if rows:
            cur.executemany(
                """
                INSERT INTO agent_chat_memory (thread_id, source_side, role, content, tool_calls)
                VALUES (:thread_id, :source_side, :role, :content, :tool_calls)
                """,
                rows,
            )
        conn.commit()
    return len(messages)


def get_oracle_thread(thread_id: str = DEFAULT_THREAD_ID, limit: int = 200) -> list[dict]:
    init_oracle_memory()
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT thread_id, source_side, role, content, tool_calls,
                   TO_CHAR(created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS created_at
            FROM agent_chat_memory
            WHERE thread_id = :thread_id
            ORDER BY memory_id
            FETCH FIRST :limit ROWS ONLY
            """,
            {"thread_id": thread_id, "limit": limit},
        )
        cols = [c[0].lower() for c in cur.description]
        rows = []
        for row in cur.fetchall():
            item = dict(zip(cols, row, strict=False))
            # oracledb may return CLOB values as LOB objects depending on mode.
            for key in ("content", "tool_calls"):
                if hasattr(item.get(key), "read"):
                    item[key] = item[key].read()
            try:
                item["tool_calls"] = json.loads(item.get("tool_calls") or "[]")
            except Exception:
                item["tool_calls"] = []
            rows.append(item)
        return rows


def count_oracle_messages(
    thread_id: str = DEFAULT_THREAD_ID, source_side: str | None = None
) -> int:
    init_oracle_memory()
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        if source_side:
            cur.execute(
                "SELECT COUNT(*) FROM agent_chat_memory WHERE thread_id = :thread_id AND source_side = :source_side",
                {"thread_id": thread_id, "source_side": source_side},
            )
        else:
            cur.execute(
                "SELECT COUNT(*) FROM agent_chat_memory WHERE thread_id = :thread_id",
                {"thread_id": thread_id},
            )
        return int(cur.fetchone()[0])


def clear_oracle_memory(thread_id: str = DEFAULT_THREAD_ID) -> None:
    init_oracle_memory()
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM agent_chat_memory WHERE thread_id = :thread_id", {"thread_id": thread_id}
        )
        conn.commit()


def build_context(thread_id: str = DEFAULT_THREAD_ID, limit: int = 6) -> str:
    """Return a compact memory context string for the Oracle-side agent."""
    messages = get_oracle_thread(thread_id=thread_id, limit=limit)
    if not messages:
        return ""
    lines = ["Prior conversation memory migrated into Oracle:"]
    for m in messages[-limit:]:
        lines.append(f"- {m['role']}: {m['content'][:300]}")
    return "\n".join(lines)
