# Setup

## Prerequisites

- Docker (tested with Rancher Desktop), with about 12 GB free for the database image and data
- [uv](https://docs.astral.sh/uv/) (it installs Python 3.11 for you if needed)
- git
- Node.js, only for the MCP Inspector (`npx`)

## Installing

Every command below is the same in PowerShell and a POSIX shell unless shown otherwise. Run them from the project root.

**1. Create your `.env`.** Copy the example, then replace both passwords. Oracle passwords need at least 8 characters with an upper-case letter, a lower-case letter and a digit.

```powershell
Copy-Item .env.example .env     # PowerShell
```
```sh
cp .env.example .env            # POSIX
```

`.env` is ignored by git. No script prints its passwords.

**2. Start the database.** It runs as the container `oracle26ai` on port 1521. The first start creates the database and the application user, which takes a minute or two.

```sh
docker compose up -d
docker ps
docker logs oracle26ai | tail -5     # look for DATABASE IS READY TO USE!
```

If port 1521 is taken, set `DB_PORT` in `.env` before starting.

**3. Install the Python project.**

```sh
uv sync
```

**4. Check the database.** This waits up to 5 minutes for a first start, then prints the connection, the version, the vector check and the smoke table's row count.

```sh
uv run golestan-check-db
```

Exit codes: `0` ok, `1` a setting is missing, `2` unreachable or still starting, `3` connected but the `VECTOR` check failed.

**5. Clone the sample repositories.** Flask (Python) and Gin (Go) go to `../ccctx-repos` by default (set `CCCTX_REPOS_DIR` to change it; it must be outside this project). Running it again skips what is already there.

```sh
uv run golestan-clone-samples
```

**6. Run the tests.** Database tests are skipped, with a reason, when the database is down. The parser tests always run.

```sh
uv run pytest
```

## Checking that data persists

`uv run pytest` adds a row to the `ccctx_smoke` table on each run. Note the count, restart the container, and check it again:

```sh
uv run golestan-check-db
docker compose stop
docker compose start
uv run golestan-check-db --wait 300
```

The second count matches the first. `docker compose down` also keeps the data. Only `docker compose down -v` deletes it.
