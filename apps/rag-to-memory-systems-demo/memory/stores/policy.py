"""Versioned policy storage. Writes via admin; reads via the unified retrieval
query — this class exposes single-key reads for inspection."""
from __future__ import annotations
import json
import secrets
from datetime import datetime, timezone
from typing import Any
import oracledb


def _pid() -> str:
    return f"pol_{secrets.token_hex(6)}"


class PolicyStore:
    def __init__(self, conn: oracledb.AsyncConnection):
        self.conn = conn

    async def set_policy(
        self,
        tenant_id: str,
        policy_key: str,
        policy_value: dict[str, Any],
        policy_type: str,
        version: int = 1,
        effective_from: datetime | None = None,
        effective_until: datetime | None = None,
        created_by: str = "admin",
    ) -> str:
        policy_id = _pid()
        effective_from = effective_from or datetime.now(tz=timezone.utc)
        cur = self.conn.cursor()
        await cur.execute(
            """
            INSERT INTO policy_memory
              (policy_id, tenant_id, policy_type, policy_key, policy_value,
               version, effective_from, effective_until, created_by)
            VALUES
              (:pid, :tid, :ptype, :pkey, :pval, :ver, :efrom, :euntil, :cby)
            """,
            pid=policy_id, tid=tenant_id, ptype=policy_type, pkey=policy_key,
            pval=json.dumps(policy_value), ver=version,
            efrom=effective_from, euntil=effective_until, cby=created_by,
        )
        await self.conn.commit()
        return policy_id

    async def get(self, tenant_id: str, policy_key: str) -> dict | None:
        cur = self.conn.cursor()
        await cur.execute(
            """
            SELECT policy_id, policy_value, version, policy_type
              FROM policy_memory
             WHERE tenant_id = :tid AND policy_key = :pkey
               AND (effective_until IS NULL OR effective_until > SYSTIMESTAMP)
             ORDER BY version DESC FETCH FIRST 1 ROWS ONLY
            """,
            tid=tenant_id, pkey=policy_key,
        )
        row = await cur.fetchone()
        if not row:
            return None
        pid, pval, ver, ptype = row
        raw = pval.read() if hasattr(pval, "read") else pval
        value = raw if isinstance(raw, (dict, list)) else json.loads(raw)
        return {"policy_id": pid, "value": value, "version": ver, "type": ptype}

    async def list_for_tenant(self, tenant_id: str) -> list[dict]:
        cur = self.conn.cursor()
        await cur.execute(
            """
            SELECT policy_key, policy_value, policy_type, version
              FROM policy_memory
             WHERE tenant_id = :tid
               AND (effective_until IS NULL OR effective_until > SYSTIMESTAMP)
             ORDER BY policy_key, version DESC
            """,
            tid=tenant_id,
        )
        out = []
        async for row in cur:
            pkey, pval, ptype, ver = row
            raw = pval.read() if hasattr(pval, "read") else pval
            value = raw if isinstance(raw, (dict, list)) else json.loads(raw)
            out.append({"key": pkey, "value": value, "type": ptype, "version": ver})
        return out
