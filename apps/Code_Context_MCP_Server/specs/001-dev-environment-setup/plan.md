# Implementation Plan: Development Environment Setup

**Branch**: `001-dev-environment-setup` | **Date**: 2026-10-10 | **Spec**: [dev-environment-setup.spec.md](./dev-environment-setup.spec.md)

> **Scale note**: about 15 small files across four areas (container, Python packaging, three entry points, tests) plus the README. Each file is short. The risk is in the seams: the database's slow first start, Windows path and quoting differences, and keeping secrets out of output.

## Summary

Give a developer a reproducible local setup for `golestan_code_mcp` in one sitting. Oracle AI Database 26ai Free runs from a Compose file with a named volume and a first-run script that creates the application user. A uv-managed Python 3.11 package pins the database driver (`oracledb`, thin mode), Tree-sitter with Python and Go grammars, the MCP SDK and pytest. The package ships three console commands: the stub stdio MCP server with a `health` tool, a database connectivity check, and a sample-repository cloner. Every command is a Python entry point, so one invocation works in both PowerShell and a POSIX shell.

## Technical Context

**Language/Version**: Python 3.11 (pinned with `.python-version`; 3.11.8 on the reference machine)
**Primary Dependencies**: `mcp[cli]` 1.x (FastMCP; the `cli` extra provides `mcp dev` for the Inspector), `oracledb`, `tree-sitter`, `tree-sitter-python`, `tree-sitter-go`, `python-dotenv`; dev: `pytest`
**Storage**: Oracle AI Database 26ai Free, image `container-registry.oracle.com/database/free`, pluggable database `FREEPDB1`
**Testing**: pytest. Database tests skip with a reason when the database is unreachable.
**Target Platform**: Windows 11 with Docker (Rancher Desktop) and macOS/Linux with Docker
**Project Type**: single Python package exposing an MCP stdio server
**Performance Goals**: health tool answers within 5 s when the database is down (bounded connect timeout)
**Constraints**: no secret in any committed file or script output; sample repositories live outside this project

## Constitution Check

*Gate: checked before Phase 0 and again after Phase 1. Both passes: PASS.*

| Principle | Assessment |
|---|---|
| I. Database-Native Intelligence | PASS. The database is Oracle 26ai and the check confirms `VECTOR` works. No embedding happens yet. |
| II. Structure-Aware Ingestion | PASS. Tree-sitter grammars for Python and Go are installed and proven by the smoke test. |
| III. MCP as the Single Interface | PASS. The only server surface is an MCP tool (`health`). The CLIs are developer setup tools, not a second query interface. |
| IV. Hybrid, Explainable Retrieval | PASS. No retrieval in this feature. |
| V. Self-Improvement with Provenance | PASS. No notes or feedback in this feature. |
| VI. Measured Quality (Test-First) | PASS. Parser, database and server tests are written before the code they cover. The server test covers the `health` contract. |
| VII. Safety & Simplicity | PASS. Credentials come from `.env` (ignored by git). The cloner never runs or imports cloned code and refuses a folder inside the project. Three modules, no abstraction layers. |

## Project Structure

### Documentation (this feature)

```text
specs/001-dev-environment-setup/
├── plan.md
├── research.md
├── data-model.md
└── contracts/
    ├── health-tool.md
    └── cli.md
```

### Source Code (repository root)

```text
compose.yaml                     # Oracle 26ai Free, named volume, healthcheck, port from .env
db/startup/01_app_user.sh        # every start: ensure app user in FREEPDB1 from env
.env.example                     # every setting, placeholder secrets
.gitignore                       # .env, .venv, __pycache__, caches
.python-version                  # 3.11
pyproject.toml                   # deps + console scripts
uv.lock                          # exact pins
README.md                        # prerequisites, ordered setup, Inspector, Claude Code config
src/golestan_code_mcp/
├── __init__.py                  # __version__
├── config.py                    # load .env, validate, redacted repr
├── db.py                        # connect(), check() + golestan-check-db entry point
├── samples.py                   # golestan-clone-samples entry point
└── server.py                    # FastMCP server, health tool, golestan-code-mcp entry point
tests/
├── fixtures/sample.py
├── fixtures/sample.go
├── test_parser.py               # FR-005
├── test_config.py               # missing setting named, secret never in message
├── test_db.py                   # FR-003, skips when DB down
├── test_samples.py              # refuses in-project folder, idempotent skip
└── test_server.py               # health contract, DB up and down
```

**Structure Decision**: one `src/` package. The parser has no module yet: the smoke test walks the tree itself, and an extraction module arrives with the ingestion feature that needs it.

## Verification of Success Criteria

| Criterion | How it is verified |
|---|---|
| SC-001 | A dry run of the README on a clean clone, timed, during implement. |
| SC-002, SC-003 | `test_db.py` writes a row; README step restarts the container and re-runs the check three times. |
| SC-004 | `test_parser.py` asserts the exact set of names and line ranges in each fixture. |
| SC-005 | `test_server.py` drives the server through an in-memory MCP client with the DB up and with a bad port; a manual Inspector run confirms. |
| SC-006 | `test_samples.py` runs the cloner twice against a local bare repo. |
| SC-007 | `test_config.py` asserts the password never appears in errors or repr; `.env` is in `.gitignore`. |
