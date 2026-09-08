"""Fact memory store.

The canonical write path is ``PromotionGate.promote()``. The insert
helper is named ``_write_unchecked`` so any code that bypasses the gate
is grep-visible (seed, supersession, store-layer tests). Read-side
methods (``find_dedup``, ``find_contradiction``, ``get``, ``confirm``)
are freely callable.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import Any

import oracledb

from memory.embeddings import vector_embedding_sql


def _fid() -> str:
    return f"fact_{secrets.token_hex(6)}"


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


class FactStore:
    def __init__(self, conn: oracledb.AsyncConnection):
        self.conn = conn

    async def _write_unchecked(
        self,
        tenant_id: str,
        subject: str,
        predicate: str,
        content: str,
        content_hash: str,
        source_run_id: str,
        confidence: float,
        status: str = "active",
        user_id: str | None = None,
        agent_id: str | None = None,
        source_turn_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
        commit: bool = True,
    ) -> str:
        """Insert a fact row, bypassing the promotion gate.

        commit=False lets the gate batch this with surrounding SELECTs
        into one transaction; admin callers leave commit=True.
        """
        fact_id = _fid()
        emb_sql = vector_embedding_sql(":content")
        meta_json = json.dumps(metadata) if metadata is not None else None
        created_at = datetime.now(tz=timezone.utc)

        cur = self.conn.cursor()
        await cur.execute(
            f"""
            INSERT INTO fact_memory
              (fact_id, tenant_id, user_id, agent_id, subject, predicate,
               content, content_hash, embedding, metadata, status,
               source_run_id, source_turn_id, confidence, expires_at, created_at)
            VALUES
              (:fact_id, :tenant_id, :u_id, :agent_id, :subject, :predicate,
               :content, :content_hash, {emb_sql}, :metadata, :status,
               :source_run_id, :source_turn_id, :confidence, :expires_at, :created_at)
            """,
            fact_id=fact_id,
            tenant_id=tenant_id,
            u_id=user_id,
            agent_id=agent_id,
            subject=subject,
            predicate=predicate,
            content=content,
            content_hash=content_hash,
            metadata=meta_json,
            status=status,
            source_run_id=source_run_id,
            source_turn_id=source_turn_id,
            confidence=confidence,
            expires_at=expires_at,
            created_at=created_at,
        )
        if commit:
            await self.conn.commit()
        return fact_id

    async def find_dedup(
        self,
        content_hash: str,
        tenant_id: str,
        user_id: str | None = None,
        agent_id: str | None = None,
    ) -> str | None:
        """Return fact_id for an exact-match duplicate in scope, or None."""
        cur = self.conn.cursor()
        await cur.execute(
            """
            SELECT fact_id FROM fact_memory
             WHERE content_hash = :content_hash
               AND tenant_id = :tenant_id
               AND (user_id = :u_id OR (user_id IS NULL AND :u_id IS NULL))
               AND (agent_id = :agent_id OR (agent_id IS NULL AND :agent_id IS NULL))
               AND status != 'revoked'
             ORDER BY created_at DESC
             FETCH FIRST 1 ROWS ONLY
            """,
            content_hash=content_hash,
            tenant_id=tenant_id,
            u_id=user_id,
            agent_id=agent_id,
        )
        row = await cur.fetchone()
        return row[0] if row else None

    async def find_contradiction(
        self,
        tenant_id: str,
        subject: str,
        predicate: str,
        content_hash: str,
        user_id: str | None = None,
    ) -> str | None:
        """Return fact_id for an active fact with same (tenant, subject, predicate, user)
        but different content_hash, or None."""
        cur = self.conn.cursor()
        await cur.execute(
            """
            SELECT fact_id FROM fact_memory
             WHERE tenant_id = :tenant_id
               AND subject = :subject
               AND predicate = :predicate
               AND content_hash != :content_hash
               AND (user_id = :u_id OR (user_id IS NULL AND :u_id IS NULL))
               AND status != 'revoked'
               AND superseded_by IS NULL
             FETCH FIRST 1 ROWS ONLY
            """,
            tenant_id=tenant_id,
            subject=subject,
            predicate=predicate,
            content_hash=content_hash,
            u_id=user_id,
        )
        row = await cur.fetchone()
        return row[0] if row else None

    async def mark_superseded(self, old_fact_id: str, new_fact_id: str) -> None:
        """Set superseded_by and revoke old fact. Does NOT commit — caller owns the transaction."""
        cur = self.conn.cursor()
        await cur.execute(
            """
            UPDATE fact_memory
               SET superseded_by = :new_fact_id, status = 'revoked'
             WHERE fact_id = :old_fact_id
            """,
            new_fact_id=new_fact_id,
            old_fact_id=old_fact_id,
        )

    async def get(self, fact_id: str) -> dict | None:
        """Return a dict of fact fields, or None if not found."""
        cur = self.conn.cursor()
        await cur.execute(
            """
            SELECT fact_id, tenant_id, user_id, subject, predicate, content,
                   confidence, status, superseded_by, source_run_id, created_at
              FROM fact_memory
             WHERE fact_id = :fact_id
            """,
            fact_id=fact_id,
        )
        row = await cur.fetchone()
        if not row:
            return None
        (
            fid, tid, u_id, subject, predicate, content_raw,
            confidence, status, superseded_by, source_run_id, created_at,
        ) = row
        return {
            "fact_id": fid,
            "tenant_id": tid,
            "user_id": u_id,
            "subject": subject,
            "predicate": predicate,
            "content": await _decode_clob(content_raw),
            "confidence": confidence,
            "status": status,
            "superseded_by": superseded_by,
            "source_run_id": source_run_id,
            "created_at": created_at,
        }

    async def confirm(self, fact_id: str) -> bool:
        """Promote a provisional fact to active. Returns True if a row
        was updated, False if the id didn't match a provisional fact
        (already active, revoked, or doesn't exist)."""
        cur = self.conn.cursor()
        await cur.execute(
            """
            UPDATE fact_memory
               SET status = 'active'
             WHERE fact_id = :fact_id AND status = 'provisional'
            """,
            fact_id=fact_id,
        )
        await self.conn.commit()
        return cur.rowcount > 0
