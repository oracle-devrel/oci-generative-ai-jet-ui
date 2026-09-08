---
name: oracle-aidb-docker-setup
description: Bring up Oracle 26ai Free in Docker, create a project-scoped app user with USERS tablespace + ONNX-friendly grants, and write a `.env` ready for the rest of the build-paths skills. Idempotent — safe to re-invoke. Use when any project needs a fresh local Oracle 26ai instance.
inputs:
  - target_dir: where to write docker-compose.yml + .env (default = current dir)
  - app_user: app user name for the project (default = derived from package_slug, uppercased; e.g. PDF_CHAT)
  - port: host port for the Oracle listener (default = 1521); use a different port for parallel runs
  - em_port: host port for EM Express (default = 5500)
  - compose_project: docker compose project name (default = derived from target_dir basename)
  - oracle_pwd: optional; if not set, generate a strong one
  - volume_name: docker named volume for persistence (default = oracle_<compose_project>_data)
outputs:
  - target_dir/docker-compose.yml      (parameterised — port + volume from .env)
  - target_dir/.env                    (DB_USER, DB_PASSWORD, DB_DSN — APP user, NOT SYSTEM)
  - a healthy `oracle` container reachable on host:${ORACLE_PORT}
  - an APP user (default tablespace USERS) ready for OracleVS + chat history + ONNX
---

You scaffold the Oracle 26ai Free container AND create the app user the rest of the build-paths skills will use. Nothing else. No Python app code beyond the user-creation script.

**Why an app user (not SYSTEM)?** `OracleVS` declares its metadata column as JSON. Oracle's JSON validation requires Automatic Segment Space Management (ASSM). The `SYSTEM` tablespace lacks ASSM, so connecting as `SYSTEM` and creating any OracleVS table fails with `ORA-43853: JSON type cannot be used in non-automatic segment space management tablespace "SYSTEM"`. The app user we create has `DEFAULT TABLESPACE USERS` (which has ASSM).

## Step 0 — References

- `shared/references/oracle-26ai-free-docker.md` — image, healthcheck, password rules, app-user creation rationale.
- `shared/templates/docker-compose.oracle-free.yml` — the canonical compose file (parameterised — port + volume + project name come from .env).

## Pre-flight — host-shell gotchas (for the user)

- After installing Docker, you must open a fresh shell for `docker` group membership to take effect — or use `sudo docker ...` for the rest of this session.
- `conda activate <env>` does not work in non-interactive bash. Call binaries by absolute path (`~/miniconda3/envs/<env>/bin/python`).
- conda-forge `python=3.12` does not include `pip` — when creating an env, list `pip` explicitly: `conda create -n <env> -c conda-forge --override-channels python=3.12 pip -y`.
- **Parallel runs need separate ports for ALL services**, not just Oracle. The tier skills typically write Open WebUI on `:3000` and the FastAPI adapter on `:8000` — if you're running multiple build-paths projects at once, override these in the project's `.env` (`OPEN_WEBUI_PORT`, `ADAPTER_PORT`) and read them from `docker-compose.yml` + the adapter's `uvicorn.run(port=...)` call.

## Step 1 — Detect existing setup

In `target_dir`:
- If `docker-compose.yml` exists AND it contains `image: container-registry.oracle.com/database/free:`, **don't overwrite**. Read its `ORACLE_PWD` from the existing `.env` and skip to Step 4.
- If `docker-compose.yml` exists but is for something else, stop and ask the user. Don't clobber.
- If neither, proceed.

## Step 2 — Generate password

If the user passed `oracle_pwd`, use it (validate first: 12+ chars, mixed case, digit, no `$/@/"`).

Otherwise generate one:

```python
import secrets, string
alphabet = string.ascii_letters + string.digits
pwd = "Or" + "".join(secrets.choice(alphabet) for _ in range(18))
```

Why no symbols: Oracle's `ORACLE_PWD` env var splits on `$`, breaks on `@` (interpreted as connect string), and chokes on quotes. Letters + digits avoid the whole class.

## Step 3 — Write compose + env

