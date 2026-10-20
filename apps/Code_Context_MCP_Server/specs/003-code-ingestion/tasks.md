# Tasks: Code Ingestion and Chunking

**Input**: [code-ingestion.spec.md](./code-ingestion.spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

Tests come first in each phase and must fail before the code they cover exists (constitution VI). Database tests skip with a reason when the database is unreachable.

The four user stories share two modules: the chunker (US2 structure and US3 fallback) and the ingest pipeline (US1 summary and US4 commit). So the phases follow those modules, not one phase per story. Each phase lists the stories it serves, and every file still has one owner.

## Phase 1: Setup

**Wave 1 — independent (different files):**

- [x] **T001** [P] [US2] Add `tree-sitter-javascript>=0.25` to dependencies and run `uv sync` · pyproject.toml
- [x] **T002** [P] [US1] Add `max_file_bytes(env)` (`CCCTX_MAX_FILE_BYTES`, default 1048576, must be a positive integer) and `vendor_dirs(env)` (`CCCTX_VENDOR_DIRS`, comma-separated, default `vendor,node_modules,third_party`), with tests for defaults, overrides and a bad value raising `ConfigError` (FR-002, FR-003) · src/golestan_code_mcp/config.py, tests/test_config.py

## Phase 2: Foundational (US4, US1): schema and repository lookup

Files: src/golestan_code_mcp/schema.py, src/golestan_code_mcp/registry.py, tests/test_schema.py, tests/test_registry.py

### Tests

**Wave 1 — independent (different files):**

- [x] **T003** [P] [US4] Schema tests (skip when the DB is down):
  - Migration 2 is recorded as version 2.
  - `ccctx_symbols.commit_sha` exists.
  - The check rejects `abc` and an uppercase SHA, and accepts both a 40-character and a 64-character hex SHA.
  - `migrate` run 3 times is still a no-op.

  `add_symbol` now passes a `commit_sha`. · tests/test_schema.py
- [x] **T004** [P] [US1] Registry tests:
  - `get_repo(conn, name)` returns `(id, path)` for a registered name.
  - It raises `RegistryError("no repository named '<name>'")` for an unknown name.
  - It raises `RegistryError` naming the path when the registered directory has been deleted.

  · tests/test_registry.py

### Implementation

**⟶ Wait for Wave 1 to finish, then:**

**Wave 2 — independent (different files):**

- [x] **T005** [P] [US4] Migration 2 per contracts/schema.md: `delete from ccctx_symbols`, then add `commit_sha varchar2(64) not null`, then add the `ccctx_symbols_commit_ck` hex check. Add `ORA-01430` and `ORA-02264` to `ALREADY_EXISTS` (FR-009) · src/golestan_code_mcp/schema.py
- [x] **T006** [P] [US1] `get_repo(conn, name) -> tuple[int, Path]`: `validate_name`, look up by name, then `resolve_dir` on the stored path (FR-018) · src/golestan_code_mcp/registry.py

**⟶ Wait for Wave 2 to finish, then:**

- [x] **T007** Run `uv run pytest tests/test_schema.py tests/test_registry.py tests/test_config.py` until green · src/golestan_code_mcp/schema.py

**Checkpoint**: symbols can carry a commit, and ingest can resolve a repository by name.

## Phase 3: Chunker (US2, US3, Priority: P1)

Files: src/golestan_code_mcp/chunker.py, tests/test_chunker.py, tests/test_parser.py (removed), tests/fixtures/sample.py, tests/fixtures/sample.go, tests/fixtures/sample.js, tests/fixtures/broken.py

**Goal**: given a language and file text, return definition-level chunks, or windows when the file cannot be parsed.

**Independent Test**: `uv run pytest tests/test_chunker.py`. No database is needed.

### Tests

**Wave 1:**

- [x] **T008** [US2] [US3] Fixtures:
  - Extend `sample.py` with a class that has decorated and plain methods, plus a nested class and a nested function.
  - Extend `sample.go` with an interface, a grouped `type ( … )` with a struct and an interface, and a generic pointer receiver method.
  - Add `sample.js` with a function, a generator, an exported class with methods, an arrow `const` and an `export default function`.
  - Add `broken.py` with a syntax error.

  Each fixture's docstring says its line numbers are asserted in `test_chunker.py`. · tests/fixtures/sample.py, tests/fixtures/sample.go, tests/fixtures/sample.js, tests/fixtures/broken.py

**⟶ Wait for T008, then:**

- [x] **T009** [US2] [US3] Replace `test_parser.py` with `test_chunker.py`:
  - For each fixture, the exact set of `(name, kind, start, end)`, covering methods named `Type.method`, decorators inside the range, nested functions left out, grouped Go types, struct mapped to `type` and interface to `interface` (SC-003).
  - Each chunk's `source` equals its lines from the fixture.
  - `broken.py` and an unknown language return `None`.
  - `windows()`: 130 lines give 1-60, 51-110 and 101-130 (SC-004), 60 lines give one window, and 0 lines give none, each named `<file>:<s>-<e>` with kind `chunk`.
  - `detect_language` covers `.py`, `.go`, `.js`, `.mjs`, `.md`, `.rst` and an unknown extension.

  Delete `test_parser.py`. · tests/test_chunker.py, tests/test_parser.py

### Implementation

**⟶ Wait for T009, then:**

- [x] **T010** [US2] [US3] Chunker module per research.md:
  - `Chunk(name, kind, start_line, end_line, source)`.
  - `detect_language(path) -> str`.
  - `chunk(language, text) -> list[Chunk] | None`: tree-sitter for Python, Go and JavaScript. It returns `None` when there is no grammar or `root_node.has_error`.
  - `windows(name, text, size=60, step=50) -> list[Chunk]`.
  - Grammars load once per language.

  (FR-004 to FR-008) · src/golestan_code_mcp/chunker.py

**⟶ Wait for T010, then:**

- [x] **T011** [US2] [US3] Run `uv run pytest tests/test_chunker.py` until green · src/golestan_code_mcp/chunker.py

**Checkpoint**: chunking follows the code, and anything unparseable becomes overlapping windows.

## Phase 4: Ingest pipeline (US1, US4, Priority: P1)

Files: src/golestan_code_mcp/ingest.py, tests/test_ingest.py

**Goal**: `ingest(conn, name) -> Summary` indexes a registered git repository in one transaction.

**Independent Test**: `uv run pytest tests/test_ingest.py` against temporary git repositories.

### Tests

**Wave 1:**

- [x] **T012** [US1] [US4] Ingest tests:
  - **Discovery half (no database):** a temporary git repo built with a local `git()` helper holds a gitignored file, a `vendor/` file, a PNG, a file over a lowered `CCCTX_MAX_FILE_BYTES`, a symlink (skipped where the OS can't create one), `broken.py`, a 130-line `notes.txt`, an empty file and one `.py`, `.go` and `.js` file. `discover()` must assign each file the right reason, never list `.git`, and its counts must add up (SC-007, SC-008).
  - **Database half (skip when down):**
    - The summary's `scanned`, `skipped` per reason, `fallback` (no grammar or parse error), `symbols` and `commit` values are right.
    - The stored rows match the summary, and every `commit_sha` equals `git rev-parse HEAD` (SC-006).
    - Ingesting twice gives the same counts (SC-005).
    - An exception injected mid-insert leaves the previous index intact (FR-012).
    - A dirty tree sets `dirty`.
    - A non-git directory and a repository with no commits are refused with nothing changed (FR-018).
    - A concurrent ingest holding the row lock is reported as "another ingest is running".

  Rows created use `t-` names and are cleaned up. · tests/test_ingest.py

### Implementation

**⟶ Wait for T012, then:**

- [x] **T013** [US1] [US4] Ingest module:
  - `git(repo, *args)`: read-only flags, no shell.
  - `discover(root, env) -> (to_index, skipped: Counter)`.
  - `ingest(conn, name, env) -> Summary`:
    1. `get_repo`, then check for a git repository and a commit.
    2. Run `discover`, chunk each file and fall back to windows where needed.
    3. In one transaction: lock nowait, delete the old files, insert files with `returning id`, `executemany` the symbols with a CLOB `source`, then commit (rollback on any error).
    4. Return the summary.
  - `IngestError` for refusals.
  - One JSON record on the `golestan_code_mcp.ingest` logger.

  (FR-001, FR-002, FR-009 to FR-014, FR-017, FR-018) · src/golestan_code_mcp/ingest.py

**⟶ Wait for T013 and Phase 3, then:**

- [x] **T014** [US1] [US4] Run `uv run pytest tests/test_ingest.py` until green · src/golestan_code_mcp/ingest.py

**Checkpoint**: a repository can be ingested, re-ingested and traced to its commit.

## Phase 5: Commands (US1, US2, US3, Priority: P1)

Files: src/golestan_code_mcp/cli.py, tests/test_cli.py

### Tests

**Wave 1:**

- [x] **T015** [US1] [US2] [US3] CLI tests per contracts/cli.md:
  - **Summary format:** `format_summary(summary)` produces the `Scanned`/`Skipped`/`Indexed` lines, right-aligned with thousands separators. Only non-zero reasons appear, in order. The `Fallback` line appears only when at least one file fell back. The time has one decimal.
  - **Ingest command:** on a temporary repo it exits 0 and prints the three lines. An unknown name or a non-git directory exits 1. `DB_PORT=1` exits 2 in under 5 s with no password in the output.
  - **`symbols --repo <name> --limit 3`:** the header is `NAME KIND LANGUAGE PATH LINES`, it prints 3 rows, parsed symbols come before chunks, and `--kind chunk` filters to chunks.
  - **`stats --by-language`:** the header is `REPO LANGUAGE FILES SYMBOLS CHUNKS`, with rows per repository and language.
  - The existing `repo list` tests still pass with the generalised `format_table`.

  · tests/test_cli.py

### Implementation

**⟶ Wait for T015, then:**

- [x] **T016** [US1] [US2] [US3] Commands:
  - Generalise `format_table(header, rows, numeric)`.
  - Add subcommands `ingest <name>`, `symbols --repo --limit (default 20) --kind` and `stats --by-language [--repo]`.
  - `format_summary` output goes to stdout and the dirty-tree warning to stderr.
  - `IngestError` exits 1.
  - Configure the `golestan_code_mcp.ingest` logger to stderr.

  (FR-013, FR-015, FR-016) · src/golestan_code_mcp/cli.py

**⟶ Wait for T016, then:**

- [x] **T017** [US1] [US2] [US3] Run `uv run pytest tests/test_cli.py` until green · src/golestan_code_mcp/cli.py

**Checkpoint**: every command in the request works.

## Phase 6: Polish

- [x] **T018** Document `ccctx ingest`, `ccctx symbols`, `ccctx stats --by-language`, the skip rules, the two settings and the fallback windows. Update the layout section · README.md

**⟶ Wait for T018, then:**

- [x] **T019** Run `uv run pytest` with the database up and again with it stopped. Both must be green, with DB tests skipped in the second.

**⟶ Wait for T019, then:**

- [x] **T020** Walk through the request:
  1. `ccctx ingest flask`, timed (SC-001).
  2. `ccctx symbols --repo flask --limit 5`. Check one row against the file on disk.
  3. `ccctx ingest gin`, timed.
  4. `ccctx stats --by-language`: Python for flask and Go for gin, each with fallback chunks.
  5. Re-ingest flask and compare counts (SC-005).
  6. Check 10 random parsed symbols against their files (SC-002).
  7. Run `ccctx repo list` and compare its counts with the summaries.
  8. Sweep tracked files and command output for secrets.

## Dependencies & Execution Order

- Setup → Foundational → Chunker → Ingest → Commands → Polish. Ingest's tests can be written while the chunker is being built, but T014 needs T010. Commands need Ingest.
- **Setup**: Wave 1 (T001, T002) in parallel.
- **Foundational**: Wave 1 (T003, T004), then Wave 2 (T005, T006), then T007.
- **Chunker**: T008, then T009, then T010, then T011.
- **Ingest**: T012, then T013, then T014 (also needs T010).
- **Commands**: T015, then T016, then T017.
- **Polish**: T018, then T019, then T020.
