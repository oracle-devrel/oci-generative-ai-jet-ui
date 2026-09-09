"""Pipeline health — the heartbeat that makes silent failure visible.

Row timestamps can hint that data changed; they cannot prove the sync RAN, and they
say nothing when a step fails or silently skips (the classic case: an expired API
token skipping one source for weeks). The fix is a heartbeat: the sync's last act is
one row in SYNC_RUNS (see oracle/schema/09_sync_runs.sql) with the outcome of every
step. Because it lives in the DATABASE — not in a local file on the machine that ran
the sync — the hosted MCP can read it from your phone even while that machine sleeps.

Shared by: scripts/sync.py (writer), the MCP status panel (reader), tests (pure fns).
"""
import datetime
import json

EXPECTED_HOURS = 26   # daily sync + slack; override per deployment via SYNC_EXPECTED_HOURS


def record_run(conn, results, host=""):
    """Append one heartbeat row; prune runs older than 90 days. Caller owns error policy."""
    ok = sum(1 for r in results if r.get("status") == "ok")
    with conn.cursor() as cur:
        cur.execute("INSERT INTO sync_runs (host, ok_steps, bad_steps, steps_json) "
                    "VALUES (:h, :o, :b, :j)",
                    h=(host or "")[:80], o=ok, b=len(results) - ok, j=json.dumps(results))
        cur.execute("DELETE FROM sync_runs WHERE run_at < SYSTIMESTAMP - INTERVAL '90' DAY")
    conn.commit()


def last_heartbeat(conn):
    """Latest run -> {'run_at': naive datetime, 'host': str, 'steps': [...]}, or None
    (no runs yet, table not created yet, or DB hiccup — all mean 'no heartbeat')."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT run_at, host, steps_json FROM sync_runs "
                        "ORDER BY run_id DESC FETCH FIRST 1 ROWS ONLY")
            row = cur.fetchone()
        if not row:
            return None
        ts, host, raw = row
        raw = raw.read() if hasattr(raw, "read") else raw
        ts = ts.replace(tzinfo=None) if getattr(ts, "tzinfo", None) else ts
        return {"run_at": ts, "host": host or "?", "steps": json.loads(raw)}
    except Exception:
        return None


def verdict(heartbeat, now=None, expected_hours=EXPECTED_HOURS):
    """Pure. heartbeat (from last_heartbeat, or None) ->
      {'state': 'no-heartbeat'|'ok'|'degraded'|'down', 'hours_since': float|None,
       'trouble': ['<step>: fail|skip', ...]}
    'down' = no run inside the expected window (machine off/asleep — local capabilities
    unavailable); 'degraded' = ran on time but some steps failed or skipped."""
    if heartbeat is None:
        return {"state": "no-heartbeat", "hours_since": None, "trouble": []}
    now = now or datetime.datetime.now()
    hours = max(0.0, (now - heartbeat["run_at"]).total_seconds() / 3600)
    trouble = [f"{s.get('label', '?')}: {s.get('status', '?')}"
               + (f" ({s['why']})" if s.get("why") else "")
               for s in heartbeat["steps"] if s.get("status") != "ok"]
    state = "down" if hours > expected_hours else ("degraded" if trouble else "ok")
    return {"state": state, "hours_since": round(hours, 1), "trouble": trouble}


def panel_lines(v):
    """Pure. verdict -> the LOCAL PIPELINE section of the status panel (list of lines)."""
    if v["state"] == "no-heartbeat":
        return ["LOCAL PIPELINE: no heartbeat yet — apply oracle/schema/09_sync_runs.sql "
                "(scripts/apply_schema.py) and let the sync run once."]
    head = {"ok": "OK", "degraded": "DEGRADED", "down": "DOWN"}[v["state"]]
    lines = [f"LOCAL PIPELINE: {head} — last sync run {v['hours_since']}h ago"]
    if v["state"] == "down":
        lines.append("  → the machine that runs the sync looks off/asleep; local-only "
                     "capabilities are unavailable until it wakes. Hosted search/wiki "
                     "keep working (this panel is live proof).")
    for t in v["trouble"]:
        lines.append(f"  ✗ {t}")
    return lines
