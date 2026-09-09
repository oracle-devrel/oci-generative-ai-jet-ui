# Running the workshop with Podman

The setup launcher (`01_start_oracle.sh`) auto-detects Podman when Docker is
not available, so most users do not need to read this page. Read on only if
you are running rootless Podman and hit friction.

## Quick start

    bash .claude/skills/soccer-workshop-setup/scripts/01_start_oracle.sh

The launcher prefers `docker`; if Docker is absent it falls back to `podman`
(with `podman compose` or `podman-compose`). No flag is required.

## Rootless Podman on Linux

Rootless Podman maps your UID into the container namespace. Two common
friction points:

1. **Volume label for SELinux.**
   On SELinux-enforcing hosts (Fedora, RHEL, Rocky, etc.) the Oracle container
   cannot write to a host-mounted volume unless the volume carries the `:z`
   (shared) or `:Z` (private) relabelling suffix. If you see
   `ORA-27040: file create error` or similar permission errors at first boot,
   edit `docker/docker-compose.yml` and append `:z` to the volume line:

       volumes:
         - oracle_data:/opt/oracle/oradata:z

2. **Systemd socket vs. DOCKER_HOST.**
   Rootless Podman exposes a socket at
   `$XDG_RUNTIME_DIR/podman/podman.sock`. If `podman compose` cannot find the
   socket, export:

       export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/podman/podman.sock

   then re-run the launcher.

## Apple Silicon (arm64 Mac)

The launcher automatically selects `gvenzl/oracle-free:latest` on arm64 Macs
because the official `container-registry.oracle.com/database/free` image is
amd64-only. The gvenzl image exposes the same `FREEPDB1` pluggable database
and accepts the same `ORACLE_PASSWORD` environment variable, so `.env` and
`ORACLE_DSN` need no changes.

Podman Desktop on Apple Silicon works the same way as Docker Desktop: it runs
a Linux VM under the hood, so the arm64 detection (`uname -m`) inside that VM
correctly reports `arm64`.

## Overriding the image

If you want to force a specific image regardless of arch or engine, set
`ORACLE_IMAGE` before running the launcher:

    ORACLE_IMAGE=gvenzl/oracle-free:23-slim bash \
      .claude/skills/soccer-workshop-setup/scripts/01_start_oracle.sh

Both the official Oracle image and the gvenzl image expose `FREEPDB1` and use
the same admin password env var after the launcher's compatibility shim
(section "Admin password compatibility" in `01_start_oracle.sh`).

## Checking container status

Replace `docker` with `podman` in the standard commands:

    podman ps
    podman logs -f soccer-oracle
    podman inspect --format='{{.State.Health.Status}}' soccer-oracle
