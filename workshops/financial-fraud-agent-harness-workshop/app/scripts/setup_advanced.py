"""Advanced setup — runs after bootstrap.py and seed.py.

Installs the parts of the workshop that aren't covered by bootstrap (AGENT user,
ONNX, DBFS, vector pool) or seed (FINANCE, duality views, skillbox):

  1. Oracle Text CTXSYS.CONTEXT index on the OAMP memory body
     (required for the Part 3 hybrid RRF retrieval).
  2. DDS / DBMS_RLS row policy on FINANCE.transactions (filters by region)
     and column mask on FINANCE.transactions.amount_cents
     (identity-aware authorization).
  3. AGENT_REQUEST_SCAN procedure + DBMS_SCHEDULER job + scan_history table
     (Part 10 — continuous scans).

Idempotent. Re-runs are safe.

Usage:
    cd app && python scripts/setup_advanced.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def ensure_text_index(agent_conn):
    """Oracle Text CONTEXT index on the OAMP memory body — for hybrid retrieval."""
    TEXT_INDEX_NAME = "eda_memory_text_idx"
    MEMORY_TABLE    = "eda_onnx_memory"

    with agent_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM user_indexes "
            " WHERE index_name = :n AND table_name = :t",
            n=TEXT_INDEX_NAME.upper(), t=MEMORY_TABLE.upper(),
        )
        if cur.fetchone()[0] > 0:
            print(f"  [text index] {TEXT_INDEX_NAME} already exists — skipping")
            return

        import oracledb
        try:
            cur.execute(
                f"CREATE INDEX {TEXT_INDEX_NAME} "
                f"  ON {MEMORY_TABLE}(content) "
                f"  INDEXTYPE IS CTXSYS.CONTEXT "
                f"  PARAMETERS ('SYNC (ON COMMIT)')"
            )
            print(f"  [text index] created {TEXT_INDEX_NAME} on {MEMORY_TABLE}.content")
        except oracledb.DatabaseError as e:
            if e.args[0].code == 29855:
                cur.execute(
                    f"CREATE INDEX {TEXT_INDEX_NAME} ON {MEMORY_TABLE}(content) "
                    f"  INDEXTYPE IS CTXSYS.CONTEXT"
                )
                print(f"  [text index] created {TEXT_INDEX_NAME} (no SYNC ON COMMIT)")
            else:
                raise
    agent_conn.commit()


def ensure_dds_policies(sys_conn, agent_conn, demo_user="FINANCE", agent_user="AGENT"):
    """DDS row policy on transactions.region + column mask on transactions.amount_cents.
    Falls back to DBMS_RLS when the declarative DDS DDL isn't on this image."""
    import oracledb

    # setup_deep_security.py owns the identity rules once it has run (EDA_*
    # policies, the full persona rule tables, its own setter). Re-running this
    # older, narrower installer on top would DELETE and reseed the rule tables
    # without the `agent` persona (so `agent` would see no transactions) and
    # stack two legacy policies on FINANCE.TRANSACTIONS.
    with agent_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM all_policies "
            " WHERE object_owner = :o AND policy_name LIKE 'EDA\\_%' ESCAPE '\\'",
            o=demo_user.upper(),
        )
        if cur.fetchone()[0]:
            print("  [dds] identity rules already installed by setup_deep_security.py "
                  "— leaving them untouched")
            return

    # --- Authorization + clearance tables in AGENT schema ---
    DDS_DDL = [
        ("agent_authorizations", (
            "CREATE TABLE agent_authorizations ("
            "  end_user     VARCHAR2(128) NOT NULL,"
            "  auth_region  VARCHAR2(20)  NOT NULL,"
            "  PRIMARY KEY (end_user, auth_region))"
        )),
        ("agent_clearances", (
            "CREATE TABLE agent_clearances ("
            "  end_user   VARCHAR2(128) PRIMARY KEY,"
            "  clearance  VARCHAR2(32)  NOT NULL,"
            "  notes      VARCHAR2(400))"
        )),
    ]

    with agent_conn.cursor() as cur:
        for tname, ddl in DDS_DDL:
            try:
                cur.execute(ddl)
                print(f"  [dds] created {tname}")
            except oracledb.DatabaseError as e:
                if e.args[0].code != 955:
                    raise

        cur.execute("DELETE FROM agent_authorizations")
        cur.executemany(
            "INSERT INTO agent_authorizations (end_user, auth_region) VALUES (:1, :2)",
            [
                ("analyst.east@meridianbank.example", "EUROPE"),
                ("analyst.east@meridianbank.example", "MIDDLE_EAST"),
                ("analyst.west@meridianbank.example", "AMERICAS"),
                ("analyst.west@meridianbank.example", "ASIA_PACIFIC"),
                ("ops.viewer@meridianbank.example",   "ALL"),
                ("compliance.officer@meridianbank.example", "ALL"),
                ("cfo@meridianbank.example",          "ALL"),
            ],
        )
        cur.execute("DELETE FROM agent_clearances")
        cur.executemany(
            "INSERT INTO agent_clearances (end_user, clearance, notes) VALUES (:1, :2, :3)",
            [
                ("analyst.east@meridianbank.example",  "STANDARD",  "Europe + Middle East regional analyst"),
                ("analyst.west@meridianbank.example",  "STANDARD",  "Americas + Asia-Pacific regional analyst"),
                ("ops.viewer@meridianbank.example",    "STANDARD",  "Read-only risk-ops viewer"),
                ("compliance.officer@meridianbank.example", "EXECUTIVE", "AML compliance officer (SAR access)"),
                ("cfo@meridianbank.example",           "EXECUTIVE", "Chief Financial Officer"),
            ],
        )
    agent_conn.commit()

    with sys_conn.cursor() as cur:
        cur.execute(f"GRANT SELECT ON {agent_user}.agent_authorizations TO {demo_user}")
        cur.execute(f"GRANT SELECT ON {agent_user}.agent_clearances     TO {demo_user}")
    sys_conn.commit()
    print(f"  [dds] seeded authorizations + clearances")

    # --- EDA_CTX namespace + setter procedure ---
    SETTER_SQL = """
    CREATE OR REPLACE PROCEDURE set_eda_ctx(
        p_end_user  IN VARCHAR2,
        p_clearance IN VARCHAR2 DEFAULT NULL
    ) AS
        v_clearance VARCHAR2(32);
    BEGIN
        IF p_clearance IS NULL AND p_end_user IS NOT NULL THEN
            BEGIN
                SELECT clearance INTO v_clearance
                  FROM agent_clearances WHERE end_user = p_end_user;
            EXCEPTION WHEN NO_DATA_FOUND THEN
                v_clearance := 'STANDARD';
            END;
        ELSE
            v_clearance := NVL(p_clearance, 'STANDARD');
        END IF;
        DBMS_SESSION.SET_CONTEXT('EDA_CTX', 'END_USER',  p_end_user);
        DBMS_SESSION.SET_CONTEXT('EDA_CTX', 'CLEARANCE', v_clearance);
    END;
    """
    with agent_conn.cursor() as cur:
        cur.execute(SETTER_SQL)
    print(f"  [dds] created procedure {agent_user}.set_eda_ctx")

    try:
        with agent_conn.cursor() as cur:
            cur.execute(f"CREATE OR REPLACE CONTEXT eda_ctx USING {agent_user}.set_eda_ctx")
        print(f"  [dds] created namespace EDA_CTX (writes restricted to set_eda_ctx)")
    except oracledb.DatabaseError:
        with sys_conn.cursor() as cur:
            cur.execute(f"GRANT CREATE ANY CONTEXT TO {agent_user}")
            cur.execute(f"CREATE OR REPLACE CONTEXT eda_ctx USING {agent_user}.set_eda_ctx")
        print(f"  [dds] granted CREATE ANY CONTEXT, created EDA_CTX")

    # --- Get the demo connection to install policies on FINANCE.transactions ---
    demo_pass = os.environ.get("ORACLE_DEMO_PASS", "FinancePwd_2025")
    dsn = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")
    demo_conn = oracledb.connect(user=demo_user, password=demo_pass, dsn=dsn)

    # Try declarative DDS first; fall back to DBMS_RLS.
    ROW_POLICY_DDS = """
    CREATE DATA SECURITY POLICY transactions_region_policy
    ON transactions
    USING (
        SYS_CONTEXT('EDA_CTX','END_USER') IS NULL
     OR EXISTS (
            SELECT 1 FROM AGENT.agent_authorizations a
             WHERE a.end_user = SYS_CONTEXT('EDA_CTX','END_USER')
               AND (a.auth_region = 'ALL' OR a.auth_region = transactions.region)
        )
    )
    """
    COL_POLICY_DDS = """
    CREATE DATA SECURITY POLICY amount_cents_policy
    ON transactions
    HIDE COLUMNS (amount_cents)
    WHEN SYS_CONTEXT('EDA_CTX','END_USER') IS NOT NULL
     AND COALESCE(SYS_CONTEXT('EDA_CTX','CLEARANCE'),'STANDARD') <> 'EXECUTIVE'
    """

    for stmt in [
        "DROP DATA SECURITY POLICY transactions_region_policy",
        "DROP DATA SECURITY POLICY amount_cents_policy",
    ]:
        try:
            with demo_conn.cursor() as cur:
                cur.execute(stmt)
        except oracledb.DatabaseError:
            pass

    fallback_codes = {900, 901, 922, 2000, 942, 1031}
    dds_unsupported = False

    for label, ddl in [
        ("row policy on transactions", ROW_POLICY_DDS),
        ("col mask on transactions", COL_POLICY_DDS),
    ]:
        try:
            with demo_conn.cursor() as cur:
                cur.execute(ddl)
            print(f"  [dds] declarative: {label}")
        except oracledb.DatabaseError as e:
            if e.args[0].code in fallback_codes:
                print(f"  [dds] declarative not available (ORA-{e.args[0].code}) — falling back to DBMS_RLS")
                dds_unsupported = True
                break
            raise

    if dds_unsupported:
        with sys_conn.cursor() as cur:
            try:
                cur.execute(f"GRANT EXECUTE ON SYS.DBMS_RLS TO {demo_user}")
            except oracledb.DatabaseError as e:
                if e.args[0].code != 1031:
                    raise
        sys_conn.commit()

        DROP_BLOCK = """
DECLARE
  e_no_policy EXCEPTION;
  PRAGMA EXCEPTION_INIT(e_no_policy, -28102);
BEGIN
  BEGIN DBMS_RLS.DROP_POLICY(:s, 'TRANSACTIONS', 'TRANSACTIONS_REGION_POLICY');
  EXCEPTION WHEN e_no_policy THEN NULL; END;
  BEGIN DBMS_RLS.DROP_POLICY(:s, 'TRANSACTIONS', 'AMOUNT_CENTS_POLICY');
  EXCEPTION WHEN e_no_policy THEN NULL; END;
END;
"""
        with demo_conn.cursor() as cur:
            try:
                cur.execute(DROP_BLOCK, s=demo_user)
            except oracledb.DatabaseError:
                pass

        PRED_TRANSACTIONS = """
CREATE OR REPLACE FUNCTION transactions_region_predicate(
    p_schema IN VARCHAR2, p_object IN VARCHAR2
) RETURN VARCHAR2 AS
BEGIN
    IF SYS_CONTEXT('EDA_CTX','END_USER') IS NULL THEN RETURN '1=1'; END IF;
    RETURN q'[EXISTS (
        SELECT 1 FROM AGENT.agent_authorizations a
         WHERE a.end_user = SYS_CONTEXT('EDA_CTX','END_USER')
           AND (a.auth_region = 'ALL' OR a.auth_region = region))]';
END;
"""
        PRED_AMOUNT = """
CREATE OR REPLACE FUNCTION amount_cents_predicate(
    p_schema IN VARCHAR2, p_object IN VARCHAR2
) RETURN VARCHAR2 AS
BEGIN
    IF SYS_CONTEXT('EDA_CTX','END_USER') IS NULL THEN RETURN '1=1'; END IF;
    IF NVL(SYS_CONTEXT('EDA_CTX','CLEARANCE'),'STANDARD') = 'EXECUTIVE' THEN RETURN '1=1'; END IF;
    RETURN '1=0';
END;
"""
        with demo_conn.cursor() as cur:
            cur.execute(PRED_TRANSACTIONS)
            cur.execute(PRED_AMOUNT)
            cur.execute("""
BEGIN
  DBMS_RLS.ADD_POLICY(
    object_schema => :s, object_name => 'TRANSACTIONS',
    policy_name => 'TRANSACTIONS_REGION_POLICY',
    function_schema => :s, policy_function => 'TRANSACTIONS_REGION_PREDICATE',
    statement_types => 'SELECT');
END;
""", s=demo_user)
            cur.execute("""
BEGIN
  DBMS_RLS.ADD_POLICY(
    object_schema => :s, object_name => 'TRANSACTIONS',
    policy_name => 'AMOUNT_CENTS_POLICY',
    function_schema => :s, policy_function => 'AMOUNT_CENTS_PREDICATE',
    statement_types => 'SELECT',
    sec_relevant_cols => 'AMOUNT_CENTS',
    sec_relevant_cols_opt => DBMS_RLS.ALL_ROWS);
END;
""", s=demo_user)
        print(f"  [dds] DBMS_RLS policies installed")

    demo_conn.close()


