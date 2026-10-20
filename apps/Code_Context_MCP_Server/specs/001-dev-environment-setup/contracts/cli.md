# Contract: developer commands and environment

All commands are Python console entry points run with `uv run`, so the same line works in PowerShell and a POSIX shell. Output never contains a secret value (SC-007).

## Environment (`.env`, template in `.env.example`)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `ORACLE_PWD` | yes (container) | none | admin password for the container; used only by `compose.yaml` |
| `DB_USER` | yes | none | application user created in `FREEPDB1` on first start |
| `DB_PASSWORD` | yes | none | secret; never printed |
| `DB_HOST` | no | `localhost` | |
| `DB_PORT` | no | `1521` | also the host port published by `compose.yaml` |
| `DB_SERVICE` | no | `FREEPDB1` | |
| `CCCTX_REPOS_DIR` | no | `../ccctx-repos` | resolved against the project root; must be outside it |

A missing or blank required setting fails with a message naming the variable, e.g. `missing setting: DB_PASSWORD`.

## Commands

| Command | Purpose |
|---|---|
| `docker compose up -d` | start Oracle AI Database 26ai Free (`container-registry.oracle.com/database/free`) with a named volume on `/opt/oracle/oradata` |
| `docker compose stop` / `docker compose start` | stop and restart; data persists |
| `uv sync` | create the venv and install pinned dependencies from `uv.lock` |
| `uv run pytest` | run tests; database tests skip with a reason when the DB is unreachable |
| `uv run golestan-check-db` | connectivity check |
| `uv run golestan-clone-samples` | clone sample repositories |
| `uv run golestan-code-mcp` | start the stdio MCP server (see `health-tool.md`) |

## `golestan-check-db`

- Waits up to a bounded time (default 300 s, flag `--wait SECONDS`) for the database while it initializes.
- Success output (exit `0`):
  ```text
  connected: <DB_USER>@<DB_HOST>:<DB_PORT>/<DB_SERVICE>
  version: <database version banner>
  vector: ok (VECTOR)
  ccctx_smoke rows: <n>
  ```
  The `VECTOR` check runs `SELECT VECTOR_DIMENSION_COUNT(TO_VECTOR('[1,2,3]')) FROM dual` and requires `3`.
- Exit codes: `0` ok, `1` configuration error (names the setting), `2` unreachable or still starting after the wait (prints `still starting` when the listener answers but the service is not open yet), `3` connected but `VECTOR` check failed.

## `golestan-clone-samples`

Clones into `CCCTX_REPOS_DIR` (folder name `ccctx-repos` by default):

| Name | Language | URL | Local path |
|---|---|---|---|
| `flask` | Python | `https://github.com/pallets/flask.git` | `<CCCTX_REPOS_DIR>/flask` |
| `gin` | Go | `https://github.com/gin-gonic/gin.git` | `<CCCTX_REPOS_DIR>/gin` |

- Creates `CCCTX_REPOS_DIR` if missing.
- Per repository prints one line: `cloned <name> <commit>` or `present <name> <commit>`. An existing clone is skipped with no network access (idempotent).
- Exit codes: `0` ok, `1` target folder resolves inside the project (refused, nothing written), `2` a clone failed (message names the repository).
- Never runs, imports, or installs cloned code.

## Claude Code client configuration (README snippet)

```json
{
  "mcpServers": {
    "golestan_code_mcp": {
      "command": "uv",
      "args": ["run", "--directory", "<absolute project path>", "golestan-code-mcp"]
    }
  }
}
```
