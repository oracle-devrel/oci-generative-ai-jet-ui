# Tasks: Database Schema and Repository Registry

**Input**: [repo-registry.spec.md](./repo-registry.spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

Tests come first in each phase and must fail before the code they cover exists (constitution VI). Database tests skip with a reason when the database is unreachable.

US2 (register) and US3 (list) share one phase. Both are P1 and both live in `registry.py` and `cli.py`, so splitting them would put one file under two owners.

## Phase 1: Setup

**Wave 1 — independent (different files):**

- [x] **T001** [P] [US1] Rename the container to `oracle26ai`, keep service `db` and volume `oradata`, and add a comment warning that a top-level `name:` would change the volume name (FR-001, FR-002) · compose.yaml
- [x] **T002** [P] [US2] Add the console script `ccctx = "golestan_code_mcp.cli:main"` (FR-010) · pyproject.toml

## Phase 2: Foundational (US1, Priority: P1): the schema

Files: src/golestan_code_mcp/schema.py, tests/test_schema.py

**Goal**: the four `ccctx_` tables exist under the application user and survive restarts.

**Independent Test**: run `migrate` on a fresh database, list the tables, run it again and see nothing change.

### Tests

**Wave 1:**

- [x] **T003** [US1] Tests (all skip when the DB is down):
  - `migrate` creates `ccctx_repos`, `ccctx_files`, `ccctx_symbols` and `ccctx_migrations`, and records version 1.
  - Running it 3 times applies nothing more and leaves row counts unchanged (SC-002).
  - The name and kind check constraints reject bad rows.
  - `end_line < start_line` is rejected.
  - Deleting a repository cascades to its files and symbols (FR-009).

  Tests that insert rows use a unique name prefix and clean up after themselves. · tests/test_schema.py

### Implementation

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T004** [US1] `MIGRATIONS` holds version 1, `core tables`, with the SQL from contracts/schema.md. `migrate(conn) -> list[int]`:
  - Creates `ccctx_migrations` if it is missing (ignore ORA-00955).
  - Runs each missing version's statements in order, ignoring ORA-00955.
  - Inserts the version row only after its statements succeed, then commits.

  (FR-003, FR-004, FR-005 to FR-009) · src/golestan_code_mcp/schema.py

**⟶ Wait for T004, then:**

- [x] **T005** [US1] Run `docker compose up -d`, then confirm `docker ps` shows `oracle26ai` on 1521 and `docker logs oracle26ai` shows `DATABASE IS READY TO USE!`. Then run `uv run pytest tests/test_schema.py` until it is green (FR-001, FR-002, FR-003). · src/golestan_code_mcp/schema.py

**Checkpoint**: the schema exists, is safe to re-run, and enforces its constraints.

## Phase 3: US2 + US3 (Priority: P1): register and list repositories

Files: src/golestan_code_mcp/registry.py, src/golestan_code_mcp/cli.py, tests/test_registry.py, tests/test_cli.py

**Goal**: `ccctx repo add <path> --name <name>` registers a directory, and `ccctx repo list` shows every repository with its counts.

**Independent Test**: register two temporary directories, list them, and try each of the 5 refusals.

### Tests

**Wave 1 — independent (different files):**

- [x] **T006** [P] [US2] [US3] Registry tests:
  - `validate_name` accepts `flask` and `my-repo_2` and rejects `Flask`, `a b`, `a/b`, an empty name and 65 characters.
  - `add_repo` stores the resolved absolute path for `~` and relative paths.
  - It refuses a missing path, a file, a taken name and an already-registered directory (including the same directory via `..`), with the repository count unchanged.
  - `list_repos` is sorted by name, with counts matching inserted files and symbols.

  DB tests skip when it is down, and use unique names and clean up. · tests/test_registry.py
- [x] **T007** [P] [US2] [US3] CLI tests via `cli.main(argv)` and capsys:
  - `repo add` success line and exit 0.
  - Each refusal exits 1 with its contracts/cli.md message.
  - The `repo list` header is `NAME  PATH  FILES  SYMBOLS` with aligned rows, and an empty registry prints `no repositories registered`.
  - `db migrate` output.
  - With `DB_PORT=1` and a fake password, each command exits 2 in under 5 s and the password is not in the output (FR-014, SC-006).

  The empty-registry case runs against a separate monkeypatched `list_repos` so it does not depend on DB contents. · tests/test_cli.py

### Implementation

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T008** [US2] [US3] Core module:
  - `NAME_RE`, plus `RegistryError` subclasses for each refusal, each carrying its message.
  - `validate_name(name)`.
  - `resolve_dir(path) -> Path`: `expanduser().resolve()`, then `exists`/`is_dir` checks only, never reading the directory's contents.
  - `add_repo(conn, path, name) -> Repo`: checks for an existing name or path first, and maps ORA-00001 from a race to the same errors.
  - `list_repos(conn) -> list[Repo]`: one query with left joins and counts, ordered by name.
  - `Repo` dataclass with `name, path, files, symbols`.

  (FR-005, FR-010, FR-011, FR-012, FR-013) · src/golestan_code_mcp/registry.py

**⟶ Wait for T008, then:**

- [x] **T009** [US2] [US3] The `ccctx` command:
  - argparse with subcommands `repo add <path> --name`, `repo list` and `db migrate`. Each opens `db.connect(config.load())`, calls `schema.migrate`, then calls `registry`.
  - The table is formatted with `ljust`/`rjust` and two-space gaps.
  - Exit codes: 1 for `ConfigError` or `RegistryError`. 2 for `oracledb.Error`, reporting "database is still starting" for `db.STARTING_CODES` and otherwise `db.describe(e)`.
  - `sys.exit(main())`.

  (FR-010, FR-011, FR-012, FR-014) · src/golestan_code_mcp/cli.py

**⟶ Wait for T009, then:**

- [x] **T010** [US2] [US3] Run `uv run pytest tests/test_registry.py tests/test_cli.py` until green · src/golestan_code_mcp/cli.py

**Checkpoint**: repositories can be registered, refused and listed from the command line.

## Phase 4: US4 (Priority: P3): list repositories over MCP

Files: src/golestan_code_mcp/server.py, tests/test_server.py

**Goal**: an MCP client sees the same repository list as `ccctx repo list`.

**Independent Test**: call `list_repositories` through the in-memory client and compare it with `registry.list_repos`.

### Tests

**Wave 1:**

- [x] **T011** [US4] Tests:
  - Update the tool-list test to expect exactly `["health", "list_repositories"]`, each with a description and no input properties.
  - `list_repositories` matches `registry.list_repos` field for field when the DB is up (SC-007, skip when down).
  - With `DB_PORT=1` it returns `database: "unreachable"`, a reason without the password, `repositories: []` and no error, in under 5 s.

  · tests/test_server.py

### Implementation

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T012** [US4] Add the pydantic models `RepoInfo` and `RepoList`, and the `list_repositories` tool. It connects, calls `schema.migrate` and then `registry.list_repos`, and returns errors as data the way `health` does (FR-015) · src/golestan_code_mcp/server.py

**⟶ Wait for T012, then:**

- [x] **T013** [US4] Run `uv run pytest tests/test_server.py` until green · src/golestan_code_mcp/server.py

**Checkpoint**: the registry is visible to MCP clients.

## Phase 5: Polish

- [x] **T014** Document the `ccctx` commands, the schema, `docker logs oracle26ai` and the exit codes, and update the layout section · README.md

**⟶ Wait for T014, then:**

- [x] **T015** Run `uv run pytest` with the database up and again with it stopped. Both must be green, with DB tests skipped in the second (SC-002, SC-005, SC-006, SC-007).

**⟶ Wait for T015, then:**

- [x] **T016** Walk through the request's test, in order:
  1. Run `docker ps` and `docker logs oracle26ai | tail -5`.
  2. Run `ccctx repo add` for `../ccctx-repos/flask` and `gin`, then `ccctx repo list`, and confirm 2 rows with 0 files and 0 symbols (SC-003).
  3. Run `docker compose restart` and `down`/`up`, then list again (SC-004).
  4. Time a first start on a scratch volume and a warm start (SC-001).
  5. Sweep for secrets in tracked files and command output.
- [x] **T017** Call `list_repositories` over stdio and from the MCP Inspector, and compare it with `ccctx repo list` (SC-007).

## Dependencies & Execution Order

- Setup → Foundational → US2+US3 → US4 → Polish. US4 needs `registry.py` from US2+US3. The Polish tasks run in order.
- **Setup**: Wave 1 (T001, T002) in parallel.
- **Foundational**: T003, then T004, then T005.
- **US2+US3**: Wave 1 (T006, T007) in parallel, then T008, then T009, then T010.
- **US4**: T011, then T012, then T013.
- **Polish**: T014, then T015, then T016 and T017.
