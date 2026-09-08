"""Working memory: per-session key/value store backed by Oracle."""

from __future__ import annotations

import json
from typing import Any

from soccer_agent.db import get_connection


class WorkingMemory:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._ensure_session()

    def _ensure_session(self) -> None:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "MERGE INTO agent_sessions s USING (SELECT :sid sid FROM DUAL) src "
                "ON (s.session_id = src.sid) "
                "WHEN NOT MATCHED THEN INSERT (session_id) VALUES (:sid)",
                sid=self.session_id,
            )
            conn.commit()

    def set(self, key: str, value: Any) -> None:
        payload = json.dumps(value)
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM working_memory WHERE session_id = :sid AND key = :k",
                sid=self.session_id, k=key,
            )
            cur.execute(
                "INSERT INTO working_memory (session_id, key, value_json) "
                "VALUES (:sid, :k, :v)",
                sid=self.session_id, k=key, v=payload,
            )
            conn.commit()

    def get(self, key: str) -> Any | None:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT value_json FROM working_memory "
                "WHERE session_id = :sid AND key = :k",
                sid=self.session_id, k=key,
            )
            row = cur.fetchone()
        if not row:
            return None
        val = row[0].read() if hasattr(row[0], "read") else row[0]
        if isinstance(val, (dict, list)):
            return val
        return json.loads(val)

    def delete(self, key: str) -> None:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM working_memory WHERE session_id = :sid AND key = :k",
                sid=self.session_id, k=key,
            )
            conn.commit()

    def clear_session(self) -> None:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM working_memory WHERE session_id = :sid",
                sid=self.session_id,
            )
            conn.commit()
