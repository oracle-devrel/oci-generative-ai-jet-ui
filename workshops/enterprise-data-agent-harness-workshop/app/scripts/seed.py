"""Populate the demo data on top of an already-bootstrapped Oracle.

Assumes `python scripts/bootstrap.py` has run at least once (creates AGENT user,
vector memory pool, ONNX embedder, DBFS, empty toolbox/skillbox). This script:

  - Creates / reseeds the SUPPLYCHAIN schema with spatial data + duality views
  - Scans the schema into OAMP institutional knowledge
  - Ingests oracle/skills into the skillbox

Idempotent. Re-runnable to refresh the data.

Run:
    cd app && python scripts/seed.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def main():
    # 1. Connect.
    from db.connection import connect_sys, connect_agent
    print("Connecting...")
    sys_conn = connect_sys()
    agent_conn = connect_agent()

    # 2. Ensure SUPPLYCHAIN user exists with the grants we need.
    SCHEMA = os.environ.get("ORACLE_DEMO_USER", "SUPPLYCHAIN")
    PASS = os.environ.get("ORACLE_DEMO_PASS", "SupplyPwd_2025")
    AGENT = os.environ.get("ORACLE_AGENT_USER", "AGENT")

    print(f"Ensuring user {SCHEMA} exists with required grants...")
    with sys_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM all_users WHERE username = :u", u=SCHEMA)
        if cur.fetchone()[0] == 0:
            cur.execute(f"CREATE USER {SCHEMA} IDENTIFIED BY {PASS}")
        cur.execute(f"GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO {SCHEMA}")
        cur.execute(f"GRANT CREATE VIEW, CREATE PROCEDURE, CREATE TYPE TO {SCHEMA}")
        try:
            cur.execute(f"GRANT EXECUTE ON MDSYS.SDO_GEOMETRY TO {SCHEMA}")
        except Exception:
            pass
        cur.execute(f"GRANT SELECT ANY TABLE TO {AGENT}")
    sys_conn.commit()

    # 3. Run the supply chain schema + seed + duality views.
    from db.connection import connect
    import oracledb
    sup_conn = connect(SCHEMA, PASS, os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"))
    from db.seed_supplychain import seed
    seed(sup_conn)
    sup_conn.close()

    # 4. Toolbox + skillbox in AGENT.
    print("\nEnsuring toolbox and skillbox tables...")
    from agent.skills import ensure_skillbox, ingest_skills
    from agent.tools import ensure_toolbox
    ensure_toolbox(agent_conn)
    ensure_skillbox(agent_conn)

    # 4b. DBFS scratchpad (idempotent).
    print("\nEnsuring DBFS scratchpad (tablespace + store + mount)...")
    from db.dbfs_setup import ensure as ensure_dbfs
    ensure_dbfs(sys_conn, agent_conn, agent_user=AGENT)

    # 5. Build OAMP client and scan SUPPLYCHAIN into memory.
    print("\nBuilding OAMP memory client + scanning schema...")
    from memory.manager import build_memory_client
    from retrieval.scanner import run_scan
    mc = build_memory_client(agent_conn)
    summary = run_scan(agent_conn, mc, SCHEMA)
    print(f"  scan summary: {summary}")

    # 6. Ingest oracle/skills (one tarball download + dedup by SHA).
    print("\nIngesting oracle/skills repo into skillbox...")
    ing = ingest_skills(agent_conn)
    print(f"  ingest summary: {ing}")

    print("\nSeed complete. Start the backend with:  cd backend && python app.py")


if __name__ == "__main__":
    main()
