"""Identity-aware data access: probe, install, and prove it.

Run after `setup_advanced.py`. This script is the DB-layer companion to
`api/identities.py`: it turns the persona registry into policy that the
*database* enforces, using whichever backend the connected release supports.

    python scripts/setup_deep_security.py            # probe + install
    python scripts/setup_deep_security.py --demo     # + same-SQL/different-persona proof
    python scripts/setup_deep_security.py --ddl-only # write the Deep Sec DDL, touch nothing

Backends (see `db/deep_security.py`):

    DEEP_SEC   a 26ai Enterprise-class database runs the real thing: data roles,
               data grants, end users, application identity. On top of that,
               oracleagentmemory >= 26.8 can place the agent's *own* memory
               store under Deep Sec (UserOwnRows + GlobalMemories policies);
               this script installs those policies too when the target and the
               installed SDK support them.
    VPD        Oracle AI Database 26ai Free (the shipped Codespace) cannot — it
               has no DBMS_DEEP_SEC and rejects every Deep Sec DDL form with
               ORA-00901. Equivalant semantics are installed as DBMS_RLS
               policies driven by the EDA_CTX application context. The OAMP
               memory-store policies need data roles/data grants, so on Free
               they are reported and skipped, not faked.

Either way the rule set comes from one place — `api/identities.py` — so the
kernel and the application cannot drift apart.

Idempotent. Re-runs are safe.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

OUT_DIR = Path(__file__).resolve().parent / "out"
DDL_FILE = OUT_DIR / "deep_sec_ddl.sql"

# Tables that get a row-level region predicate. Region-carrying and
# region-via-FK tables are both listed in deep_security.REGION_EXPR.
REGION_TABLES = ("TRANSACTIONS", "BRANCHES", "MERCHANTS", "ACCOUNTS", "LOANS",
                 "CARDS", "CUSTOMERS", "SAR_REPORTS")

SUPPORT_DDL = {
    "AGENT_MASKS": (
        "CREATE TABLE agent_masks ("
        "  end_user    VARCHAR2(128) NOT NULL,"
        "  owner       VARCHAR2(64)  NOT NULL,"
        "  table_name  VARCHAR2(128) NOT NULL,"
        "  column_name VARCHAR2(128) NOT NULL)"
    ),
    "AGENT_DENIALS": (
        "CREATE TABLE agent_denials ("
        "  end_user    VARCHAR2(128) NOT NULL,"
        "  owner       VARCHAR2(64)  NOT NULL,"
        "  table_name  VARCHAR2(128) NOT NULL)"
    ),
    "AGENT_SCOPE": (
        "CREATE TABLE agent_scope ("
        "  end_user   VARCHAR2(128) NOT NULL,"
        "  scope_kind VARCHAR2(10)  NOT NULL,"
        "  scope_id   NUMBER)"
    ),
}

# Tables reached by a foreign key need their authorization precomputed, because
# a VPD predicate may not subquery another table that is itself VPD-protected
# (Oracle raises ORA-28113). scope_kind names the key column on the target table.
FK_SCOPE_KIND = {
    "ACCOUNTS": "BRANCH",
    "LOANS": "BRANCH",
    "CARDS": "ACCOUNT",
    "CUSTOMERS": "CUSTOMER",
    "SAR_REPORTS": "CUSTOMER",
}


# --------------------------------------------------------------------------- #
# 1. Probe
# --------------------------------------------------------------------------- #


def report_capability(conn) -> "object":
    from db.deep_security import probe, latest_driver_supports_deep_sec

    cap = probe(conn)
    print("  [probe] release      :", cap.version)
    print("  [probe] edition      :", cap.edition)
    print("  [probe] DBMS_DEEP_SEC:", "present" if cap.has_dbms_deep_sec else "ABSENT")
    print("  [probe] data-grant views:", "present" if cap.has_data_grant_views else "ABSENT")
    print("  [probe] DBMS_RLS     :", "present" if cap.has_dbms_rls else "ABSENT")
    print("  [probe] EDA_CTX      :", "installed" if cap.has_eda_context else "not installed")
    print(f"  [probe] => enforcement backend: {cap.backend}")

    ok, detail = latest_driver_supports_deep_sec()
    print(f"  [probe] client driver: {detail}")
    print(f"  [probe] OAMP         : {cap.oamp_version}")
    print("  [probe] OAMP memory DDS:",
          "available" if cap.has_oamp_deepsec else "ABSENT")
    if cap.backend != "DEEP_SEC" and not ok:
        print("  [probe] note: Deep Sec also needs the 4.x client API; "
              "Free cannot run it regardless.")
    for note in cap.notes:
        print("  [probe] note:", note)
    return cap


# --------------------------------------------------------------------------- #
# 2. Install the VPD backend
# --------------------------------------------------------------------------- #


def seed_policy_tables(agent_conn, identities) -> dict:
    """Rewrite the policy tables from the persona registry. Data, not DDL —
    so changing a persona's regions is an INSERT, not a code deploy."""
    from db.deep_security import vpd_seed

    with agent_conn.cursor() as cur:
        for name, ddl in SUPPORT_DDL.items():
            try:
                cur.execute(ddl)
                print(f"  [rules] created {name.lower()}")
            except Exception as e:
                if getattr(e.args[0], "code", None) != 955:
                    raise
        # FINANCE builds the precomputed scope and the predicates read the
        # rule tables, so it needs write access to one and read to all.
        for table in SUPPORT_DDL:
            try:
                cur.execute(f"GRANT SELECT ON {table} TO FINANCE")
            except Exception as e:
                if getattr(e.args[0], "code", None) != 1031:
                    raise
        for priv in ("INSERT", "DELETE"):
            try:
                cur.execute(f"GRANT {priv} ON AGENT_SCOPE TO FINANCE")
            except Exception as e:
                if getattr(e.args[0], "code", None) != 1031:
                    raise
    agent_conn.commit()

    seeds = vpd_seed(identities)
    with agent_conn.cursor() as cur:
        for table, rows, columns in (
            ("agent_authorizations", seeds["authorizations"], "(end_user, auth_region)"),
            ("agent_masks", seeds["masks"], "(end_user, owner, table_name, column_name)"),
            ("agent_denials", seeds["denials"], "(end_user, owner, table_name)"),
            ("agent_clearances", seeds["clearances"], "(end_user, clearance, notes)"),
        ):
            try:
                cur.execute(f"DELETE FROM {table}")
            except Exception as e:
                if getattr(e.args[0], "code", None) != 942:
                    raise
                print(f"  [rules] {table} missing — created by setup_advanced.py, skipping")
                continue
            marks = ",".join(f":{i + 1}" for i in range(len(columns.split(","))))
            if rows and len(rows[0]) != len(columns.split(",")):
                raise ValueError(
                    f"{table}: seed rows have {len(rows[0])} values but the "
                    f"target has {len(columns.split(','))} columns"
                )
            cur.executemany(
                f"INSERT INTO {table} {columns} VALUES ({marks})", rows
            )
            print(f"  [rules] {table}: {len(rows)} row(s)")
    agent_conn.commit()
    return seeds