`target_dir/docker-compose.yml` — copied verbatim from `shared/templates/docker-compose.oracle-free.yml`. The template uses `${ORACLE_PORT}`, `${ORACLE_PWD}`, `${ORACLE_VOLUME}`, and `${COMPOSE_PROJECT_NAME}` — compose reads them from `.env`.

`target_dir/.env`:

```
COMPOSE_PROJECT_NAME=<compose_project>
ORACLE_PWD=<generated>
ORACLE_PORT=<port>
ORACLE_EM_PORT=<em_port>
ORACLE_VOLUME=<volume_name>

# SYS / SYSTEM creds — only used for the app-user creation in Step 6 and for
# any SYSDBA-only operations (e.g. GRANT EXECUTE ON SYS.DBMS_VECTOR).
SYS_USER=SYSTEM
SYS_PASSWORD=<same as ORACLE_PWD>

# Application credentials — what every other skill uses.
DB_USER=<app_user>
DB_PASSWORD=<generated app pwd>
DB_DSN=localhost:<port>/FREEPDB1
```

Don't commit `.env`. The skill confirms `target_dir/.gitignore` contains `.env` — adds the line if missing.

## Step 3b — Pull the image for the host's native arch (load-bearing on Apple Silicon)

Before `docker compose up`, check the host arch and force a native-arch pull. The Oracle 26ai Free image is multi-arch, but Docker's manifest auto-resolution is unreliable when a stale image is on disk or the host VM is degraded — most commonly amd64 layers end up on an arm64 Mac. Under emulation the entrypoint's `su oracle` step silently fails with "Authentication failure", no Oracle processes ever start, and the old `sqlplus | grep '1'` healthcheck false-positives on the ORA-01034 error text (the new `/opt/oracle/checkDBStatus.sh` check catches it, but pulling the right image up front avoids the whole detour).

```bash
HOST_ARCH=$(uname -m)
case "$HOST_ARCH" in
  x86_64)         PLATFORM=linux/amd64 ;;
  arm64|aarch64)  PLATFORM=linux/arm64 ;;
  *)              echo "unsupported host arch: $HOST_ARCH"; exit 1 ;;
esac

EXISTING=$(docker image inspect container-registry.oracle.com/database/free:latest \
             --format '{{.Architecture}}' 2>/dev/null || true)
if [ -n "$EXISTING" ] && [ "$EXISTING" != "${PLATFORM##*/}" ]; then
  echo "stale $EXISTING image on disk; re-pulling for $PLATFORM"
  docker rmi container-registry.oracle.com/database/free:latest
fi

docker pull --platform "$PLATFORM" container-registry.oracle.com/database/free:latest
```

On amd64 Linux hosts the inspect matches and the `docker pull` is a no-op cache hit. The cost is one extra command; the saving is the user not spending an hour on "the container is healthy but I can't connect" on a Mac.

## Step 4 — Bring it up

```bash
cd target_dir
docker compose up -d --wait
```

`--wait` blocks until the healthcheck passes. First boot: ~90s. Subsequent boots: ~15s.

The compose template uses the image's own `/opt/oracle/checkDBStatus.sh` for the healthcheck — it returns 0 only when the PDB is actually OPEN. Do not regress this to the older `echo 'SELECT 1 FROM DUAL;' | sqlplus -L ... | grep -q '1'` pattern: when the entrypoint aborts (e.g. arch mismatch — see Step 3b), sqlplus returns an `ORA-01034: ORACLE not available` banner containing the digit `1`, the grep matches the error text, and compose reports HEALTHY for a container that has zero Oracle processes inside. This is the friction Step 3b was added to catch.

If `--wait` exits non-zero:
1. Print `docker compose logs oracle | tail -30`.
2. Common causes: port collision (someone else has 1521 — ask the user to pick a different port and re-run), insufficient memory (Oracle needs ~2GB; tell the user), corrupt volume (rare, suggest `docker compose down -v` AFTER confirming with the user), arch mismatch (look for `su: Authentication failure` or `Permission denied` in the logs — re-run Step 3b).
3. Stop. Don't retry blindly.

## Step 5 — Smoke SYSTEM connect

