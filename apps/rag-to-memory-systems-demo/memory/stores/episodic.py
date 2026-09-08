"""Episodic memory store. Structured task summaries with in-DB embedding."""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import Any

import oracledb

from memory.embeddings import vector_embedding_sql


def _eid() -> str:
    return f"ep_{secrets.token_hex(6)}"


async def _decode_clob(raw: Any) -> str | None:
    """Read a CLOB object back to a plain string. Handles async LOB objects."""
    if raw is None:
        return None
    if hasattr(raw, "read"):
        result = raw.read()
        # oracledb async LOB returns a coroutine from .read()
        if hasattr(result, "__await__"):
            return await result
        return result
    return str(raw)


def _decode_json(raw: Any) -> Any:
    """Decode a JSON column value that may already be decoded or may be a string."""
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


class EpisodicStore:
    def __init__(self, conn: oracledb.AsyncConnection):
        self.conn = conn

    async def write(
        self,
        tenant_id: str,
        task_type: str,
        title: str,
        summary: str,
        outcome: str,
        key_steps: list[str],
        source_run_id: str,
        completed_at: datetime | None = None,
        user_id: str | None = None,
        artifacts: dict | None = None,
        status: str = "active",
    ) -> str:
        episode_id = _eid()
        emb_sql = vector_embedding_sql(":summary")
        key_steps_json = json.dumps(key_steps)
        artifacts_json = json.dumps(artifacts) if artifacts is not None else None
        if completed_at is None:
            completed_at = datetime.now(tz=timezone.utc)

        cur = self.conn.cursor()
        await cur.execute(
            f"""
            INSERT INTO episodic_memory
              (episode_id, tenant_id, user_id, task_type, title, summary,
               outcome, key_steps, artifacts, embedding, status,
               source_run_id, completed_at)
            VALUES
              (:episode_id, :tenant_id, :u_id, :task_type, :title, :summary,
               :outcome, :key_steps, :artifacts, {emb_sql}, :status,
               :source_run_id, :completed_at)
            """,
            episode_id=episode_id,
            tenant_id=tenant_id,
            u_id=user_id,
            task_type=task_type,
            title=title,
            summary=summary,
            outcome=outcome,
            key_steps=key_steps_json,
            artifacts=artifacts_json,
            status=status,
            source_run_id=source_run_id,
            completed_at=completed_at,
        )
        await self.conn.commit()
        return episode_id

    async def get(self, episode_id: str) -> dict | None:
        """Return a dict of episode fields, or None if not found."""
        cur = self.conn.cursor()
        await cur.execute(
            """
            SELECT episode_id, tenant_id, task_type, title, summary,
                   outcome, key_steps, status, source_run_id, completed_at
              FROM episodic_memory
             WHERE episode_id = :episode_id
            """,
            episode_id=episode_id,
        )
        row = await cur.fetchone()
        if not row:
            return None
        (
            eid, tid, task_type, title, summary_raw,
            outcome, key_steps_raw, status, source_run_id, completed_at,
        ) = row
        return {
            "episode_id": eid,
            "tenant_id": tid,
            "task_type": task_type,
            "title": title,
            "summary": await _decode_clob(summary_raw),
            "outcome": outcome,
            "key_steps": _decode_json(key_steps_raw),
            "status": status,
            "source_run_id": source_run_id,
            "completed_at": completed_at,
        }
