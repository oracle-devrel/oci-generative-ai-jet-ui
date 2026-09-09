"""Episodic memory: past conversation turns, vector-searchable."""

from __future__ import annotations

import array
import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from soccer_agent.db import get_connection


@dataclass
class Turn:
    role: str
    content: str
    embedding: np.ndarray
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None


def _to_vector(arr: np.ndarray) -> array.array:
    if arr.dtype != np.float32:
        arr = arr.astype(np.float32)
    if arr.shape != (384,):
        raise ValueError(f"Expected (384,) embedding, got {arr.shape}")
    return array.array("f", arr.tolist())


class EpisodicMemory:
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

    def _next_turn_index(self, cur) -> int:
        cur.execute(
            "SELECT NVL(MAX(turn_index), -1) + 1 FROM episodic_memory "
            "WHERE session_id = :sid",
            sid=self.session_id,
        )
        return int(cur.fetchone()[0])

    def append(self, turn: Turn) -> None:
        with get_connection() as conn:
            cur = conn.cursor()
            idx = self._next_turn_index(cur)
            cur.execute(
                "INSERT INTO episodic_memory "
                "(session_id, turn_index, role, content, tool_name, tool_args, embedding) "
                "VALUES (:sid, :idx, :role, :content, :tname, :targs, :emb)",
                sid=self.session_id, idx=idx, role=turn.role, content=turn.content,
                tname=turn.tool_name,
                targs=json.dumps(turn.tool_args) if turn.tool_args else None,
                emb=_to_vector(turn.embedding),
            )
            conn.commit()

    def recent(self, limit: int = 8) -> list[Turn]:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT role, content, tool_name, tool_args "
                "FROM (SELECT role, content, tool_name, tool_args, turn_index "
                "      FROM episodic_memory WHERE session_id = :sid "
                "      ORDER BY turn_index DESC) "
                "WHERE ROWNUM <= :lim ORDER BY turn_index",
                sid=self.session_id, lim=limit,
            )
            rows = [
                (
                    role,
                    content.read() if hasattr(content, "read") else content,
                    tname,
                    (targs.read() if hasattr(targs, "read") else targs) if targs else None,
                )
                for role, content, tname, targs in cur.fetchall()
            ]
        return [
            Turn(
                role=role,
                content=content,
                embedding=np.zeros(384, dtype=np.float32),
                tool_name=tname,
                tool_args=(
                    targs if isinstance(targs, (dict, list))
                    else json.loads(targs)
                ) if targs else None,
            )
            for role, content, tname, targs in rows
        ]

    def search(self, query_embedding: np.ndarray, limit: int = 5) -> list[Turn]:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT role, content FROM episodic_memory WHERE session_id = :sid "
                "ORDER BY VECTOR_DISTANCE(embedding, :q, COSINE) "
                "FETCH FIRST :lim ROWS ONLY",
                sid=self.session_id, q=_to_vector(query_embedding), lim=limit,
            )
            rows = [
                (role, content.read() if hasattr(content, "read") else content)
                for role, content in cur.fetchall()
            ]
        return [
            Turn(
                role=role,
                content=content,
                embedding=np.zeros(384, dtype=np.float32),
            )
            for role, content in rows
        ]
