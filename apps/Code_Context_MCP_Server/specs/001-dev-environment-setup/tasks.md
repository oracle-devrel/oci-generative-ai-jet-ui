# Tasks: Development Environment Setup

**Input**: [plan.md](./plan.md), [dev-environment-setup.spec.md](./dev-environment-setup.spec.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [research.md](./research.md)

> **Scale note**: 25 tasks over about 20 files in six phases. US4 imports `connect()` from US1's `db.py`, so US4 starts after US1. Tests that need the database skip without it. Rancher Desktop must be running for US1's checkpoint and the Polish validation.

## Phase 1: Setup

**Wave 1 — independent (different files):**

- [x] **T001** [P] Ignore `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/` · .gitignore
- [x] **T002** [P] Pin Python 3.11 · .python-version
- [x] **T003** [P] List every setting from contracts/cli.md with placeholder values and a comment on each · .env.example
- [x] **T004** [P] Package metadata with `__version__ = "0.1.0"` · src/golestan_code_mcp/__init__.py

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T005** Define the package: `requires-python >=3.11`, deps `mcp[cli]>=1.12,<2`, `oracledb`, `tree-sitter`, `tree-sitter-python`, `tree-sitter-go`, `python-dotenv`, dev group `pytest`, console scripts `golestan-code-mcp`, `golestan-check-db`, `golestan-clone-samples`, src layout (FR-004) · pyproject.toml

**⟶ Wait for T005, then:**

- [x] **T006** Run `uv sync` and commit the lockfile (FR-004) · uv.lock

## Phase 2: Foundational

Files: src/golestan_code_mcp/config.py, tests/test_config.py

**Wave 1:**

- [x] **T007** Write failing tests: all missing or blank required settings named in one error, bad `DB_PORT` named, password never in error text, `repr()` or `str()`, defaults applied, `repos_dir` resolved against the project root, existing env wins over `.env` (FR-002) · tests/test_config.py

**⟶ Wait for T007, then:**

- [x] **T008** Load `.env` with python-dotenv (no override), validate per data-model.md §1, expose a frozen config with a redacted repr and a `ConfigError` (FR-002) · src/golestan_code_mcp/config.py

## Phase 3: User Story 1 - Start the local database with one command (P1) 🎯 MVP

**Goal**: one command starts Oracle 26ai; the check confirms login, version and `VECTOR`; data survives a restart.
**Independent Test**: `docker compose up -d`, then `uv run golestan-check-db` prints the four lines from contracts/cli.md.
Files: compose.yaml, db/setup/01_app_user.sh, src/golestan_code_mcp/db.py, tests/test_db.py

### Tests

- [x] **T009** [US1] Write failing tests: skip with a reason when the DB is unreachable; `check()` returns ok, a version and `vector_ok`; create `ccctx_smoke` if missing and insert a row; row count grows; check output never contains the password (FR-003, FR-006) · tests/test_db.py

### Implementation

**Wave 1 — independent (different files):**

- [x] **T010** [P] [US1] Service on `container-registry.oracle.com/database/free:latest` with `ORACLE_PWD`, `DB_USER`, `DB_PASSWORD` from `.env`, port `${DB_PORT:-1521}:1521`, named volume on `/opt/oracle/oradata`, `db/setup` mounted at `/opt/oracle/scripts/setup`, healthcheck `/opt/oracle/checkDBStatus.sh` (FR-001, FR-002) · compose.yaml
- [x] **T011** [P] [US1] First-run script: in `FREEPDB1` create `DB_USER` from env, grant `DB_DEVELOPER_ROLE`, quota unlimited on `USERS`; never echo the password; LF line endings (FR-001) · db/setup/01_app_user.sh
- [x] **T012** [P] [US1] `connect(cfg, timeout=3)` in thin mode; `check(cfg, wait)` retrying until the deadline per data-model.md §3 with no retry on auth errors; `VECTOR_DIMENSION_COUNT(TO_VECTOR('[1,2,3]'))` must be 3; `main()` with `--wait` and exit codes 0/1/2/3 from contracts/cli.md (FR-003) · src/golestan_code_mcp/db.py

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T013** [US1] Start the container, run `uv run golestan-check-db` and `uv run pytest tests/test_db.py`; fix until green (needs Docker running) · compose.yaml, src/golestan_code_mcp/db.py

**Checkpoint**: the database starts with one command and the check passes. US1 is independently usable.

## Phase 4: User Story 2 - Python project that installs and runs its checks (P1)

**Goal**: the parser finds function and class/type boundaries in Python and Go.
**Independent Test**: `uv run pytest tests/test_parser.py` passes with no database.
Files: tests/fixtures/sample.py, tests/fixtures/sample.go, tests/test_parser.py

### Tests

**Wave 1 — independent (different files):**

- [x] **T014** [P] [US2] Python fixture: two top-level functions, one class with a method, one decorated function · tests/fixtures/sample.py
- [x] **T015** [P] [US2] Go fixture: one function, one struct type, one method on it · tests/fixtures/sample.go

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T016** [US2] Parse each fixture with `Language(tree_sitter_python.language())` and `Language(tree_sitter_go.language())`; assert the exact set of `(name, kind, start_line, end_line)` per data-model.md §6; a missing grammar fails naming its package (FR-005, FR-006) · tests/test_parser.py

**Checkpoint**: `uv sync` then `uv run pytest` gives a green parser suite on a machine with no database.

## Phase 5: User Story 3 - Sample repositories ready to index (P2)

**Goal**: one idempotent command clones Flask and Gin outside the project.
**Independent Test**: run `uv run golestan-clone-samples` twice; the second run prints `present` for both.
Files: src/golestan_code_mcp/samples.py, tests/test_samples.py

### Tests

- [x] **T017** [US3] Write failing tests against local bare repos in a temp dir: clones and prints `cloned <name> <commit>`; second run prints `present` without network; target inside the project exits 1 and writes nothing; a non-git folder at the path is an error; a failed clone exits 2 naming the repo (FR-007) · tests/test_samples.py

### Implementation

- [x] **T018** [US3] Fixed repo list with the verbatim URLs, `clone(repos_dir, repos)` using `git` via `subprocess` (no shell), refuse a resolved path inside the project, `main()` with exit codes from contracts/cli.md (FR-007) · src/golestan_code_mcp/samples.py

**Checkpoint**: Flask and Gin sit in `../ccctx-repos` with recorded commits.

## Phase 6: User Story 4 - Reach a stub MCP server from an MCP client (P2)

**Goal**: a `golestan_code_mcp` stdio server whose `health` tool reports version and database reachability.
**Independent Test**: `uv run mcp dev src/golestan_code_mcp/server.py`, list tools, call `health`.
**Depends on**: US1 (`db.connect`).
Files: src/golestan_code_mcp/server.py, tests/test_server.py

### Tests

- [x] **T019** [US4] Write failing tests through an in-memory MCP client session: one tool named `health` with an empty input schema; DB up gives `reachable` and `reason` null (skip when down); `DB_PORT` on a closed port gives `unreachable`, a reason, `isError` false, under 5 s; missing `DB_PASSWORD` gives `unreachable` naming it (FR-008, FR-009) · tests/test_server.py

### Implementation

- [x] **T020** [US4] `FastMCP("golestan_code_mcp")`, a `health` tool returning the result shape in contracts/health-tool.md, catching every config and connect error into `unreachable`; `main()` runs stdio; logs go to stderr only (FR-008, FR-009) · src/golestan_code_mcp/server.py

**Checkpoint**: the Inspector lists and calls `health` with the database up and down.

## Phase 7: Polish

- [x] **T021** Write the README: prerequisites, ordered setup (`.env`, `docker compose up -d`, `uv sync`, check, clone, tests), restart persistence step, Inspector command, the Claude Code config snippet from contracts/cli.md, each command shown for PowerShell and POSIX where they differ (FR-010) · README.md
- [x] **T022** Run `uv run pytest` with the database up and again with it stopped; both green, DB tests skipped in the second (SC-004, SC-005, SC-006, SC-007)
- [x] **T023** Cold-start check three times: `docker compose down`, `up -d`, `golestan-check-db`; and confirm `ccctx_smoke` rows survive `stop`/`start` (SC-002, SC-003)
- [x] **T024** Connect the MCP Inspector and Claude Code with the README snippet; call `health` with the DB up and down (SC-005)
- [x] **T025** Secrets sweep: `git grep` the tracked files for the `.env` password values and check `git status` shows `.env` untracked (SC-007); time the README walkthrough on a clean clone (SC-001)

## Dependencies & Execution Order

- **Setup** (T001-T006) blocks everything. Wave 1 is parallel; T005 then T006.
- **Foundational** (T007-T008) blocks US1, US3 and US4. US2 needs only Setup.
- **US1** (T009-T013): T009, then Wave 1 (T010, T011, T012) in parallel, then T013.
- **US2** (T014-T016): Wave 1 (T014, T015), then T016. Can run alongside Foundational and US1.
- **US3** (T017-T018): after Foundational; parallel with US1, US2 and US4.
- **US4** (T019-T020): after US1 (imports `db.connect`).
- **Polish** (T021-T025): after all stories. T021 first, then T022-T025 in order.
