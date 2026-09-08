# Part 10: Continuous Scans via DBMS_SCHEDULER

The Part 2 scanner runs once on demand. **Part 10 moves it onto a schedule** — `DBMS_SCHEDULER` queues scan requests, the harness drains them when it's running. Schemas drift; this Part keeps the agent's institutional knowledge from going stale.

## Two ideas in one cell

1. **Incremental scans are already cheap.** The `body_hash` check from Part 2 means a re-scan only re-embeds facts whose underlying text changed. So running `run_scan(conn, "SUPPLYCHAIN")` every hour is viable — the vast majority of calls hash-check and skip. That's the minimum you need for continuous knowledge; everything below makes it *operationally* nicer.

2. **Periodic scans via `DBMS_SCHEDULER`.** A scan you only run manually isn't very institutional — schemas drift, new tables land, query patterns change. We want re-scans on a cadence. The natural place for that schedule is **inside the database**.

## Why put the schedule in the database?

| Reason | Detail |
|---|---|
| **Lifecycle** | The DB scheduler keeps running when the harness kernel is gone, when your laptop is asleep, when you reboot. |
| **Operational surface** | `DBA_SCHEDULER_JOB_RUN_DETAILS` is a real audit trail; you can query it, alert on failures, suspend during a freeze. |

## Two ways to bridge `DBMS_SCHEDULER` and Python

`DBMS_SCHEDULER` runs PL/SQL, not our Python `scan_schema`. Two ways to bridge:

1. **Rewrite the scanner in PL/SQL.** Mine the catalog views, build the fact body in PL/SQL, INSERT directly into the OAMP memory table with `VECTOR_EMBEDDING(...)` for the embedding column. Zero Python in the loop — fully autonomous. It's the right end state, but it couples to OAMP's internal table layout (the `eda_onnx_*` schema).

2. **Use the scheduler as a *trigger*.** A tiny PL/SQL proc just *requests* a scan by writing a queued `scan_history` row. The harness, when next running, polls for queued rows and runs `run_scan(owner)` on each. This keeps the scan logic in one place (`scan_schema`), gives you a durable schedule, and stays decoupled from OAMP's internals.

The notebook wires up #2 as the default. The cell is opt-in via `RUN_SCHEDULER=1` so it doesn't create a job on every kernel run.

## What's pre-built

The Part 10 cells handle:

- **Migration of `scan_history.notes`** from `CLOB` to `VARCHAR2(4000)`. The original DDL made `notes` a CLOB, but the queue check is `WHERE notes = 'queued-by-scheduler'` and `ORA-22848` forbids CLOB equality comparisons. Idempotent — only runs if the column is still CLOB.

- **`AGENT_REQUEST_SCAN(p_owner)` procedure** — the `DBMS_SCHEDULER` job calls this. It just inserts a queued row:

  ```sql
  CREATE OR REPLACE PROCEDURE AGENT_REQUEST_SCAN(p_owner IN VARCHAR2) AS
  BEGIN
      INSERT INTO scan_history (target_owner, notes)
      VALUES (UPPER(p_owner), 'queued-by-scheduler');
      COMMIT;
  END;
  ```

- **`DBMS_SCHEDULER.CREATE_JOB`** — schedules `AGENT_REQUEST_SCAN(SUPPLYCHAIN)` every `SCAN_INTERVAL_MIN` minutes (default 60).

- **`drain_queued_scans()` Python helper** — call from your agent loop, a worker process, or inline before a demo. For each `queued-by-scheduler` row in `scan_history`, runs `run_scan` and updates the row's `notes`/`finished_at` with the actual outcome.

## How a real deployment uses this

In production, the harness runs as a service. The pattern is:

1. The scheduler queues `scan_history` rows on its cadence (every hour, say).
2. Every N minutes, your service worker calls `drain_queued_scans()`. It picks up any rows the scheduler created since the last drain and runs scans for each.
3. The scanner's `body_hash` dedup means most scans are no-ops at the OAMP level — only changed facts re-embed.

## Inspect the scheduler

```sql
-- Did the job run?
SELECT log_date, status, run_duration
  FROM user_scheduler_job_run_details
 WHERE job_name = 'AGENT_PERIODIC_SCAN'
 ORDER BY log_date DESC FETCH FIRST 5 ROWS ONLY;

-- What's queued right now?
SELECT scan_id, target_owner, started_at, notes
  FROM scan_history
 WHERE notes = 'queued-by-scheduler'
   AND finished_at IS NULL;

-- What did the latest drains accomplish?
SELECT scan_id, target_owner, started_at, finished_at, notes
  FROM scan_history
 WHERE finished_at IS NOT NULL
 ORDER BY finished_at DESC
 FETCH FIRST 5 ROWS ONLY;
```

## Key Takeaways — Part 10

- **Schemas drift; institutional knowledge must drift with them.** A one-shot scan on day zero rots. The agent's "what tables exist" answer must track reality, not training-day reality.
- **Scheduler-as-trigger beats rewriting in PL/SQL.** `DBMS_SCHEDULER` queues a row, the harness drains it on its own cadence — Python logic stays in one place, the database owns the schedule.
- **Lifecycle outlives the kernel.** A `dbms_scheduler` job keeps running when your laptop sleeps, when the kernel restarts, when you bounce the container. `DBA_SCHEDULER_JOB_RUN_DETAILS` is the audit trail.

## Troubleshooting

**`ORA-22848: cannot use CLOB type as comparison key`** — the `scan_history.notes` migration didn't run. The pre-built cell handles this; if you skipped it, run the migration cell.

**Scheduler job created but never fires** — check `enabled = 'TRUE'` in `user_scheduler_jobs`. The pre-built cell calls `DBMS_SCHEDULER.ENABLE` after `CREATE_JOB`; on some images you may need to run it manually.

**`drain_queued_scans` returns 0** — no rows are queued. Either the scheduler hasn't fired yet (interval too long), or the scheduler isn't running. Check `user_scheduler_job_run_details`.
