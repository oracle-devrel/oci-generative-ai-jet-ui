# Migration Cutover Strategy

## Overview

Cutover is the moment when the production workload moves from the source database to Oracle. It is the highest-risk phase of any migration project — execution errors at this point can cause data loss, extended downtime, and emergency rollbacks. A well-planned cutover turns this moment into a routine, predictable operational procedure rather than a crisis.

This guide covers the full arc of cutover planning: phases, parallel run strategy, dual-write patterns, go/no-go criteria, rollback planning, minimizing downtime with Oracle GoldenGate, and stakeholder communication.

---

## Cutover Planning Phases

### Phase 1 — Pre-Cutover Preparation (Weeks Before)

The cutover plan should be ready and rehearsed before the migration project even begins. During this phase:

**Technical preparation:**

- [ ] Complete schema migration and data validation (see `migration-data-validation.md`)
- [ ] Complete application code changes (connection strings, SQL dialect adjustments)
- [ ] Performance benchmark critical queries on Oracle — response times acceptable
- [ ] Configure Oracle for production: connection pooling, resource manager, user accounts
- [ ] Set up monitoring: Oracle Enterprise Manager, AWR baselines, alert thresholds
- [ ] Configure Oracle backups: RMAN, Data Guard, snapshot schedule
- [ ] Establish network routes: Oracle listeners accessible from all application hosts
- [ ] Test Oracle from every application server (not just DBAs)
- [ ] Test all reporting tools and ETL pipelines against Oracle target

**Process preparation:**

- [ ] Document the cutover runbook (step-by-step with owners and time estimates)
- [ ] Schedule the cutover window on the change management calendar
- [ ] Notify all stakeholders (business users, support teams, upstream/downstream systems)
- [ ] Prepare rollback runbook with specific decision criteria
- [ ] Book support contacts: application vendors, Oracle support, DBA on call
- [ ] Establish a war room or call bridge for the cutover window

### Phase 2 — Cutover Rehearsal (1–2 Weeks Before)

A dry-run cutover in a staging environment that mirrors production as closely as possible:

```
Rehearsal Checklist:
[ ] Execute the full cutover runbook in staging
[ ] Time each step — record actual duration
[ ] Simulate rollback scenario — practice the rollback runbook
[ ] Test application startup against Oracle staging
[ ] Run smoke tests against Oracle staging
[ ] Identify gaps between runbook and actual execution
[ ] Update runbook with timing corrections and clarifications
[ ] Confirm all team members know their roles
```

The rehearsal should reveal:

- Steps that take longer than estimated
- Missing runbook steps discovered during execution
- Dependency ordering issues
- Team communication gaps

### Phase 3 — Pre-Cutover Day (Day Before)

**24 hours before cutover:**

- [ ] Final incremental data sync — bring Oracle as close to current as possible
- [ ] Freeze non-emergency changes to source database and application
- [ ] Complete final validation queries (row counts, aggregates)
- [ ] Confirm rollback decision deadline: "We will not proceed past T+2h if Oracle is not stable"
- [ ] Brief all team members on roles and the communication plan
- [ ] Verify monitoring is in place for the cutover window
- [ ] Confirm backup of source database is current

### Phase 4 — Cutover Execution

**The cutover window itself — sample timeline:**

```
T-0:00  Announce maintenance window begins. Prevent new connections to source DB.
T-0:05  Verify source DB traffic has drained (active session count = 0 non-admin).
T-0:10  Run final DML on source DB — log the exact timestamp.
T-0:15  Final incremental data sync: export changes since last sync, load to Oracle.
T-0:35  Run validation queries: row counts, critical aggregate comparisons.
T-0:45  GO/NO-GO decision point.
T-0:50  Update connection strings / DNS / load balancer to point to Oracle.
T-0:55  Application servers restart with Oracle connection configuration.
T-1:00  Run application smoke tests (key workflows, login, search, checkout, etc.).
T-1:15  Monitoring check: Oracle CPU, memory, I/O, wait events — all normal?
T-1:20  Open for business: announce maintenance window complete.
T-2:00  Post-cutover monitoring checkpoint: all systems normal? Declare success.
```

### Phase 5 — Post-Cutover Stabilization (48–72 Hours After)

- Heightened monitoring for the first 48–72 hours
- DBAs on standby for performance issues (missing indexes, bad plans, lock contention)
- Application teams available to address any SQL compatibility issues found in production traffic
- Run drift detection queries every hour (see `migration-data-validation.md`)
- Decommission source database only after this stabilization period, not immediately

---