def populate_scope(demo_conn, identities) -> int:
    """Precompute which branches/accounts/customers each persona may reach.

    Predicates can then be a plain EXISTS against this unprotected table instead
    of a subquery into FINANCE.branches, which is itself policied and therefore
    illegal to nest (ORA-28113). A NULL scope_id means "all".

    Runs as FINANCE on a session with no end-user context, where every predicate
    evaluates to 1=1, so it can read the full mapping.
    """
    from db.deep_security import end_user_name

    written = 0
    with demo_conn.cursor() as cur:
        cur.execute("DELETE FROM AGENT.agent_scope")
        for ident in identities.values():
            user = end_user_name(ident.id)

            if not ident.regions:
                cur.executemany(
                    "INSERT INTO AGENT.agent_scope (end_user, scope_kind, scope_id) "
                    "VALUES (:u, :k, NULL)",
                    [(user, k) for k in ("BRANCH", "ACCOUNT", "CUSTOMER")],
                )
                written += 3
                continue

            marks = ",".join(f":r{i}" for i in range(len(ident.regions)))
            binds = {"u": user, **{f"r{i}": r for i, r in enumerate(ident.regions)}}

            cur.execute(
                f"INSERT INTO AGENT.agent_scope (end_user, scope_kind, scope_id) "
                f"SELECT :u, 'BRANCH', b.branch_id FROM FINANCE.branches b "
                f" WHERE b.region IN ({marks})",
                binds,
            )
            written += cur.rowcount

            for kind, key in (("ACCOUNT", "a.account_id"),
                              ("CUSTOMER", "a.customer_id")):
                cur.execute(
                    f"INSERT INTO AGENT.agent_scope (end_user, scope_kind, scope_id) "
                    f"SELECT DISTINCT :u, '{kind}', {key} "
                    f"  FROM FINANCE.accounts a JOIN FINANCE.branches b "
                    f"    ON b.branch_id = a.branch_id "
                    f" WHERE b.region IN ({marks})",
                    binds,
                )
                written += cur.rowcount
        demo_conn.commit()
    return written


