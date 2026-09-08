"""Append-only trace log. Every turn writes at least two rows
(user_msg + model_msg). Replay by run_id."""
from __future__ import annotations
import json
import secrets
from datetime import datetime, timezone
from typing import Any
import oracledb


def _tid() -> str:
    return f"trc_{secrets.token_hex(6)}"


def _decode_json(raw: Any) -> Any:
    """Defensive decode for Oracle JSON column return values.
    Oracle 23ai may return decoded dicts/lists OR JSON strings.
    """
    if raw is None:
        return None
    if hasattr(raw, "read"):
        raw = raw.read()
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


class TraceStore:
    def __init__(self, conn: oracledb.AsyncConnection):
        self.conn = conn

    async def write(
        self,
        run_id: str,
        tenant_id: str,
        user_id: str | None,
        turn_index: int,
        event_type: str,
        payload: dict[str, Any],
        token_cost: int | None = None,
        latency_ms: int | None = None,
    ) -> str:
        trace_id = _tid()
        cur = self.conn.cursor()
        await cur.execute(
            """
            INSERT INTO trace_memory
              (trace_id, run_id, tenant_id, user_id, turn_index, event_type,
               payload, token_cost, latency_ms, created_at)
            VALUES
              (:trace_id, :run_id, :tid, :u_id, :turn, :etype,
               :payload, :tokens, :latency, :now)
            """,
            trace_id=trace_id, run_id=run_id, tid=tenant_id, u_id=user_id,
            turn=turn_index, etype=event_type,
            payload=json.dumps(payload), tokens=token_cost,
            latency=latency_ms, now=datetime.now(tz=timezone.utc),
        )
        await self.conn.commit()
        return trace_id

    async def get_run(self, run_id: str) -> list[dict]:
        cur = self.conn.cursor()
        await cur.execute(
            """
            SELECT turn_index, event_type, payload, created_at
              FROM trace_memory WHERE run_id = :run_id
             ORDER BY turn_index, created_at
            """,
            run_id=run_id,
        )
        out = []
        async for row in cur:
            turn, etype, payload, created = row
            out.append({
                "turn_index": turn, "event_type": etype,
                "payload": _decode_json(payload), "created_at": created,
            })
        return out

    async def count(self, tenant_id: str, since: datetime | None = None) -> int:
        cur = self.conn.cursor()
        if since:
            await cur.execute(
                "SELECT COUNT(*) FROM trace_memory WHERE tenant_id = :tid AND created_at >= :since",
                tid=tenant_id, since=since,
            )
        else:
            await cur.execute(
                "SELECT COUNT(*) FROM trace_memory WHERE tenant_id = :tid",
                tid=tenant_id,
            )
        (n,) = await cur.fetchone()
        return n
