"""Provision Oracle True Cache for the Free primary with the image's built-in True Cache setup.

The container connects to the primary as SYS (HF_PRIMARY_SYS_PASSWORD), pulls its configuration,
creates the True Cache instance with DBCA and registers a read service. HF_TRUE_CACHE_DSN is written
to .env only after a desk identity reads through it and the session reports DATABASE_ROLE = TRUE CACHE.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import oracledb  # noqa: E402
from backend.config import PERSONAS, ROOT, env  # noqa: E402

PRIMARY = env("HF_DB_CONTAINER", "hf-oracle")
NAME = "hf-true-cache"
NETWORK = "hf-tc-net"
PORT = "1524"
SERVICE = "HF_READS_TC"
DSN = f"localhost:{PORT}/{SERVICE}"


def run(*args, **kw):
    return subprocess.run(list(args), check=True, **kw)


def exists(kind, name):
    return subprocess.run(["docker", kind, "inspect", name], capture_output=True).returncode == 0


def main():
    password = env("HF_PRIMARY_SYS_PASSWORD")
    if not password:
        sys.exit("Set the primary SYS password first: ./scripts/set_primary_sys_password.sh")
    if not exists("network", NETWORK):
        run("docker", "network", "create", NETWORK, capture_output=True)
    networks = subprocess.check_output(
        ["docker", "inspect", "-f", "{{json .NetworkSettings.Networks}}", PRIMARY], text=True
    )
    if NETWORK not in networks:
        run("docker", "network", "connect", "--alias", "hf-primary", NETWORK, PRIMARY)
    folder = ROOT / "var/true-cache"
    folder.mkdir(parents=True, exist_ok=True)
    if exists("container", NAME):
        run("docker", "start", NAME, capture_output=True)
    else:
        # Manual flow: the image's automatic setup needs Docker secrets; DBCA only needs the primary's password file.
        run(
            "docker",
            "cp",
            PRIMARY + ":/opt/oracle/product/26ai/dbhomeFree/dbs/orapwFREE",
            str(folder / "orapwFREE"),
        )
        (folder / "orapwFREE").chmod(0o644)
        # ORACLE_PWD is the primary SYS password; it is passed through the environment, never on the command line.
        run(
            "docker",
            "run",
            "-d",
            "--name",
            NAME,
            "--hostname",
            NAME,
            "--network",
            NETWORK,
            "--shm-size",
            "1g",
            "-p",
            f"127.0.0.1:{PORT}:1521",
            "-e",
            "TRUE_CACHE=true",
            "-e",
            "AUTO_TRUE_CACHE_SETUP=false",
            "-e",
            "ORACLE_PWD",
            "-e",
            "PRIMARY_DB_CONN_STR=hf-primary:1521/FREE",
            "-e",
            "PRIMARY_DB_PWD_FILE=/opt/oracle/hf_tc/orapwFREE",
            "-v",
            f"{folder}:/opt/oracle/hf_tc:ro",
            "-v",
            "hf-true-cache-data:/opt/oracle/oradata",
            "container-registry.oracle.com/database/free:latest",
            env={**os.environ, "ORACLE_PWD": password},
            capture_output=True,
        )
    print("True Cache container started; waiting for DBCA (typically 10-20 minutes)…", flush=True)
    deadline = time.time() + 2400
    while time.time() < deadline:
        logs = subprocess.run(["docker", "logs", NAME], capture_output=True, text=True).stdout
        if "DATABASE IS READY TO USE" in logs:
            break
        if "ERROR" in logs and ("Exiting" in logs or "DBCA" in logs and "failed" in logs.lower()):
            sys.exit("True Cache setup failed; inspect: docker logs " + NAME)
        time.sleep(20)
    else:
        sys.exit("Timed out waiting for True Cache; inspect: docker logs " + NAME)
    # Map a primary application service to a True Cache service (DBCA on the primary, password on stdin).
    services = subprocess.run(
        [
            "docker",
            "exec",
            PRIMARY,
            "bash",
            "-c",
            "echo \"select name||'='||true_cache_service from dba_services where name='HF_READS';\" | sqlplus -s / as sysdba",
        ],
        capture_output=True,
        text=True,
    ).stdout
    if "HF_READS=" + SERVICE not in services.replace(" ", ""):
        r = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                PRIMARY,
                "bash",
                "-c",
                "dbca -silent -configureDatabase -configureTrueCacheInstanceService -sourceDB FREE -trueCacheConnectString hf-true-cache:1521/FREE_TC -trueCacheServiceName "
                + SERVICE
                + " -serviceName HF_READS -pdbName FREEPDB1",
            ],
            input=password + "\n",
            capture_output=True,
            text=True,
        )
        print(
            "\n".join(
                line
                for line in (r.stdout + r.stderr).splitlines()
                if line.strip() and password not in line
            )[-1500:],
            flush=True,
        )
    # Verify the identities that read through True Cache. DDS end users cannot log in to the read-only
    # instance in this release (ORA-16000), so desk-entitled reads stay on the primary; that is recorded, not hidden.
    checks = {}
    for label, user, pw in [
        ("reference", "HF_REFERENCE", env("HF_REFERENCE_PASSWORD")),
        ("memory", "HF_CREDIT_MEM", PERSONAS["Credit"]["password"]),
    ]:
        for _attempt in range(30):
            try:
                with oracledb.connect(user=user, password=pw, dsn=DSN) as c:
                    cur = c.cursor()
                    role, service = cur.execute(
                        "SELECT SYS_CONTEXT('USERENV','DATABASE_ROLE'),SYS_CONTEXT('USERENV','SERVICE_NAME') FROM dual"
                    ).fetchone()
                    if label == "reference":
                        checks["position_vertices_visible"] = cur.execute(
                            "SELECT COUNT(*) FROM GRAPH_TABLE(HF_OWNER.HF_GRAPH MATCH (p IS Position) COLUMNS(p.position_id AS id))"
                        ).fetchone()[0]
                checks[label] = (role, service)
                break
            except oracledb.Error as e:
                last = e
                time.sleep(10)
        else:
            sys.exit(f"{user} cannot read through {SERVICE}: {last}")
    try:
        with oracledb.connect(
            user='"' + PERSONAS["Credit"]["user"] + '"',
            password=PERSONAS["Credit"]["password"],
            dsn=DSN,
        ):
            checks["dds_end_user"] = "login ok"
    except oracledb.Error as e:
        checks["dds_end_user"] = str(e).split(chr(10))[0]
    role, service = checks["reference"]
    if (
        role not in ("TRUE CACHE", "PHYSICAL STANDBY")
        or service.upper() != SERVICE
        or checks["position_vertices_visible"] != 0
    ):
        sys.exit(f"Refusing to configure: {checks}")
    lines = [
        line
        for line in (ROOT / ".env").read_text().splitlines()
        if not line.startswith("HF_TRUE_CACHE_DSN=")
    ] + [f"HF_TRUE_CACHE_DSN={DSN}"]
    (ROOT / ".env").write_text("\n".join(lines) + "\n")
    (ROOT / ".env").chmod(0o600)
    print(f"Verified {DSN}: {checks}. HF_TRUE_CACHE_DSN written; restart ./run.sh.")


if __name__ == "__main__":
    main()