## Parallel Run Strategy

A parallel run operates both databases simultaneously, comparing output to build confidence before committing to Oracle as the authoritative system.

### Read-Only Parallel Run

The simplest form: direct read-only queries (reports, analytics) to Oracle while writes still go to the source database.

```
Application Traffic Split:
  WRITES    → Source Database (authoritative)
  READ queries (reports, dashboards) → Oracle
  Compare report results between systems weekly
```

This approach carries no risk to data integrity and allows you to validate Oracle query performance and results under real workload before cutover.

### Dual-Read with Comparison

A more rigorous parallel run where the same read queries are executed against both databases and results are compared programmatically:

```python
# Application-level dual-read comparison (Python example)
def get_customer_orders(customer_id):
    # Execute against both databases
    source_result = source_db.execute(
        "SELECT order_id, total FROM orders WHERE customer_id = %s ORDER BY order_id",
        (customer_id,)
    ).fetchall()

    oracle_result = oracle_db.execute(
        "SELECT order_id, total FROM orders WHERE customer_id = :1 ORDER BY order_id",
        (customer_id,)
    ).fetchall()

    # Compare results
    if source_result != oracle_result:
        log_discrepancy('customer_orders', customer_id, source_result, oracle_result)

    # Return source result (still authoritative)
    return source_result
```

Log discrepancies to a monitoring table:

```sql
CREATE TABLE parallel_run_discrepancies (
    id              NUMBER GENERATED ALWAYS AS IDENTITY,
    query_name      VARCHAR2(200),
    parameter       VARCHAR2(500),
    source_result   CLOB,
    oracle_result   CLOB,
    logged_at       TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

Review discrepancies daily. Zero discrepancies over a defined period (e.g., 2 business days with representative traffic) is a strong indicator that Oracle is ready.

---

## Dual-Write Pattern

The dual-write pattern writes every data change to both the source and Oracle simultaneously. This keeps Oracle fully synchronized without depending on batch replication, and allows instant cutover of reads.

### Application-Level Dual Write

```python
# Application dual-write (conceptual pattern)
def create_order(customer_id, items, total):
    try:
        # Write to source database first (authoritative)
        with source_db.transaction():
            order_id = source_db.execute(
                "INSERT INTO orders (customer_id, total) VALUES (%s, %s) RETURNING order_id",
                (customer_id, total)
            ).fetchone()[0]
            # insert line items...

        # Write to Oracle (shadow write)
        try:
            with oracle_db.transaction():
                oracle_db.execute(
                    "INSERT INTO orders (order_id, customer_id, total) VALUES (:1, :2, :3)",
                    (order_id, customer_id, total)
                )
                # insert line items...
        except Exception as oracle_err:
            # Log Oracle write failure but do NOT fail the user request
            log_oracle_write_failure('create_order', oracle_err, order_id)

        return order_id

    except Exception as source_err:
        raise  # Source database failures always propagate
```

**Key principles of dual-write:**

1. Source database failures always fail the request
2. Oracle failures are logged but do NOT fail the user-facing operation
3. A reconciliation job runs periodically to detect and correct drift
4. Once Oracle drift falls below an acceptable threshold, switch Oracle to primary

### Database-Level Dual Write (Triggers)

For applications where modifying application code is not feasible, use source-database triggers to replicate changes:

```sql
-- SQL Server trigger replicating to Oracle via linked server
-- (Not recommended for high-throughput systems due to latency)
CREATE TRIGGER tr_orders_replicate
ON orders
AFTER INSERT, UPDATE
AS
BEGIN
    -- This approach adds latency to every write on the source
    -- Only suitable for low-volume tables
    INSERT INTO [OracleLinkedServer]..orders (order_id, customer_id, total, order_date)
    SELECT order_id, customer_id, total, order_date FROM inserted;
END;
```

### Preferred Approach: Change Data Capture + Oracle GoldenGate

For production migrations, Oracle GoldenGate provides real-time, low-latency replication without application changes:

```
Source DB ──[GoldenGate Extract]──► Trail Files ──[GoldenGate Replicat]──► Oracle Target
                                                         ^
                                             (lag typically < 1 second)