DROP_POLICY = """
BEGIN
  DBMS_RLS.DROP_POLICY(
    object_schema => :schema, object_name => :object_name,
    policy_name   => :policy_name);
END;
"""

def install_vpd(sys_conn, agent_conn, demo_conn, identities, agent_user: str = "AGENT",
                demo_user: str = "FINANCE") -> None:
    """Install application context + DBMS_RLS policies for every rule.

    Predicates read the policy tables, so the same SQL produces different rows
    for different end users without any DDL change.
    """
    import oracledb

    print("  [vpd] app context namespace...")
    created = False
    with agent_conn.cursor() as cur:
        try:
            cur.execute(f"CREATE OR REPLACE CONTEXT eda_ctx USING {agent_user}.set_eda_ctx")
            created = True
        except oracledb.DatabaseError as e:
            if e.args[0].code not in (1031, 2000, 900, 901, 922):
                raise
    if not created:
        # setup_advanced.py takes the same route: the AGENT user may not hold
        # CREATE ANY CONTEXT, and only the owner of the trusted setter can.
        with sys_conn.cursor() as cur:
            try:
                cur.execute(f"GRANT CREATE ANY CONTEXT TO {agent_user}")
            except oracledb.DatabaseError as e:
                if e.args[0].code != 1031:
                    raise
            cur.execute(
                f"CREATE OR REPLACE CONTEXT eda_ctx USING {agent_user}.set_eda_ctx"
            )
        sys_conn.commit()
    print("  [vpd] EDA_CTX present; writable only via the trusted setter")

    # The predicates run as FINANCE, so they must be able to read the rules.
    with agent_conn.cursor() as cur:
        for table in ("AGENT_MASKS", "AGENT_DENIALS", "AGENT_SCOPE",
                      "AGENT_AUTHORIZATIONS", "AGENT_CLEARANCES"):
            try:
                cur.execute(f"GRANT SELECT ON {table} TO {demo_user}")
            except oracledb.DatabaseError as e:
                if e.args[0].code != 1031:
                    raise
    agent_conn.commit()
    print(f"  [vpd] granted SELECT on the policy tables to {demo_user}")

    # --- row predicate: region membership, data-driven ---
    region_fn = """
    CREATE OR REPLACE FUNCTION eda_region_predicate(
        p_schema IN VARCHAR2, p_object IN VARCHAR2
    ) RETURN VARCHAR2 AS
        v_user VARCHAR2(128) := SYS_CONTEXT('EDA_CTX', 'END_USER');
    BEGIN
        IF v_user IS NULL THEN RETURN '1=1'; END IF;
        IF p_object IN ('TRANSACTIONS', 'BRANCHES', 'MERCHANTS') THEN
            RETURN q'[EXISTS (SELECT 1 FROM AGENT.agent_authorizations a
                              WHERE a.end_user = SYS_CONTEXT('EDA_CTX','END_USER')
                                AND (a.auth_region = 'ALL' OR a.auth_region = region))]';
        ELSIF p_object IN ('ACCOUNTS', 'LOANS') THEN
            RETURN q'[branch_id IN (SELECT b.branch_id FROM FINANCE.branches b
                                     WHERE EXISTS (SELECT 1 FROM AGENT.agent_authorizations a
                                                    WHERE a.end_user = SYS_CONTEXT('EDA_CTX','END_USER')
                                                      AND (a.auth_region = 'ALL' OR a.auth_region = b.region)))]';
        ELSE
            RETURN q'[1=1]';
        END IF;
    END;
    """

    # FK-reachable tables cannot subquery another policied table, so the
    # authorization was precomputed into AGENT.agent_scope by populate_scope().
    fk_fn = """
    CREATE OR REPLACE FUNCTION eda_scope_predicate(
        p_schema IN VARCHAR2, p_object IN VARCHAR2
    ) RETURN VARCHAR2 AS
        v_user VARCHAR2(128) := SYS_CONTEXT('EDA_CTX', 'END_USER');
        v_kind VARCHAR2(10);
    BEGIN
        IF v_user IS NULL THEN RETURN '1=1'; END IF;
        v_kind := CASE p_object
                    WHEN 'ACCOUNTS'    THEN 'BRANCH'
                    WHEN 'LOANS'       THEN 'BRANCH'
                    WHEN 'CARDS'       THEN 'ACCOUNT'
                    WHEN 'CUSTOMERS'   THEN 'CUSTOMER'
                    WHEN 'SAR_REPORTS' THEN 'CUSTOMER'
                  END;
        IF v_kind IS NULL THEN RETURN '1=1'; END IF;
        RETURN 'EXISTS (SELECT 1 FROM AGENT.agent_scope s'
            || ' WHERE s.end_user = SYS_CONTEXT(''EDA_CTX'',''END_USER'')'
            || '   AND s.scope_kind = ''' || v_kind || ''''
            || '   AND (s.scope_id IS NULL OR s.scope_id = ' || LOWER(p_object) || '.'
            || CASE v_kind WHEN 'BRANCH' THEN 'branch_id'
                           WHEN 'ACCOUNT' THEN 'account_id'
                           ELSE 'customer_id' END
            || '))';
    END;
    """

    deny_fn = """
    CREATE OR REPLACE FUNCTION eda_deny_predicate(
        p_schema IN VARCHAR2, p_object IN VARCHAR2
    ) RETURN VARCHAR2 AS
        v_user VARCHAR2(128) := SYS_CONTEXT('EDA_CTX', 'END_USER');
        v_hit  PLS_INTEGER;
    BEGIN
        IF v_user IS NULL THEN RETURN '1=1'; END IF;
        SELECT COUNT(*) INTO v_hit
          FROM AGENT.agent_denials d
         WHERE d.end_user = v_user
           AND d.owner = p_schema
           AND d.table_name = p_object;
        IF v_hit > 0 THEN RETURN '1=0'; END IF;
        RETURN '1=1';
    END;
    """

    denial_tables = sorted({
        qualified.split(".")[1].upper()
        for ident in identities.values()
        for qualified in ident.forbid_tables
        if qualified.split(".")[0].upper() == "FINANCE"
    })
    owned_tables = sorted(set(REGION_TABLES) | set(FK_SCOPE_KIND) | set(denial_tables))

    with demo_conn.cursor() as cur:
        # This installer owns the policies on these tables. Clear whatever a
        # previous run (or an earlier run) left behind first: a stale
        # policy still points at the predicate function we are about to replace,
        # which surfaces later as ORA-28113 on an unrelated SELECT.
        cur.execute(
            "SELECT object_name, policy_name FROM all_policies "
            " WHERE object_owner = :o", o=demo_user,
        )
        cleared = 0
        for obj, pol in cur.fetchall():
            if obj in owned_tables:
                cur.execute(DROP_POLICY, schema=demo_user, object_name=obj,
                            policy_name=pol)
                cleared += 1
        if cleared:
            print(f"  [vpd] cleared {cleared} policy/policies from a previous install")

    with demo_conn.cursor() as cur:
        for label, fn in (("row", region_fn), ("row-fk", fk_fn),
                          ("deny", deny_fn)):
            cur.execute(fn)
            print(f"  [vpd] created {label} predicate function")

    # Column masks need one policy+function per column, because DBMS_RLS binds
    # `sec_relevant_cols` into the policy, not into the function signature. We
    # generate a tiny per-column predicate that names its own column.
    masked_columns: list[tuple[str, str]] = []
    for ident in identities.values():
        for qualified in ident.mask_cols:
            owner, table, column = qualified.split(".")
            pair = (table.upper(), column.upper())
            if pair not in masked_columns:
                masked_columns.append(pair)

    with demo_conn.cursor() as cur:
        for table, column in masked_columns:
            fn = f"""
            CREATE OR REPLACE FUNCTION eda_mask_{table.lower()}_{column.lower()}(
                p_schema IN VARCHAR2, p_object IN VARCHAR2
            ) RETURN VARCHAR2 AS
                v_user VARCHAR2(128) := SYS_CONTEXT('EDA_CTX', 'END_USER');
                v_hit  PLS_INTEGER;
            BEGIN
                IF v_user IS NULL THEN RETURN '1=1'; END IF;
                SELECT COUNT(*) INTO v_hit
                  FROM AGENT.agent_masks m
                 WHERE m.end_user = v_user
                   AND m.owner = p_schema
                   AND m.table_name = '{table}'
                   AND m.column_name = '{column}';
                IF v_hit > 0 THEN RETURN '1=0'; END IF;
                RETURN '1=1';
            END;
            """
            cur.execute(fn)

    demo_conn.commit()

    # --- attach policies ---
    ADD_POLICY = """
    BEGIN
      DBMS_RLS.ADD_POLICY(
        object_schema   => :schema,
        object_name     => :object_name,
        policy_name     => :policy_name,
        function_schema => :schema,
        policy_function => :function_name,
        statement_types => 'SELECT',
        sec_relevant_cols => :sec_cols,
        sec_relevant_cols_opt => DBMS_RLS.ALL_ROWS);
    END;
    """
    ADD_ROW_POLICY = """
    BEGIN
      DBMS_RLS.ADD_POLICY(
        object_schema   => :schema,
        object_name     => :object_name,
        policy_name     => :policy_name,
        function_schema => :schema,
        policy_function => :function_name,
        statement_types => 'SELECT');
    END;
    """
    installed = 0
    with demo_conn.cursor() as cur:
        # row-level region policies
        for table in REGION_TABLES:
            fn = "EDA_REGION_PREDICATE" if table in ("TRANSACTIONS", "BRANCHES", "MERCHANTS") \
                else "EDA_SCOPE_PREDICATE"
            policy = f"EDA_{table}_REGION_POLICY"
            try:
                cur.execute(DROP_POLICY, schema=demo_user, object_name=table,
                            policy_name=policy)
            except oracledb.DatabaseError:
                pass
            try:
                cur.execute(ADD_ROW_POLICY, schema=demo_user, object_name=table,
                            policy_name=policy, function_name=fn)
                installed += 1
            except oracledb.DatabaseError as e:
                print(f"  [vpd] SKIP {table} row policy: {str(e)[:90]}")
                demo_conn.rollback()

        # column masks
        for table, column in masked_columns:
            policy = f"EDA_{table}_{column}_MASK_POLICY"
            fn = f"EDA_MASK_{table}_{column}"
            try:
                cur.execute(DROP_POLICY, schema=demo_user, object_name=table,
                            policy_name=policy)
            except oracledb.DatabaseError:
                pass
            try:
                cur.execute(ADD_POLICY, schema=demo_user, object_name=table,
                            policy_name=policy, function_name=fn,
                            sec_cols=column)
                installed += 1
            except oracledb.DatabaseError as e:
                print(f"  [vpd] SKIP {table}.{column} mask: {str(e)[:90]}")
                demo_conn.rollback()

    # table denials (SAR_REPORTS etc. are already row-filtered; make it explicit)
    with demo_conn.cursor() as cur:
        for table in denial_tables:
            policy = f"EDA_{table}_DENY_POLICY"
            try:
                cur.execute(DROP_POLICY, schema=demo_user, object_name=table,
                            policy_name=policy)
            except oracledb.DatabaseError:
                pass
            try:
                cur.execute(ADD_ROW_POLICY, schema=demo_user, object_name=table,
                            policy_name=policy, function_name="EDA_DENY_PREDICATE")
                installed += 1
            except oracledb.DatabaseError as e:
                print(f"  [vpd] SKIP {table} deny policy: {str(e)[:90]}")
                demo_conn.rollback()
    demo_conn.commit()
    print(f"  [vpd] {installed} DBMS_RLS policy/policies attached")


