# Container troubleshooting

Quick reference for failures you may hit when running `01_start_oracle.sh`.

---

## The container engine is not found

**Symptom:** The launcher prints `ERROR: no working container engine found.`

**Fix:** Install Docker (<https://docs.docker.com/get-docker/>) or Podman
(<https://podman.io/>). On Docker, also make sure the daemon is running and
your user is in the `docker` group:

    sudo usermod -aG docker $USER   # then log out and back in

---

## No compose command found

**Symptom:** The launcher prints `ERROR: found 'docker' but no compose command.`

**Fix:** Install the compose plugin.

- Docker: `sudo apt install docker-compose-plugin` (Debian/Ubuntu) or follow
  <https://docs.docker.com/compose/install/>.
- Podman: `pip install podman-compose` or install the `podman-compose` package
  from your distro.

---

## Port 1525 is already in use

**Symptom:** `docker compose up` (or `podman compose up`) exits with a bind
error on port 1525.

**Fix:** Find the conflicting container:

    docker ps        # or: podman ps

Then either stop that container or edit `docker/docker-compose.yml` to map a
different host port (and update `ORACLE_DSN` in `.env` to match).

---

## Container never becomes healthy (timeout after 7.5 min)

**Symptom:** The launcher polls for 90 × 5 s and then exits with
`Oracle did not become healthy in time.`

**Common causes and fixes:**

1. **Not enough memory.** Oracle AI Database Free needs at least 2 GB RAM
   available to the container engine. Check Docker Desktop / Podman Machine
   memory settings.
2. **Cold image pull still in progress.** On a slow connection the first `docker
   compose up` can take several minutes just to download the image before the
   healthcheck even starts. Watch `docker logs -f soccer-oracle` to see where
   it is.
3. **SELinux blocking writes (rootless Podman on Linux).** See
   [PODMAN.md](PODMAN.md) — you may need to add `:z` to the volume line in
   `docker-compose.yml`.

---

## Apple Silicon: image/platform error

**Symptom:** Docker or Podman refuses to run the amd64 image on an arm64 Mac,
or the container starts but crashes immediately.

**Fix:** The launcher should automatically select `gvenzl/oracle-free:latest`
on arm64. Confirm:

    uname -m   # should print arm64

If you have set `ORACLE_IMAGE` manually to the official amd64 image, unset it
and re-run:

    unset ORACLE_IMAGE
    bash .claude/skills/soccer-workshop-setup/scripts/01_start_oracle.sh

See [PODMAN.md](PODMAN.md) for more Apple Silicon details.

---

## ORA-27040 or permission denied on volume (rootless Podman)

**Symptom:** First-boot log shows `ORA-27040: file create error` or a
`permission denied` on `/opt/oracle/oradata`.

**Fix:** Add the SELinux relabelling suffix to the volume in
`docker/docker-compose.yml`:

```yaml
volumes:
  - oracle_data:/opt/oracle/oradata:z
```

See [PODMAN.md](PODMAN.md) for the full rootless Podman guide.

---

## Healthcheck false positives (grep matching release banner)

**Background (for contributors):** Searching for `1` in `sqlplus` output
matches the release banner (`Release 23.x.x`) and connection failures
(`ORA-01017`), giving false-healthy results. The healthcheck in
`docker-compose.yml` uses `SELECT 424242` and greps for `^\s*424242\s*$` to
avoid this.
