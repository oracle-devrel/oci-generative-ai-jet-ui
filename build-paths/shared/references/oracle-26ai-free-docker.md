# Oracle 26ai Free — local Docker setup

Every build-paths project starts here. The skill copies `shared/templates/docker-compose.oracle-free.yml` into the user's target dir, generates an `ORACLE_PWD`, brings the container up, and waits for the healthcheck.

## What the user gets

- Listener on `localhost:1521`, service name `FREEPDB1` → DSN `localhost:1521/FREEPDB1`.
- EM Express on `https://localhost:5500/em` (browser UI for SQL + monitoring), creds `SYSTEM` / `<ORACLE_PWD>`.
- Persistent volume `oracle-data` so data survives `docker compose down`.
- Optional `./init-schema/*.sql` — Oracle runs these once on first boot, alphabetically, against `FREEPDB1`. Some skills use this for seed data.

## ORACLE_PWD rules (the #1 trap)

The image rejects passwords that don't meet **all four** of:
- ≥ 12 characters
- ≥ 1 uppercase letter
- ≥ 1 lowercase letter
- ≥ 1 digit

The skill generates a compliant password automatically — never let the user pick one. Generation pattern (from the skill, not for the user to type):

```python
import secrets, string
def gen():
    alphabet = string.ascii_letters + string.digits
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(16))
        if (any(c.isupper() for c in pw)
            and any(c.islower() for c in pw)
            and any(c.isdigit() for c in pw)):
            return pw
```

Write the result to `.env` only — never to a committed file. `.env` is gitignored by the project's `.gitignore` (the skill ensures this).

## Host architecture — Apple Silicon (arm64) and other non-amd64 hosts

The `container-registry.oracle.com/database/free:latest` manifest is multi-arch, but Docker's auto-resolution is unreliable when there's a stale image on disk or the host VM (Docker Desktop, colima, OrbStack) is in a degraded state. The failure mode on Apple Silicon: amd64 layers get pulled onto an arm64 host, the container starts under QEMU emulation, the entrypoint's `su oracle` step fails with "Authentication failure", no Oracle processes ever start, and the container looks fine from the outside.

The skill MUST detect this before `docker compose up`:

```bash
HOST_ARCH=$(uname -m)   # x86_64 | arm64 | aarch64
case "$HOST_ARCH" in
  x86_64)            PLATFORM=linux/amd64 ;;
  arm64|aarch64)     PLATFORM=linux/arm64 ;;
  *)                 echo "unsupported host arch: $HOST_ARCH"; exit 1 ;;
esac

# If a stale image exists, check its arch and force a re-pull on mismatch.
EXISTING=$(docker image inspect container-registry.oracle.com/database/free:latest \
             --format '{{.Architecture}}' 2>/dev/null || true)
if [ -n "$EXISTING" ] && [ "$EXISTING" != "${PLATFORM##*/}" ]; then
  echo "stale $EXISTING image on disk; re-pulling for $PLATFORM"
  docker rmi container-registry.oracle.com/database/free:latest
fi

docker pull --platform "$PLATFORM" container-registry.oracle.com/database/free:latest
```

Then `docker compose up -d --wait` as usual. The image is pinned-by-pull, so compose won't re-resolve to a different arch.

On amd64 Linux hosts this is a no-op (the existing image's `Architecture` already matches). The check costs nothing and saves an hour of confused debugging the first time someone on a Mac runs the skill.

## Healthcheck — why and how

`docker compose up -d` returns before the database is ready. First boot takes ~90-120 seconds; subsequent boots ~30s. The compose file uses the image's own status script:

```yaml
test: ["CMD-SHELL", "/opt/oracle/checkDBStatus.sh"]
interval: 15s
retries: 20
start_period: 90s
```

`checkDBStatus.sh` ships inside the image and returns 0 only when the PDB is OPEN. It does not parse sqlplus output, so it can't false-positive on error banners.

**Why not `sqlplus | grep '1'`?** The previous template used `echo 'SELECT 1 FROM DUAL;' | sqlplus -L SYSTEM/${ORACLE_PWD}@localhost:1521/FREEPDB1 | grep -q '1'`. When the container starts under the wrong arch (see above) the entrypoint aborts, no Oracle processes ever start, and sqlplus returns an `ORA-01034: ORACLE not available` banner that contains the digit `1`. The grep matched the error text, compose reported HEALTHY, and the user only discovered the DB was dead when the first `oracledb.connect()` raised minutes later. The image's own script side-steps that whole class of bug.

The skill MUST `docker compose up -d --wait` (which respects healthchecks) or poll the healthcheck status before it runs any Python that touches the DB. Otherwise the user gets a confusing `ORA-12541: TNS:no listener` mid-script and assumes the skill is broken.

## DSN formats

| Where | Form |
| --- | --- |
| Default (skills) | `localhost:1521/FREEPDB1` |
| Easy connect string | `oracledb.connect(user="SYSTEM", password=PWD, dsn="localhost:1521/FREEPDB1")` |
| Autonomous DB (out of scope v1) | mTLS wallet path; the skill detects this case and asks the user to provide their own wallet |

## Common ORA codes the skill should translate for the user

| Code | Means | Skill should say |
| --- | --- | --- |
| ORA-12541 | TNS:no listener | "Container isn't ready yet — wait for the healthcheck." |
| ORA-01017 | Invalid credentials | "ORACLE_PWD in .env doesn't match the running container. `docker compose down -v` to wipe the volume, then re-up." |
| ORA-12514 | Listener up but service unknown | "Use `FREEPDB1`, not `FREE`. Some online docs are wrong about this." |
| ORA-00942 | Table or view does not exist | "If you just changed table_name in the skill, run the schema setup again." |

## What the skill does NOT do

- It does not pull the image manually with `docker pull`. `docker compose up` does it.
- It does not configure backup, archive logging, or PDB cloning. Out of scope for v1.
- It does not enable wallet auth — that's an Autonomous-DB topic.
- It does not change ports. If the user has a port conflict, they edit the compose file by hand.

## Exemplar

`~/git/personal/oracle-aidev-template/docker-compose.yml` (lines 1-80) is the source pattern. The version above is a tightened, commented-up rewrite of it.