```

During the parallel run period, GoldenGate continuously applies changes from source to Oracle. At cutover, the only downtime is the time needed for the lag to drain to zero and the application to reconnect.

---

## Go/No-Go Criteria Checklist

This checklist must be completed and approved **at the go/no-go decision point** during cutover. If any mandatory item is not PASS, do not proceed — execute the rollback plan.

### Mandatory (Must All Pass)

| Criterion                 | Threshold                       | Check Method            | Result |
| ------------------------- | ------------------------------- | ----------------------- | ------ |
| Row count validation      | 100% match for all tables       | SQL comparison queries  |        |
| Financial aggregate match | < 0.001% difference             | SUM(amount) comparison  |        |
| Constraint violations     | 0 violations                    | ALTER TABLE VALIDATE    |        |
| Application smoke tests   | 100% pass                       | Automated test suite    |        |
| Oracle error rate         | 0 ORA- errors in smoke test     | Oracle alert log        |        |
| Response time — P50       | < 2× source baseline            | Load test or benchmark  |        |
| Response time — P99       | < 5× source baseline            | Load test or benchmark  |        |
| Rollback plan tested      | Rollback rehearsed successfully | Rehearsal documentation |        |
| Support team available    | DBA, App, Network on standby    | Call confirmation       |        |
| Monitoring active         | All dashboards green            | OEM / custom monitoring |        |

### Advisory (Failures May Delay Cutover)

| Criterion                  | Threshold                      | Action if Not Met                |
| -------------------------- | ------------------------------ | -------------------------------- |
| GoldenGate replication lag | < 10 seconds                   | Wait for lag to drain            |
| Oracle SGA/PGA usage       | < 80%                          | Resize if needed                 |
| Oracle redo log switches   | < 4 per hour                   | Resize redo logs if thrashing    |
| Batch jobs validated       | All critical batch jobs tested | Schedule post-cutover validation |

---

## Rollback Plan

A rollback plan must be defined, documented, and rehearsed before cutover begins. Define a clear rollback deadline — a specific time after cutover starts at which you will automatically initiate rollback if Oracle is not stable.

### Rollback Decision Triggers

Automatically initiate rollback if ANY of the following occur within the rollback window:

- Oracle is returning errors for > 5% of requests for more than 5 consecutive minutes
- A critical application workflow is completely broken (login, checkout, data save)
- Oracle performance is > 10× worse than source baseline for P99 latency
- Data corruption detected (validation query returns unexpected results)
- Oracle instance crashes or becomes unreachable

### Rollback Runbook

```
ROLLBACK PROCEDURE — Execute only with explicit approval from Incident Commander

T+0:00  Declare rollback initiated. Notify all stakeholders.
T+0:02  Stop all application servers.
T+0:05  Revert connection strings / DNS to point to source database.
T+0:08  Verify source database is still accessible and current.
T+0:10  Restart application servers against source database.
T+0:15  Application smoke tests against source database — all pass?
T+0:20  Reopen service to users.
T+0:25  Begin incident review: capture Oracle alert logs, OEM snapshot, application logs.
T+1:00  Post-mortem meeting: identify root cause, plan remediation, schedule re-migration.
```

### Preserving Source Database During Rollback Window

Never decommission the source database until the rollback window has closed (typically 48–72 hours after cutover):

```sql
-- Oracle: document rollback deadline in a migration log
CREATE TABLE migration_log (
    event_type    VARCHAR2(50),
    event_time    TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP,
    details       VARCHAR2(2000),
    operator      VARCHAR2(100) DEFAULT USER
);

INSERT INTO migration_log (event_type, details)
VALUES ('CUTOVER_COMPLETE', 'Production cutover completed. Source DB remains live until ' ||
        TO_CHAR(SYSTIMESTAMP + INTERVAL '72' HOUR, 'YYYY-MM-DD HH24:MI TZR'));
COMMIT;
```

---

## Minimizing Downtime with GoldenGate Replication

Oracle GoldenGate is the industry-standard tool for near-zero-downtime database migration. Here is the high-level architecture and cutover procedure:

### GoldenGate Setup for Near-Zero Downtime

**Phase 1 — Initial bulk load (while GoldenGate captures changes):**

```bash
# Start GoldenGate Extract on source (begin capturing changes from this SCN/LSN)
GGSCI> ADD EXTRACT ext_src, TRANLOG, BEGIN NOW
GGSCI> ADD EXTTRAIL ./dirdat/et, EXTRACT ext_src
GGSCI> START EXTRACT ext_src

# While GoldenGate is capturing, perform initial bulk load via Data Pump or SQL*Loader
# This can take hours for large databases
expdp source_user/pass TABLES=... DUMPFILE=initial_load.dmp
impdp oracle_user/pass DUMPFILE=initial_load.dmp TABLE_EXISTS_ACTION=APPEND
```

**Phase 2 — GoldenGate replication applies accumulated changes:**

```bash
# Configure Replicat on Oracle target
GGSCI> ADD REPLICAT rep_tgt, INTEGRATED, EXTTRAIL ./dirdat/rt
GGSCI> START REPLICAT rep_tgt

