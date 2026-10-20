# Tasks: Incremental Re-indexing

**Inputs**: [incremental-ingest.spec.md](./incremental-ingest.spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

Every user story is served by the same three modules (`schema.py`, `ingest.py`, `cli.py`), so all code and its tests live in Foundational. The story phases are the live acceptance runs against the real flask checkout. They own no files and share the flask working tree, so they run one after another.

Setup is omitted: the project, the database and both sample repositories already exist.

## Phase 2: Foundational

Files: `tests/test_schema.py`, `tests/test_ingest.py`, `tests/test_cli.py`, `src/golestan_code_mcp/schema.py`, `src/golestan_code_mcp/ingest.py`, `src/golestan_code_mcp/cli.py`

### Tests (write first, confirm they fail)

**Wave 1 — independent (different files):**

- [x] **T001** [P] Migration 5 tests: version `(5, "repo indexed revision")` recorded; `INDEXED_COMMIT`, `INDEXED_DIRTY`, `INDEXED_AT` nullable; `ccctx_repos_indexed_ck` accepts NULL, 40 and 64 hex, rejects other values · tests/test_schema.py
- [x] **T002** [P] Ingest tests:
  - US1: a second run is `current`, writes nothing and logs `mode: current`. Uncommitted tracked edits at the same HEAD are indexed. The revision is recorded only on commit.
  - US2: add, edit, rename, untracked file, and changed-then-changed-back. Each incremental result equals a `full=True` rebuild, excluding `commit_sha`. Unchanged symbol rows keep their ids. A reverted edit after a dirty ingest is picked up. The counts are correct.
  - US3: delete, and a file that became binary or too large, leave zero rows for the path. A text search no longer returns it.
  - US4: `full=True` on an up-to-date repository re-processes everything, with the same counts as the first ingest.
  - Fallbacks: a NULL revision with files stored gives a full run and a note. A missing commit gives a full run and a note.
  - A failed run keeps the index and `indexed_commit`.
  - `git diff` and `rev-parse --verify` are added to the read-only check.

  · tests/test_ingest.py
- [x] **T003** [P] CLI tests, cases built from `Summary` objects as the existing helper does:
  - `ingest --full` is accepted.
  - The incremental summary prints `Changed`, `Unchanged`, `Skipped`, `Indexed`, then `Fallback`, right-aligned with thousands separators.
  - The up-to-date line is exact and exits 0.
  - Fallback notes go to stderr.

  · tests/test_cli.py

### Implementation

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T004** Migration 5 `repo indexed revision`: add the three columns and `ccctx_repos_indexed_ck`, re-runnable through the tolerated codes · src/golestan_code_mcp/schema.py

**⟶ Wait for T004, then:**

- [x] **T005** Incremental ingest:
  - `Summary` gains defaulted `mode`, `added`, `changed`, `removed`, `unchanged` and `note`.
  - `ingest(conn, name, env=None, full=False)`. `require_model` still runs first.
  - Lock the repository row first, then read `indexed_commit`, `indexed_dirty` and the stored path→hash map.
  - Pick the mode, including the `rev-parse --verify --quiet` check and the notes.
  - Candidates from `diff --name-only -z --no-renames`, untracked files, and vanished stored paths, or every listed file after a dirty ingest. Run them through the existing skip rules, then classify by hash.
  - Delete changed and removed file rows with executemany, insert added and changed ones, update the revision columns, and commit. A `current` run rolls back.
  - The log record gains `mode` and the four counts.

  · src/golestan_code_mcp/ingest.py

**⟶ Wait for T005, then:**

- [x] **T006** CLI changes:
  - `--full` flag.
  - `format_summary` branches on `mode`: the full summary is unchanged, the incremental summary prints `Changed` and `Unchanged` lines, and `current` prints the up-to-date line.
  - `Summary.note` goes to stderr.

  · src/golestan_code_mcp/cli.py

**⟶ Wait for T006, then:**

- [x] **T007** Run `tests/test_schema.py`, `tests/test_ingest.py` and `tests/test_cli.py` against the database. Fix until green.

**Checkpoint**: every behavior is covered by passing integration tests on throwaway repositories.

## Phase 3: User Story 1 - Nothing changed, nothing done (P1)

Files: none (live verification on `../ccctx-repos/flask`)

- [x] **T008** [US1] Note flask's files and symbols from `ccctx repo list` as the baseline. Run `ccctx ingest flask` twice. The first run is a full run with the "no recorded revision" note. The second prints `flask is already up to date at …` in under 3 s, and `repo list` is unchanged (SC-001).

**Checkpoint**: re-ingest of an untouched repository is a no-op.

## Phase 4: User Story 2 - Only changed files are re-indexed (P1)

Files: none

- [x] **T009** [US2] Record flask's current branch and HEAD. `git checkout HEAD~20`, then `ccctx ingest flask` and note the counts and time. Run `ccctx ingest flask --full` on the same tree and confirm the file and symbol totals agree (SC-002, SC-005). Return to the recorded branch and re-ingest.

**Checkpoint**: a move of 20 commits re-processes only the changed files.

## Phase 5: User Story 3 - Deleted code leaves the index (P1)

Files: none

- [x] **T010** [US3]
  1. `rm src/flask/json/tag.py`, then `ccctx ingest flask` and `ccctx search "json tag serialisation" --repo flask`.
  2. Confirm no result has that path, and that zero `ccctx_files` and `ccctx_symbols` rows have it (SC-003).
  3. `git checkout -- src/flask/json/tag.py`, re-ingest, and confirm its symbols are back.

**Checkpoint**: deletions leave no orphans.

## Phase 6: User Story 4 - Full rebuild on demand (P2)

Files: none

- [x] **T011** [US4] On the restored, up-to-date flask run `ccctx ingest flask --full`. It re-processes every file, and its file and symbol counts equal the T008 baseline (SC-004).

**Checkpoint**: the escape hatch rebuilds to identical counts.

## Phase 7: Polish

Files: `README.md`, `specs/006-incremental-ingest/contracts/cli.md`, `specs/006-incremental-ingest/contracts/schema.md`

**Wave 1 — independent (different files):**

- [x] **T012** [P] "Ingesting a codebase" section: incremental runs, the up-to-date message, deletions, `--full` and when to use it (after changing chunking rules, `CCCTX_VENDOR_DIRS` or `CCCTX_MAX_FILE_BYTES`) · README.md
- [x] **T013** [P] Reconcile both contracts with the shipped output and log keys · specs/006-incremental-ingest/contracts/cli.md, specs/006-incremental-ingest/contracts/schema.md

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T014** Run the full test suite with the database up and down, run ruff, and do a secrets sweep. Validate against SC-001 to SC-006.

## Dependencies & Execution Order

- Foundational, then US1, then US2, then US3, then US4, then Polish. The story phases share the flask working tree, so they run one at a time.
- Foundational: T001, T002 and T003 have no dependencies. T004 waits for them. T005 waits for T004, T006 for T005, and T007 for T006.
- Polish: T012 and T013 have no dependencies. T014 waits for both.
