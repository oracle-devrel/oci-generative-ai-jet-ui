# Oracle AI Database Free container (soccer-oracle)

Used for the soccer analytics agent workshop. The container exposes Oracle on
host port **1525** (chosen to avoid conflicts with other Oracle containers
that often occupy 1521-1524).

## Bring up

    docker compose -f docker/docker-compose.yml up -d

First boot (cold image + initdb) takes 2-3 minutes. Subsequent starts
reuse the volume and come up in ~10 seconds.
If the container does not become healthy within 7.5 minutes, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
Watch progress with:

    docker logs -f soccer-oracle

### Docker or Podman, Intel or Apple Silicon

The setup launcher (`01_start_oracle.sh`) auto-detects your engine and arch:

- **Engine:** prefers `docker`, falls back to `podman` (`podman compose` / `podman-compose`).
- **Apple Silicon (arm64 Mac):** uses the ARM-native `gvenzl/oracle-free` image; the official `container-registry.oracle.com/database/free` image is amd64-only and will not run there.
- **Everything else:** uses the official amd64 image.

Both images expose `FREEPDB1` and accept the same admin password, so `.env` / `ORACLE_DSN` need no changes. You can override the image explicitly with `ORACLE_IMAGE=...`.

## Tear down (keep data)

    docker compose -f docker/docker-compose.yml stop

## Tear down (destroy data)

    docker compose -f docker/docker-compose.yml down -v

## Connect from host

DSN: `localhost:1525/FREEPDB1`
SYSTEM user: `system` / value of `ORACLE_ADMIN_PASSWORD` (defaults to `SoccerAdmin2026#` if unset — see `.env.example`).
The container binds to `127.0.0.1` only; remote access is intentionally not exposed.
The `soccer` user is created by the setup skill.

## See also

- [PODMAN.md](PODMAN.md) — rootless Podman setup, SELinux volume labels, Apple Silicon image selection.
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — quick reference for common container start-up failures.