# Monitor replication lag
GGSCI> INFO REPLICAT rep_tgt
# Watch "Lag at Chkpt" — when it approaches 0, you're ready
```

**Phase 3 — Cutover (lag approaches zero):**

```bash
# When lag < 5 seconds:
# 1. Stop new writes to source (application maintenance mode)
# 2. Wait for GoldenGate lag to reach 0
GGSCI> STATS REPLICAT rep_tgt, TOTALSONLY *
# 3. Confirm Oracle row counts match source
# 4. Switch application connections to Oracle
# 5. Stop GoldenGate processes
GGSCI> STOP EXTRACT ext_src
GGSCI> STOP REPLICAT rep_tgt
```

### GoldenGate Parameter Files

```
-- GoldenGate Extract parameter file (ext_src.prm)
EXTRACT ext_src
SOURCEDB mydb, USERID gg_user, PASSWORD gg_pass
EXTTRAIL ./dirdat/et
GETTRUNCATES
TABLE myschema.*;

-- GoldenGate Replicat parameter file (rep_tgt.prm)
REPLICAT rep_tgt
TARGETDB oracle_db USERID gg_user PASSWORD gg_pass
MAP myschema.*, TARGET myschema.*;
-- Handle sequence updates
SEQNO SQLEXEC (ID upd_seq, QUERY "BEGIN EXECUTE IMMEDIATE 'ALTER SEQUENCE &3 RESTART START WITH ' || :1; END;", PARAMS (v_seqno))
```

### Expected GoldenGate Downtime

| Scenario                      | Expected Cutover Window              |
| ----------------------------- | ------------------------------------ |
| Small schema (< 50 GB)        | 15–30 minutes                        |
| Medium schema (50–500 GB)     | 30–90 minutes                        |
| Large schema (> 500 GB)       | 60–240 minutes (for final sync only) |
| GoldenGate with near-zero lag | 2–10 minutes                         |

---

## Communicating Cutover to Stakeholders

### 4-Week Communication Timeline

**4 weeks before cutover:**

- Announce planned maintenance window to all business users
- Identify impacted downstream systems and notify their owners
- Request testing participation from key business users

**2 weeks before:**

- Confirm maintenance window with IT management sign-off
- Send detailed impact summary: expected downtime, affected services
- Schedule go/no-go call with decision-makers

**1 week before:**

- Final reminder to all users
- Confirm support team availability roster
- Distribute escalation contact list

**Day before:**

- Final confirmation email with exact window times
- Confirm war room bridge / chat channel
- Verify everyone knows the rollback decision deadline

**Cutover day:**

- Send "maintenance starting" notification at window open
- Provide status updates every 30 minutes during window
- Send "migration complete" notification when service restored
- Send post-cutover summary within 2 hours of completion

### Sample Stakeholder Communication

```
Subject: [ACTION REQUIRED] Database Migration Maintenance Window — Saturday Mar 15, 2AM-6AM EST

Team,

We will be migrating our production database to Oracle on Saturday, March 15 from 2:00 AM to
6:00 AM EST. The following systems will be UNAVAILABLE during this window:

  - Customer Portal (portal.company.com)
  - Order Management System
  - Reporting Dashboard

IMPACT: No orders can be placed or modified during this window.
AFFECTED USERS: All users of the above systems.
ROLLBACK PLAN: If issues are detected, we will revert within 2 hours. Maximum possible impact is a
4-hour outage, with a target of 2 hours.

ACTION REQUIRED: If you have scheduled jobs or automated processes that run during this window,
contact [dba-team@company.com] to coordinate.

