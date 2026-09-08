"""One-time bootstrap to make the app fully self-sufficient (no notebook required).

Steps:
  1. Create the AGENT user with all grants the harness needs.
  2. Set vector_memory_size = 512M at CDB-root scope (SPFILE).
  3. If the running instance hasn't picked up the new pool, bounce the Oracle
     container and wait for FREEPDB1 to come back online.
  4. Stage + register the in-database ONNX embedder model (ALL_MINILM_L12_V2).
  5. Ensure the DBFS scratchpad tablespace + store + mount exist.
  6. Ensure the toolbox + skillbox tables exist (empty).

After this finishes, run `python scripts/seed.py` to populate SUPPLYCHAIN data
and ingest oracle/skills.

Usage:
    cd app && python scripts/bootstrap.py            # auto-bounces if needed
    cd app && python scripts/bootstrap.py --no-bounce   # skip the bounce; you bounce yourself
"""

import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def _docker_cli() -> str | None:
    os.environ["PATH"] = ":".join([
        "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
        os.environ.get("PATH", ""),
    ])
    return shutil.which("docker") or shutil.which("podman")


def _bounce_and_wait(container_name: str, dsn: str, sys_user: str, sys_pass: str,
                     max_wait_s: int = 300):
    cli = _docker_cli()
    if not cli:
        raise SystemExit(
            f"Auto-bounce requested but neither docker nor podman is on PATH.\n"
            f"Restart the container yourself: docker restart {container_name}\n"
            f"Then re-run bootstrap with --no-bounce."
        )
    print(f"Bouncing {container_name} via {cli}...")
    subprocess.run([cli, "restart", container_name], check=True)

    print(f"Waiting up to {max_wait_s}s for FREEPDB1 to come back online...")
    import oracledb
    start = time.time()
    while time.time() - start < max_wait_s:
        try:
            conn = oracledb.connect(
                user=sys_user, password=sys_pass, dsn=dsn,
                mode=oracledb.AUTH_MODE_SYSDBA,
            )
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM dual")
                cur.fetchone()
            conn.close()
            print(f"  FREEPDB1 is back online ({int(time.time() - start)}s).")
            return
        except Exception:
            time.sleep(5)
    raise SystemExit(f"FREEPDB1 didn't come back within {max_wait_s}s.")


def main():
    auto_bounce = "--no-bounce" not in sys.argv

    # Read config the same way the rest of the backend does
    from config import (
        AGENT_PASS, AGENT_USER,
        SYS_DSN, SYS_PASS, SYS_USER,
    )

    print("\n=== Bootstrap: setting up Oracle for the Enterprise Data Agent ===\n")

    # 1. AGENT user
    print("[1/6] AGENT user + grants...")
    from db.connection import connect_sys
    sys_conn = connect_sys()
    from db.agent_setup import ensure_agent_user
    ensure_agent_user(sys_conn, AGENT_USER, AGENT_PASS)

    # 2. Vector memory pool
    print("\n[2/6] vector_memory_size...")
    from db.vector_pool import (
        get_running_mb, get_spfile_mb, needs_bounce, set_spfile,
    )
    print(f"  running: {get_running_mb(sys_conn)} MB; "
          f"SPFILE: {get_spfile_mb(sys_conn)} MB")
    if get_spfile_mb(sys_conn) < 512:
        set_spfile(sys_conn, 512)
        print("  set vector_memory_size = 512M SCOPE=SPFILE CONTAINER=ALL")
    else:
        print("  SPFILE already at 512M+; no change")

    # 3. Bounce if running pool < SPFILE setting
    if needs_bounce(sys_conn, target_mb=512):
        sys_conn.close()
        if auto_bounce:
            container = os.environ.get("ORACLE_CONTAINER", "oracle-free")
            print(f"\n[3/6] Bouncing {container} so the SGA picks up the new pool...")
            _bounce_and_wait(container, SYS_DSN, SYS_USER, SYS_PASS)
        else:
            print("\n[3/6] *** ACTION REQUIRED ***")
            print("  Run:  docker restart oracle-free")
            print("  Then: python scripts/bootstrap.py --no-bounce  (to resume)")
            return
        # Reconnect after bounce
        sys_conn = connect_sys()
        live = get_running_mb(sys_conn)
        print(f"  vector pool now live at {live} MB")
        if live < 512:
            print(f"  !! pool still {live} MB after bounce — investigate v$spparameter")
    else:
        print(f"\n[3/6] Bounce not needed ({get_running_mb(sys_conn)} MB already live)")

    # 4. ONNX embedder
    print("\n[4/6] ONNX embedder model...")
    from db.connection import connect_agent
    agent_conn = connect_agent()
    from db.onnx_setup import ensure_embedder
    ensure_embedder(sys_conn, agent_conn, AGENT_USER)

    # 5. DBFS scratchpad
    print("\n[5/6] DBFS scratchpad (tablespace + store + mount)...")
    from db.dbfs_setup import ensure as ensure_dbfs
    ensure_dbfs(sys_conn, agent_conn, agent_user=AGENT_USER)

    # 6. Empty toolbox + skillbox tables
    print("\n[6/6] toolbox + skillbox tables (empty)...")
    from agent.skills import ensure_skillbox
    from agent.tools import ensure_toolbox
    ensure_toolbox(agent_conn)
    ensure_skillbox(agent_conn)

    print("\n=== Bootstrap complete ===")
    print("Now run:  python scripts/seed.py")


if __name__ == "__main__":
    main()
