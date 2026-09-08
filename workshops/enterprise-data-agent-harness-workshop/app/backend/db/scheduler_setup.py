"""Periodic schema rescans via DBMS_SCHEDULER. Mirrors notebook §12.

Two pieces:

  1. `scan_history` table — bookkeeping for every scan the agent has run.
     Created idempotently on app boot. The §5 scanner writes a row when
     it starts/finishes a scan.

  2. (opt-in) A `DBMS_SCHEDULER` job that calls a tiny PL/SQL procedure to
     enqueue a scan request — the harness, when running, drains queued rows
     and runs `run_scan(owner)` on each. This keeps the cron in the database
     (so it survives kernel restarts) while keeping the actual scan logic in
     Python.

Opt in by setting SCAN_INTERVAL_MIN in the env (e.g. SCAN_INTERVAL_MIN=60).
With the variable unset (the default), no scheduler job is created.
"""

from __future__ import annotations

import os
import traceback

import oracledb


SCAN_PROC = os.environ.get("SCAN_PROC_NAME", "AGENT_REQUEST_SCAN")
SCAN_JOB = os.environ.get("SCAN_JOB_NAME", "AGENT_PERIODIC_SCAN")


SCAN_HISTORY_DDL = (
    "CREATE TABLE scan_history ("
    "  scan_id          VARCHAR2(64) DEFAULT SYS_GUID() PRIMARY KEY,"
    "  target_owner     VARCHAR2(128) NOT NULL,"
    "  objects_scanned  NUMBER,"
    "  facts_written    NUMBER,"
    "  notes            VARCHAR2(4000),"
    "  started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
    "  finished_at      TIMESTAMP)"
)


def ensure_scan_history(agent_conn) -> None:
    """Idempotently create the bookkeeping table. The notebook used CLOB for
    `notes`; we use VARCHAR2(4000) so DBMS_SCHEDULER queries that compare on
    `notes = 'queued-by-scheduler'` don't trip ORA-22848 (CLOB comparison)."""
    with agent_conn.cursor() as cur:
        try:
            cur.execute(SCAN_HISTORY_DDL)
        except oracledb.DatabaseError as e:
            if e.args[0].code != 955:  # 955 = name already used
                raise
    agent_conn.commit()


def ensure_scheduler(agent_conn, interval_min: int, owner: str) -> dict:
    """Create or replace the DBMS_SCHEDULER job that enqueues scans.

    Returns a status dict { ok, reason, job_name, interval_min, owner }.
    """
    if interval_min <= 0:
        return {"ok": False, "reason": "interval_min <= 0; skipping",
                "job_name": SCAN_JOB, "interval_min": interval_min, "owner": owner}

    proc_sql = (
        f"CREATE OR REPLACE PROCEDURE {SCAN_PROC}(p_owner IN VARCHAR2) AS "
        f"BEGIN "
        f"  INSERT INTO scan_history (target_owner, notes) "
        f"  VALUES (UPPER(p_owner), 'queued-by-scheduler'); "
        f"  COMMIT; "
        f"END;"
    )
    try:
        with agent_conn.cursor() as cur:
            cur.execute(proc_sql)
        agent_conn.commit()
    except oracledb.DatabaseError as e:
        return {"ok": False, "reason": f"failed to create {SCAN_PROC}: {e}",
                "job_name": SCAN_JOB, "interval_min": interval_min, "owner": owner}

    try:
        with agent_conn.cursor() as cur:
            # Drop existing job (idempotent recreation).
            try:
                cur.execute(
                    "BEGIN DBMS_SCHEDULER.DROP_JOB(:n, force => TRUE); END;",
                    n=SCAN_JOB,
                )
            except oracledb.DatabaseError:
                pass

            cur.execute(
                "BEGIN "
                "  DBMS_SCHEDULER.CREATE_JOB("
                "    job_name        => :job_name, "
                "    job_type        => 'STORED_PROCEDURE', "
                "    job_action      => :proc, "
                "    number_of_arguments => 1, "
                "    start_date      => SYSTIMESTAMP, "
                "    repeat_interval => :rep, "
                "    enabled         => FALSE); "
                "  DBMS_SCHEDULER.SET_JOB_ARGUMENT_VALUE("
                "    job_name => :job_name, argument_position => 1, argument_value => :owner); "
                "  DBMS_SCHEDULER.ENABLE(:job_name); "
                "END;",
                job_name=SCAN_JOB,
                proc=SCAN_PROC,
                rep=f"FREQ=MINUTELY; INTERVAL={interval_min}",
                owner=owner,
            )
        agent_conn.commit()
    except oracledb.DatabaseError as e:
        return {"ok": False, "reason": f"DBMS_SCHEDULER call failed: {e}",
                "job_name": SCAN_JOB, "interval_min": interval_min, "owner": owner}

    return {"ok": True, "reason": "scheduler ready",
            "job_name": SCAN_JOB, "interval_min": interval_min, "owner": owner}


def drain_queued_scans(agent_conn, memory_client, *, verbose: bool = False) -> int:
    """Process every 'queued-by-scheduler' row in scan_history. For each
    queued row, run the §5 scanner against the named owner and update the
    row's notes/finished_at. Returns the number of scans run.

    Safe to call from app startup or from a periodic foreground sweep — if
    nothing is queued, it's a single SELECT.
    """
    try:
        from retrieval.scanner import run_scan
    except Exception as e:
        print(f"[drain] scanner import failed: {e}")
        return 0

    try:
        with agent_conn.cursor() as cur:
            cur.execute(
                "SELECT scan_id, target_owner FROM scan_history "
                " WHERE notes = 'queued-by-scheduler' "
                "   AND finished_at IS NULL "
                " ORDER BY started_at"
            )
            queued = list(cur)
    except oracledb.DatabaseError as e:
        # Table may not exist yet; that's fine.
        if e.args[0].code == 942:
            return 0
        traceback.print_exc()
        return 0

    ran = 0
    for scan_id, owner in queued:
        try:
            summary = run_scan(agent_conn, memory_client, owner)
            with agent_conn.cursor() as cur:
                cur.execute(
                    "UPDATE scan_history "
                    "   SET objects_scanned = :n, "
                    "       facts_written = :w, "
                    "       finished_at = CURRENT_TIMESTAMP, "
                    "       notes = :notes "
                    " WHERE scan_id = :id",
                    n=summary.get("facts_total", 0),
                    w=summary.get("new", 0) + summary.get("updated", 0),
                    notes=(f"drained: new={summary.get('new', 0)} "
                           f"updated={summary.get('updated', 0)} "
                           f"skipped={summary.get('skipped', 0)}")[:4000],
                    id=scan_id,
                )
            agent_conn.commit()
            ran += 1
            if verbose:
                print(f"[drain] scanned {owner}: {summary}")
        except Exception as e:
            print(f"[drain] {owner} failed: {type(e).__name__}: {e}")
    return ran