Questions or concerns? Contact: [migration-project@company.com]
```

---

## Post-Cutover Checklist

Complete this checklist in the 72 hours following a successful cutover:

**Hour 0–4 (immediate post-cutover):**

- [ ] Application smoke tests passed
- [ ] Oracle error log clean (no ORA- errors from application activity)
- [ ] Performance monitoring baseline established
- [ ] GoldenGate stopped and configuration archived

**Hours 4–24:**

- [ ] Full business day of traffic processed without incidents
- [ ] All scheduled batch jobs ran successfully on Oracle
- [ ] Reporting and analytics tools verified against Oracle data
- [ ] Row count drift check — still zero drift

**Hours 24–72:**

- [ ] All weekly/bi-weekly batch processes tested on Oracle
- [ ] Source database decommission checklist initiated (if rollback window closed)
- [ ] Post-mortem document drafted: what went well, what to improve
- [ ] Migration project formally closed and documented
- [ ] Oracle monitoring tuned based on first 72 hours of production patterns
- [ ] AWR baseline created from first week of production data

---

## Best Practices

1. **Never skip the dry run.** Performing the cutover runbook in staging reveals timing issues, missing steps, and team coordination gaps that would cause extended downtime in production.

2. **Define the rollback deadline in writing.** "We will rollback if Oracle is not stable by T+2 hours" must be agreed in advance by all stakeholders. Without a pre-committed deadline, the pressure of the moment can lead to continuing with an unstable system for too long.

3. **Make connection string changes atomic.** Use a load balancer, service mesh, or DNS-based redirect for Oracle connection switching. This allows instantaneous rollback of connectivity without restarting applications one by one.

4. **Do not decommission the source database immediately.** Keep the source database read-only and available for at least 72 hours after cutover. This is your safety net for unexpected issues.

5. **Plan for the unexpected.** Every migration encounters at least one issue not anticipated during planning. The cutover window must have buffer time built in (30–50% of estimated active work time) for unexpected debugging.

6. **Treat cutover as a product launch.** All the communication, monitoring, and stakeholder coordination disciplines of a major product launch apply. The technical work is the easy part; the coordination and communication determine the experience.

---

## Common Cutover Pitfalls

**Pitfall 1 — Forgetting to update connection strings in all locations.**
Connection strings exist in: application config files, environment variables, docker/k8s secrets, LDAP/directory services, JDBC datasource pools, hard-coded values in legacy code, reporting tool configurations, ETL pipeline configurations, and monitoring probes. Create a complete inventory before cutover.

**Pitfall 2 — Oracle sequence values behind the source.**
After data migration, Oracle sequences must be reset to values higher than any existing ID. If sequences are not updated before the application starts writing, INSERT statements will fail with ORA-00001 (unique constraint violated).

```sql
-- Reset all sequences post-migration
BEGIN
    FOR t IN (SELECT table_name, column_name FROM (
        SELECT 'CUSTOMERS' AS table_name, 'CUSTOMER_ID' AS column_name FROM DUAL
        UNION ALL SELECT 'ORDERS', 'ORDER_ID' FROM DUAL
        UNION ALL SELECT 'PRODUCTS', 'PRODUCT_ID' FROM DUAL
    )) LOOP
        EXECUTE IMMEDIATE
            'ALTER TABLE ' || t.table_name || ' MODIFY ' || t.column_name ||
            ' GENERATED ALWAYS AS IDENTITY (START WITH LIMIT VALUE)';
    END LOOP;
END;
/
```

**Pitfall 3 — Time zone misconfiguration.**
Oracle session time zone defaults to the OS time zone of the database server. If the application was connecting to a UTC source database but Oracle is configured for a local time zone, timestamp values may be offset. Set Oracle session time zone explicitly:

```sql
ALTER SESSION SET TIME_ZONE = 'UTC';
-- Or in connection string: jdbc:oracle:thin:@host:1521/db?oracle.jdbc.defaultTimeZone=UTC
```

**Pitfall 4 — Missing grants for the new Oracle schema.**
Application users need appropriate privileges in Oracle. A common oversight is forgetting to grant access to sequences, synonyms, or procedures that were not in the original migration scope.

**Pitfall 5 — Performance regression on first production queries.**
Oracle's optimizer builds statistics over time. The first executions of complex queries may use non-optimal plans because statistics are based on the initial data load, not the pattern of production queries. Monitor the top wait events in V$SESSION_WAIT immediately after cutover and address any slow queries proactively.

---

## Oracle Version Notes (19c vs 26ai)

- Baseline guidance in this file is valid for Oracle Database 19c unless a newer minimum version is explicitly called out.
- Features marked as 21c, 23c, or 23ai should be treated as Oracle Database 26ai-capable features; keep 19c-compatible alternatives for mixed-version estates.
- For dual-support environments, test syntax and package behavior in both 19c and 26ai because defaults and deprecations can differ by release update.

## Sources

- [Oracle Zero Downtime Migration documentation](https://docs.oracle.com/en/database/oracle/zero-downtime-migration/index.html)
- [Oracle GoldenGate 19c documentation](https://docs.oracle.com/en/middleware/goldengate/core/19.1/index.html)
- [Oracle Database 19c SQL Language Reference — ALTER TABLE (MODIFY GENERATED AS IDENTITY)](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/ALTER-TABLE.html)