# --------------------------------------------------------------------------- #
# 3. Deep Sec DDL for the enterprise target
# --------------------------------------------------------------------------- #


def write_deep_sec_ddl(conn, identities) -> Path:
    """Emit the real Deep Sec DDL for a 26ai Enterprise-class target."""
    from db.deep_security import deep_sec_ddl

    table_columns: dict[str, list[str]] = {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name, column_name FROM all_tab_columns "
            " WHERE owner = 'FINANCE' "
            "   AND table_name NOT LIKE 'MDRT$%' "
            "   AND table_name NOT LIKE 'DM$%' "
            " ORDER BY table_name, column_id"
        )
        for table, column in cur:
            table_columns.setdefault(f"FINANCE.{table}", []).append(column)

    stmts = deep_sec_ddl(
        identities,
        table_columns,
        end_user_password=os.environ.get("EDA_END_USER_PASS", "ChangeMe_2026"),
        application_identity="MERIDIAN_AGENT",
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DDL_FILE.write_text("\n".join(stmts) + "\n", encoding="utf-8")
    print(f"  [deep_sec] wrote {len(stmts)} statement(s) -> {DDL_FILE}")
    return DDL_FILE


def apply_deep_sec(conn, identities) -> None:
    """Execute the Deep Sec DDL. Only reachable on a supporting database."""
    from db.deep_security import deep_sec_ddl

    table_columns: dict[str, list[str]] = {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name, column_name FROM all_tab_columns "
            " WHERE owner = 'FINANCE' ORDER BY table_name, column_id"
        )
        for table, column in cur:
            table_columns.setdefault(f"FINANCE.{table}", []).append(column)

    for stmt in deep_sec_ddl(identities, table_columns,
                             end_user_password=os.environ.get("EDA_END_USER_PASS"),
                             application_identity="MERIDIAN_AGENT"):
        if stmt.startswith("--") or not stmt.strip():
            continue
        with conn.cursor() as cur:
            cur.execute(stmt)
        print(f"  [deep_sec] ok: {stmt.splitlines()[0][:70]}")


# --------------------------------------------------------------------------- #
# 3b. OAMP memory-store Deep Data Security (OAMP >= 26.8)
# --------------------------------------------------------------------------- #


def memory_store_settings() -> tuple[str, str]:
    """(owner_schema, memory_store_id) for the harness's OAMP store.

    Kept in lockstep with `memory/manager.py`, which builds the client with the
    same store ID, so the policies protect the tables the agent actually uses.
    """
    from config import AGENT_USER
    from memory.manager import MEMORY_STORE_ID

    return AGENT_USER, MEMORY_STORE_ID


def install_memory_enforcement(conn, identities, cap) -> None:
    """Put the OAMP store under Deep Data Security when the database can do it.

    On Free, the data roles and data grants Deep Sec is built from are absent,
    so this reports the skip rather than pretending the memory layer is
    protected; the runtime keeps its application-level thread scoping there.
    """
    from db.deep_security import (
        install_memory_policies,
        oamp_memory_deep_sec_available,
    )

    owner_schema, store_id = memory_store_settings()
    if not cap.supports_deep_sec:
        print(f"  [memory] skipped {owner_schema}.{store_id}: backend="
              f"{cap.backend} has no data roles/data grants (OAMP memory "
              "policies require Deep Sec).")
        return
    ok, detail = oamp_memory_deep_sec_available()
    if not ok:
        print(f"  [memory] skipped {owner_schema}.{store_id}: {detail}")
        return

    report = install_memory_policies(
        conn, identities, owner_schema=owner_schema, memory_store_id=store_id
    )
    print(f"  [memory] {report.store}: {len(report.installed)} policy/policies "
          f"({', '.join(report.installed)})")
    names = ", ".join(name for name, _ in report.assignments[:3])
    suffix = " ..." if report.granted_principals > 3 else ""
    print(f"  [memory] granted to {report.granted_principals} end user(s): "
          f"{names}{suffix}")
    print("  [memory] runtime: wrap OAMP calls in "
          "db.deep_security.memory_end_user_context(ctx)")


def report_memory_policies(conn, cap) -> None:
    """Show the memory-store policy state on a Deep Sec database."""
    from db.deep_security import (
        list_memory_policies,
        oamp_memory_deep_sec_available,
    )

    owner_schema, store_id = memory_store_settings()
    print("\n  -- agent memory store (OAMP >= 26.8 Deep Data Security)")
    if not cap.supports_deep_sec:
        print(f"  not enforceable on backend={cap.backend}: no data roles/"
              "data grants for the memory tables.")
        return
    ok, detail = oamp_memory_deep_sec_available()
    if not ok:
        print(f"  not available: {detail}")
        return
    report = list_memory_policies(
        conn, owner_schema=owner_schema, memory_store_id=store_id
    )
    print(f"  store      : {report.store}")
    print(f"  policies   : {', '.join(report.installed) or '(none installed)'}")
    if not report.assignments:
        print("  principals : (no grants)")
    for name, policies in report.assignments:
        print(f"  principal  : {name:<46} {', '.join(policies)}")
    print("  Runtime identity comes from OracleMemoryEndUserSecurityContext, "
          "not a session variable.")


# --------------------------------------------------------------------------- #
# 4. Proof
# --------------------------------------------------------------------------- #


REGION_SHORT = {
    "AMERICAS": "AMER",
    "ASIA_PACIFIC": "APAC",
    "EUROPE": "EU",
    "MIDDLE_EAST": "ME",
}


def demo(agent_conn, identities) -> None:
    """Same SQL, different persona: show the database changing its answer.

    Three rule kinds are exercised, all enforced by the kernel:
      row    — TRANSACTIONS filtered by region
      column — AMOUNT_CENTS / BALANCE_CENTS returned as NULL
      deny   — SAR_REPORTS returns nothing at all
    """
    from db.deep_security import (
        clear_identity, column_is_null_for, end_user_name, set_identity,
        visible_rows,
    )

    def table(label: str) -> None:
        print(f"\n  -- {label}")
        print(f"  {'persona':<20} {'clearance':<10} {'transactions':>12} "
              f"{'regions':<16} {'amount':>10} {'SAR rows':>9} {'balance':>9}")
        print("  " + "-" * 92)

    def region_codes(cur) -> str:
        cur.execute("SELECT DISTINCT region FROM FINANCE.transactions")
        seen = {r[0] for r in cur}
        return ",".join(REGION_SHORT.get(r, r) for r in sorted(seen))

    table("row + column + deny rules, all evaluated inside the database")
    for ident in identities.values():
        try:
            set_identity(agent_conn, ident)
        except Exception as e:
            print(f"  {ident.id:<20} could not set identity: {str(e)[:60]}")
            continue

        rows = visible_rows(agent_conn)
        with agent_conn.cursor() as cur:
            regions = region_codes(cur)
        _, amount_non_null = column_is_null_for(
            agent_conn, "FINANCE.TRANSACTIONS", "AMOUNT_CENTS")
        _, balance_non_null = column_is_null_for(
            agent_conn, "FINANCE.ACCOUNTS", "BALANCE_CENTS")
        sar = visible_rows(agent_conn, "FINANCE.SAR_REPORTS")

        print(f"  {ident.id:<20} {ident.clearance:<10} {rows:>12} "
              f"{regions:<16} "
              f"{('visible' if amount_non_null else 'NULL'):>10} "
              f"{sar:>9} "
              f"{('visible' if balance_non_null else 'NULL'):>9}")

    clear_identity(agent_conn)
    print("  " + "-" * 92)
    print("  NULL means masked, not empty: the row came back, the value did not.")
    print("  SAR rows = 0 for every persona except compliance.officer (default-deny).")
    print(f"  Identities are end-user names: {end_user_name('analyst.east')}, ...")
    print("  No Python filtered these rows — the SQL below is identical for all six.")


def main() -> int:
    from config import AGENT_USER, DEMO_USER
    from db.connection import connect_sys, connect_agent, connect_demo
    from api.identities import IDENTITIES

    args = set(sys.argv[1:])
    ddl_only = bool({"ddl-only", "--ddl-only"} & args)
    print("\n=== Deep Data Security: probe, install, prove ===\n")

    sys_conn = connect_sys()
    agent_conn = connect_agent()

    print("[1/4] What can this database enforce?")
    cap = report_capability(agent_conn)

    if ddl_only:
        print("\n[--ddl-only] writing Deep Sec DDL and exiting")
        write_deep_sec_ddl(agent_conn, IDENTITIES)
        print("  [memory] OAMP >= 26.8 manages the memory-store policies itself;"
              " run")
        print("           this script on the target (or call"
              " install_memory_policies())")
        print("           after the DDL is applied \u2014 do not hand-write those"
              " grants.")
        return 0

    print("\n[2/4] Loading the policy tables from api/identities.py...")
    seed_policy_tables(agent_conn, IDENTITIES)

    demo_conn = connect_demo()
    try:
        if not cap.supports_deep_sec:
            written = populate_scope(demo_conn, IDENTITIES)
            print(f"  [rules] agent_scope: {written} precomputed authorization row(s)")

        print("\n[3/4] Installing enforcement...")
        if cap.supports_deep_sec:
            apply_deep_sec(sys_conn, IDENTITIES)
        else:
            install_vpd(sys_conn, agent_conn, demo_conn, IDENTITIES,
                        agent_user=AGENT_USER, demo_user=DEMO_USER)
            write_deep_sec_ddl(agent_conn, IDENTITIES)
            print("  [deep_sec] NOT executed: this database has no Deep Sec. "
                  f"Run {DDL_FILE.name} on a 26ai Enterprise-class instance to "
                  "replace the VPD backend with data grants.")
        install_memory_enforcement(sys_conn, IDENTITIES, cap)
    finally:
        demo_conn.close()

    if "--demo" in args:
        print("\n[4/4] Proof: the database answers per persona")
        demo(agent_conn, IDENTITIES)
        report_memory_policies(sys_conn, cap)
    else:
        print("\n[4/4] Skipped proof (pass --demo to run it)")

    agent_conn.close()
    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