```python
import oracledb, os
from dotenv import load_dotenv

load_dotenv(f"{target_dir}/.env")
conn = oracledb.connect(
    user=os.environ["SYS_USER"],
    password=os.environ["SYS_PASSWORD"],
    dsn=os.environ["DB_DSN"],
)
with conn.cursor() as cur:
    cur.execute("SELECT 'ok' FROM dual")
    assert cur.fetchone()[0] == "ok"
print("oracle-aidb-docker-setup: SYSTEM connect OK")
```

If this fails with `ORA-12541` (no listener), wait another 30s and retry once — the container claims healthy a few seconds before the listener is ready in some kernels. If it still fails, stop and surface the error.

If `oracledb` isn't installed in the current env, install it: `pip install oracledb`.

## Step 6 — Create the app user (load-bearing for every other skill)

Connect as `SYSTEM` and create an app user named after `app_user` with `DEFAULT TABLESPACE USERS` plus the grants needed by the rest of the build-paths skill set:

```python
APP_USER = os.environ["DB_USER"]            # e.g. PDF_CHAT
APP_PWD  = os.environ["DB_PASSWORD"]
SYS_PWD  = os.environ["SYS_PASSWORD"]

with conn.cursor() as cur:
    # Drop if exists, then create. Idempotent.
    try:
        cur.execute(f"DROP USER {APP_USER} CASCADE")
    except oracledb.DatabaseError as e:
        if "ORA-01918" not in str(e):  # user does not exist
            raise

    cur.execute(
        f'CREATE USER {APP_USER} IDENTIFIED BY "{APP_PWD}" '
        f'DEFAULT TABLESPACE USERS QUOTA UNLIMITED ON USERS'
    )
    cur.execute(
        f"GRANT CONNECT, RESOURCE, CREATE SESSION, CREATE TABLE, "
        f"CREATE VIEW, CREATE PROCEDURE TO {APP_USER}"
    )
    cur.execute(f"GRANT CREATE MINING MODEL TO {APP_USER}")
conn.commit()

# Required for VECTOR_EMBEDDING(MODEL ...) — the in-DB ONNX path used by
# intermediate / advanced. GRANT EXECUTE ON SYS.DBMS_VECTOR ALWAYS requires
# SYSDBA in 26ai Free (verified during the friction pass — SYSTEM hits
# ORA-01031). Open a separate SYSDBA connection for this one GRANT.
sysdba_conn = oracledb.connect(
    user="SYS",
    password=os.environ["SYS_PASSWORD"],
    dsn=os.environ["DB_DSN"],
    mode=oracledb.AUTH_MODE_SYSDBA,
)
with sysdba_conn.cursor() as cur:
    cur.execute(f"GRANT EXECUTE ON SYS.DBMS_VECTOR TO {APP_USER}")
sysdba_conn.commit()
print(f"oracle-aidb-docker-setup: created app user {APP_USER}")
```

Now smoke the app-user connection (this is the one every other skill uses):

```python
app_conn = oracledb.connect(
    user=APP_USER, password=APP_PWD, dsn=os.environ["DB_DSN"]
)
with app_conn.cursor() as cur:
    cur.execute("SELECT 'ok' FROM dual")
    assert cur.fetchone()[0] == "ok"
print("oracle-aidb-docker-setup: app user connect OK")
```

## Stop conditions

- `docker` not on PATH. Tell the user to install Docker Desktop / engine and stop.
- Port already in use AND user hasn't supplied a different one. Ask which port to use.
- The user's `target_dir` is a different project's repo and already has a `docker-compose.yml`. Don't clobber.

## What you must NOT do

- Don't generate weak passwords (no defaults like `Welcome123`).
- Don't run `docker system prune` or anything that touches other containers.
- Don't expose Oracle on `0.0.0.0` — bind to `127.0.0.1:<port>:1521`.
- Don't mount the data volume on a path inside the project repo. Use a docker named volume.

## Final report

```
oracle-aidb-docker-setup: OK
  compose:  target_dir/docker-compose.yml
  env:      target_dir/.env  (ORACLE_PWD generated)
  dsn:      localhost:<port>/FREEPDB1
  status:   healthy (smoke connect OK)
  next:     hand off to a higher-level skill, or run your own oracledb.connect(...)
```
