# Research: Development Environment Setup

## Database image

- **Decision**: Oracle's official `container-registry.oracle.com/database/free:latest` (Oracle AI Database 26ai Free), run through Compose with a named volume on `/opt/oracle/oradata`.
- **Rationale**: the constitution names 26ai as the reference database. The official image includes AI Vector Search, honors `ORACLE_PWD`, ships a prebuilt database (so `/opt/oracle/scripts/setup` never runs) and runs scripts mounted at `/opt/oracle/scripts/startup` on every start, and ships `/opt/oracle/checkDBStatus.sh` for a healthcheck.
- **Alternatives considered**: `gvenzl/oracle-free` is faster to start and creates an app user from env vars, but it is community-maintained and its tags may trail the 26ai release. Autonomous Database Free (`adb-free`) needs `SYS_ADMIN` and FUSE and adds wallets: too heavy for a laptop.

## Application user

- **Decision**: a first-run shell script creates `DB_USER` in `FREEPDB1` with `DB_DEVELOPER_ROLE` and quota on `USERS`, reading the password from the container's environment.
- **Rationale**: the server never connects as `SYSTEM`, and no password lands in a committed SQL file.
- **Alternatives considered**: connecting as `SYSTEM` is simpler but breaks least privilege and would hide grant gaps until later.

## Database driver

- **Decision**: `oracledb` in thin mode, `tcp_connect_timeout` of 3 seconds.
- **Rationale**: pure Python, no Instant Client install on Windows, and it supports the `VECTOR` type. The short timeout keeps the health tool fast when the database is down.
- **Alternatives considered**: thick mode needs Instant Client; SQLAlchemy adds a layer nothing needs yet.

## VECTOR check

- **Decision**: `SELECT VECTOR_DIMENSION_COUNT(TO_VECTOR('[1,2,3]')) FROM dual` must return 3.
- **Rationale**: proves vector support with no DDL and nothing to clean up.
- **Alternatives considered**: creating a temporary table with a `VECTOR` column also works, but leaves objects behind if the check fails midway.

## Persistence test (SC-003)

- **Decision**: `test_db.py` creates a `ccctx_smoke` table if it is missing and inserts a row. The README's restart step re-runs the check, which reports the row count.
- **Rationale**: a restart cannot happen inside a unit test without driving Docker from tests.

## Python tooling

- **Decision**: uv with `pyproject.toml`, `uv.lock`, and `.python-version` set to 3.11. Install is `uv sync`, tests are `uv run pytest`.
- **Rationale**: uv is installed, creates the venv and pins exact versions in one command, and picks 3.11 even though Python 3.14 is first on PATH.
- **Alternatives considered**: `pip` plus `requirements.txt` needs a manual venv step and a separate lock tool.

## MCP SDK

- **Decision**: `mcp[cli]>=1.12,<2`, using `FastMCP` over stdio. The tool is named `health`.
- **Rationale**: 1.x is the widely deployed line and works with the Inspector via `uv run mcp dev`. The 2.0 line renames the server class to `MCPServer`. Moving later is a one-line import change.
- **Alternatives considered**: starting on 2.0 trades a stable API for a new one with fewer client reports.

## Parser

- **Decision**: `tree-sitter` plus the `tree-sitter-python` and `tree-sitter-go` wheel packages, loaded as `Language(tspython.language())`.
- **Rationale**: prebuilt wheels for Windows, no compiler needed, and one grammar package per language keeps the dependency list honest.
- **Alternatives considered**: `tree-sitter-languages` bundles every grammar but is unmaintained against current `tree-sitter` releases.

## Cross-shell commands

- **Decision**: every script is a Python console entry point (`golestan-check-db`, `golestan-clone-samples`, `golestan-code-mcp`), run with `uv run`.
- **Rationale**: one command line works in PowerShell and POSIX shells, which satisfies FR-010 without paired `.ps1` and `.sh` files.

## Repositories folder

- **Decision**: `CCCTX_REPOS_DIR`, default `../ccctx-repos` resolved against the project root. The cloner resolves both paths and refuses a target inside the project.
- **Rationale**: matches the challenge text and keeps sample code from being committed or indexed as project code.