def ensure_scheduler(agent_conn, demo_user="FINANCE"):
    """scan_history bookkeeping + AGENT_REQUEST_SCAN procedure + DBMS_SCHEDULER job."""
    import oracledb

    with agent_conn.cursor() as cur:
        try:
            cur.execute(
                "CREATE TABLE scan_history ("
                "  scan_id          VARCHAR2(64) DEFAULT SYS_GUID() PRIMARY KEY,"
                "  target_owner     VARCHAR2(128) NOT NULL,"
                "  objects_scanned  NUMBER,"
                "  facts_written    NUMBER,"
                "  notes            VARCHAR2(4000),"
                "  started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
                "  finished_at      TIMESTAMP)"
            )
            print("  [scheduler] created scan_history")
        except oracledb.DatabaseError as e:
            if e.args[0].code != 955:
                raise
            print("  [scheduler] scan_history already exists")
    agent_conn.commit()

    SCAN_PROC = "AGENT_REQUEST_SCAN"
    SCAN_JOB  = "AGENT_PERIODIC_SCAN"
    INTERVAL_MIN = int(os.environ.get("SCAN_INTERVAL_MIN", "60"))

    proc_sql = f"""
    CREATE OR REPLACE PROCEDURE {SCAN_PROC}(p_owner IN VARCHAR2) AS
    BEGIN
      INSERT INTO scan_history (target_owner, notes)
      VALUES (UPPER(p_owner), 'queued-by-scheduler');
      COMMIT;
    END;
    """
    with agent_conn.cursor() as cur:
        cur.execute(proc_sql)
    print(f"  [scheduler] created procedure {SCAN_PROC}")

    with agent_conn.cursor() as cur:
        try:
            cur.execute("BEGIN DBMS_SCHEDULER.DROP_JOB(:n, force => TRUE); END;", n=SCAN_JOB)
        except oracledb.DatabaseError:
            pass
        cur.execute(
            "BEGIN "
            "  DBMS_SCHEDULER.CREATE_JOB("
            "    job_name => :job_name, job_type => 'STORED_PROCEDURE', "
            "    job_action => :proc, number_of_arguments => 1, "
            "    start_date => SYSTIMESTAMP, repeat_interval => :rep, "
            "    enabled => FALSE); "
            "  DBMS_SCHEDULER.SET_JOB_ARGUMENT_VALUE("
            "    job_name => :job_name, argument_position => 1, argument_value => :owner); "
            "  DBMS_SCHEDULER.ENABLE(:job_name); "
            "END;",
            job_name=SCAN_JOB, proc=SCAN_PROC,
            rep=f"FREQ=MINUTELY; INTERVAL={INTERVAL_MIN}",
            owner=demo_user.upper(),
        )
    agent_conn.commit()
    print(f"  [scheduler] scheduled job {SCAN_JOB} -> {SCAN_PROC}({demo_user!r}) every {INTERVAL_MIN}min")


def main():
    from config import AGENT_USER, DEMO_USER
    from db.connection import connect_sys, connect_agent

    print("\n=== Advanced setup: text index + DDS policies + scheduler ===\n")

    sys_conn = connect_sys()
    agent_conn = connect_agent()

    print("\n[1/3] Oracle Text index on OAMP memory...")
    ensure_text_index(agent_conn)

    print("\n[2/3] DDS / DBMS_RLS row + column policies...")
    ensure_dds_policies(sys_conn, agent_conn, demo_user=DEMO_USER, agent_user=AGENT_USER)

    print("\n[3/3] DBMS_SCHEDULER job + scan_history bookkeeping...")
    ensure_scheduler(agent_conn, demo_user=DEMO_USER)

    print("\n=== Advanced setup complete ===")


if __name__ == "__main__":
    main()
