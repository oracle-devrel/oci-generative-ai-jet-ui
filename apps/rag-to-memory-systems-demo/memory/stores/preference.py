"""Per-user preferences. PRIMARY KEY (user, tenant, pref_key) makes
this an upsert via MERGE."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any
import oracledb


class PreferenceStore:
    def __init__(self, conn: oracledb.AsyncConnection):
        self.conn = conn

    async def set(
        self,
        user_id: str,
        tenant_id: str,
        pref_key: str,
        pref_value: Any,
        source: str,
        confidence: float | None = None,
        commit: bool = True,
    ) -> None:
        """Upsert a preference row. commit=False lets PromotionGate batch
        the MERGE with the rest of the gate's checks into one transaction."""
        cur = self.conn.cursor()
        pval = json.dumps(pref_value)
        ts = datetime.now(tz=timezone.utc)
        await cur.execute(
            """
            MERGE INTO preference_memory p
            USING (SELECT :1 AS user_id, :2 AS tenant_id, :3 AS pref_key FROM dual) s
               ON (p.user_id = s.user_id AND p.tenant_id = s.tenant_id AND p.pref_key = s.pref_key)
            WHEN MATCHED THEN UPDATE SET
              pref_value = :4, source = :5, confidence = :6, updated_at = :7
            WHEN NOT MATCHED THEN INSERT
              (user_id, tenant_id, pref_key, pref_value, source, confidence, updated_at)
            VALUES
              (s.user_id, s.tenant_id, s.pref_key, :8, :9, :10, :11)
            """,
            [user_id, tenant_id, pref_key, pval, source, confidence, ts,
             pval, source, confidence, ts],
        )
        if commit:
            await self.conn.commit()

    async def get(self, user_id: str, tenant_id: str, pref_key: str) -> dict | None:
        cur = self.conn.cursor()
        await cur.execute(
            """
            SELECT pref_value, source, confidence FROM preference_memory
             WHERE user_id = :u_id AND tenant_id = :tid AND pref_key = :pkey
            """,
            u_id=user_id, tid=tenant_id, pkey=pref_key,
        )
        row = await cur.fetchone()
        if not row:
            return None
        pval, src, conf = row
        raw = pval.read() if hasattr(pval, "read") else pval
        if isinstance(raw, (dict, list, int, float, bool)):
            value = raw
        else:
            try:
                value = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                value = raw
        return {"value": value, "source": src, "confidence": conf}

    async def list_for_user(self, user_id: str, tenant_id: str) -> list[dict]:
        cur = self.conn.cursor()
        await cur.execute(
            """
            SELECT pref_key, pref_value, source, confidence FROM preference_memory
             WHERE user_id = :u_id AND tenant_id = :tid
             ORDER BY pref_key
            """,
            u_id=user_id, tid=tenant_id,
        )
        out = []
        async for row in cur:
            pkey, pval, src, conf = row
            raw = pval.read() if hasattr(pval, "read") else pval
            if isinstance(raw, (dict, list)):
                value = raw
            else:
                try:
                    value = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    value = raw
            out.append({"key": pkey, "value": value, "source": src, "confidence": conf})
        return out
