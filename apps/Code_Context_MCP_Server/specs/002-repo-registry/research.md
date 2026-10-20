# Research: Database Schema and Repository Registry

## Migrations as SQL inside a Python module

- **Decision**: `schema.MIGRATIONS` is an ordered list of `(version, name, [statements])`. `migrate(conn)` creates `ccctx_migrations` if it is missing, reads the applied versions, and runs each missing migration's statements, then inserts its row. It returns the versions it applied.
- **Rationale**: Oracle commits DDL implicitly, so a migration cannot be rolled back as one transaction. Recording the version only after all of its statements succeed, and making each statement idempotent where Oracle allows (ignore ORA-00955 "name already used"), lets a half-applied migration be re-run safely. Keeping the SQL in a module means no package data to ship and no file lookup.
- **Alternatives considered**: `.sql` files under `db/migrations` need a statement splitter and package data. Alembic or Liquibase is a new dependency for three tables. Running scripts from the container's `scripts/startup` would require the DBA account and hide the schema from the Python tests.

## When migrations run

- **Decision**: `ccctx db migrate` applies them explicitly. `ccctx repo add`, `ccctx repo list` and `list_repositories` also call `migrate` first.
- **Rationale**: a fresh database works with no extra step (spec Assumptions). Once everything is applied the check is one `select` on a tiny table, well inside the 2 s budget.
- **Alternatives considered**: migrating only on an explicit command makes the first `repo add` on a new volume fail with ORA-00942. Migrating at server start leaves the CLI unprotected.

## Table names and keys

- **Decision**: `ccctx_repos`, `ccctx_files`, `ccctx_symbols` and `ccctx_migrations`, with identity primary keys and foreign keys `on delete cascade`. Uniqueness: repository `name`, repository `path`, and file `(repo_id, path)`.
- **Rationale**: the `ccctx_` prefix matches the phase 1 `ccctx_smoke` table. Cascades give FR-009 in the database. Unique constraints make the race in the spec's edge cases safe: the loser gets ORA-00001.
- **Alternatives considered**: a `repo_id` copy on symbols would be faster for filtering but stores the same fact twice. Add it when search needs it.

## Validation lives in the database and in `registry`

- **Decision**: `registry` checks the name against `^[a-z0-9_-]{1,64}$` and the path with `Path(path).expanduser().resolve()` plus `is_dir()`, before touching the database. The database repeats the name rule as a `check` constraint, and the symbol kind as a `check (kind in (...))`.
- **Rationale**: the command fails before connecting when the input is bad, and the database still refuses bad rows written by any later code.
- **Alternatives considered**: database-only checks give worse messages and still need a connection for a typo.

## Symbol kinds

- **Decision**: `function`, `method`, `class`, `interface`, `type`, `module`, `chunk`.
- **Rationale**: these cover Python and Go top-level units (Go structs and interfaces become `type` and `interface`). `chunk` is the fallback window that constitution II says must be flagged.
- **Alternatives considered**: free text gives no guarantee to search filters. A lookup table is heavier than a check constraint for a fixed set.

## Paths

- **Decision**: store `str(Path(p).expanduser().resolve())`. Uniqueness is on that string.
- **Rationale**: `resolve()` removes `..` and symlinks and, on Windows, returns the directory's real casing, so `C:\x\Flask` and `c:\x\flask` map to one row. File paths inside a repository are stored relative, with `/` separators, for the indexing step.
- **Alternatives considered**: lowercasing paths breaks case-sensitive file systems.

## Exit codes and the "still starting" state

- **Decision**: `0` success. `1` refused input or missing configuration. `2` database unreachable or still starting. Errors go to stderr as `error: <reason>`.
- **Rationale**: this matches `golestan-check-db`. A still-starting database answers quickly with ORA-01033 or ORA-12514, so the command reports "database is still starting" and exits 2 instead of waiting. Waiting is `golestan-check-db --wait`'s job.
- **Alternatives considered**: a distinct code per refusal gives scripts little and is more surface to keep stable.

## List output format

- **Decision**: left-aligned `NAME` and `PATH` columns sized to their widest value, right-aligned `FILES` and `SYMBOLS`, separated by two spaces. With no repositories: `no repositories registered`, exit 0.
- **Rationale**: it matches the sample output in the request. Plain `str.ljust` and `rjust` need no table library.

## MCP tool shape

- **Decision**: `list_repositories()` with no input returns `{database, reason, repositories: [{name, path, files, symbols}]}`. Errors are returned as data with `database: "unreachable"`, as `health` does.
- **Rationale**: same shape and error behaviour as the existing tool. An empty registry is `repositories: []`.
- **Alternatives considered**: raising an MCP error makes clients handle a down database as a crash, which the phase 1 contract already rejected.

## Container rename

- **Decision**: `container_name: oracle26ai`. The service key stays `db` and the project name is unchanged, so the volume `code_context_mcp_server_oradata` is reused.
- **Rationale**: the request's test commands use `docker logs oracle26ai`. Compose finds the old container by service label and replaces it on the next `up`.
- **Alternatives considered**: a top-level `name:` in `compose.yaml` would change the volume name and appear to lose the data. A comment in `compose.yaml` warns against it.
