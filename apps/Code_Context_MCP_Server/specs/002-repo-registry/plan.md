# Implementation Plan: Database Schema and Repository Registry

**Branch**: `002-repo-registry` | **Date**: 2026-10-10 | **Spec**: [repo-registry.spec.md](./repo-registry.spec.md)

## Summary

The phase 1 container is renamed `oracle26ai` and keeps its volume. A new `schema` module holds ordered migrations as SQL in Python. They create `ccctx_repos`, `ccctx_files` and `ccctx_symbols` under the application user and record each applied migration in `ccctx_migrations`. A new `registry` module is the core both interfaces call. It validates and registers a directory, and lists repositories with their file and symbol counts. The `ccctx` command line (`repo add`, `repo list`, `db migrate`) and a new MCP tool `list_repositories` are thin wrappers over it. No new dependency is added. Migrations are plain SQL run through python-oracledb.

## Technical Context

- **Language**: Python 3.11, uv project from phase 1.
- **Dependencies**: `oracledb`, `mcp`, `python-dotenv`, already installed. No migration library and no ORM.
- **Storage**: Oracle AI Database 26ai Free, FREEPDB1, application user schema, named volume `oradata`.
- **Testing**: pytest. Database tests skip with a reason when the database is unreachable, as in phase 1. MCP tests use the in-memory client session.
- **Performance**: each command answers in under 2 s with the database up, and fails in under 5 s with it down (SC-006). `db.connect` already uses a 3 s TCP timeout and no retries. The migration check adds one query per command.
- **Constraints**: credentials come from the environment only. Registering never reads inside the directory beyond `is_dir()`.

## Constitution Check

| Principle | Assessment |
|---|---|
| I. Database-Native Intelligence | PASS. All state lives in Oracle. No extra infrastructure. |
| II. Structure-Aware Ingestion | PASS. Each symbol row carries repository (via file), path, language, name, kind, line range and content hash. `kind` includes `chunk` so fallback windowing can be flagged later. Repositories sit side by side and every row is reachable by repository. |
| III. MCP as the Single Interface | PASS. `list_repositories` exposes the registry over MCP. The CLI and the tool both call `registry`. The result is structured and includes paths. |
| IV. Hybrid, Explainable Retrieval | PASS. No retrieval in this step. |
| V. Self-Improvement with Provenance | PASS. No learned state in this step. |
| VI. Measured Quality (Test-First) | PASS. Tests for schema, registry, CLI and the new tool's contract are written first. The existing one-tool test is updated in the same change. |
| VII. Safety & Simplicity | PASS. Registration only checks that the path is a directory. Credentials come from `.env`. Migrations are ordered and re-runnable (`ccctx_migrations`). There is one module per concern and no plugin layer. |

Re-checked after Phase 1 design: still PASS. The data model and contracts add nothing beyond the rows above.

## Project Structure

```text
compose.yaml                         # container_name ccctx-db -> oracle26ai
pyproject.toml                       # + ccctx = "golestan_code_mcp.cli:main"
README.md                            # schema, ccctx commands, container name
src/golestan_code_mcp/
  schema.py                          # MIGRATIONS list + migrate(conn) -> applied versions
  registry.py                        # validate_name, add_repo, list_repos, errors
  cli.py                             # ccctx: repo add | repo list | db migrate
  server.py                          # + list_repositories tool
tests/
  test_schema.py                     # tables exist, re-run is a no-op, migrations recorded
  test_registry.py                   # validation, duplicates, counts, cascade
  test_cli.py                        # output format, exit codes, unreachable DB
  test_server.py                     # tool list now [health, list_repositories]; tool contract
```

**Structure Decision**: one module per concern inside the existing package. `registry` is the shared core required by constitution III. `cli` and `server` only parse input and format output.

## Success Criteria Verification

| Criterion | How it is checked |
|---|---|
| SC-001 | Time `docker compose up -d` until the ready log line, then `ccctx db migrate`, on a fresh volume and on a warm one. |
| SC-002 | `test_schema` runs `migrate` 3 times and compares row counts and the migration table. |
| SC-003 | Run `ccctx repo add` for flask and gin, then `ccctx repo list`, against the real sample repositories. |
| SC-004 | Register, then `docker compose restart` and `down`/`up`, then list again. |
| SC-005 | `test_registry` and `test_cli`: the 5 refusals each exit non-zero and the repository count is unchanged. |
| SC-006 | `test_cli` times each command with the database up and with `DB_PORT=1`. |
| SC-007 | `test_server` compares `list_repositories` with `registry.list_repos`, field for field. |
