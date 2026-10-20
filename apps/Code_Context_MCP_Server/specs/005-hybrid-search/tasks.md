# Tasks: Hybrid Code Search

**Input**: [hybrid-search.spec.md](./hybrid-search.spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

Tests come first in each phase and must fail before the code they cover exists (constitution VI). Database tests skip with a reason when the database is unreachable. Search tests also skip when the hybrid index is not built.

All five stories meet in `semantic.search`: the definition boost (US1), fusion (US2), modes (US3) and repository scoping (US4) are one function, which the MCP tool (US5) reuses. So the schema and the search core are foundational. The command line serves US1 to US4 from one file, so those share a phase.

## Phase 1: Setup

- [x] **T001** [US2] Add `search_candidates(env)` (`CCCTX_SEARCH_CANDIDATES`, positive integer, default 100), plus `text_weight(env)` and `vector_weight(env)` (`CCCTX_TEXT_WEIGHT`, `CCCTX_VECTOR_WEIGHT`, positive numbers, default 1.0). Test the defaults, overrides and a bad value raising `ConfigError` (FR-008) · src/golestan_code_mcp/config.py, tests/test_config.py

## Phase 2: Foundational (US1 to US4): schema and the hybrid search core

Files: src/golestan_code_mcp/schema.py, src/golestan_code_mcp/semantic.py, tests/test_schema.py, tests/test_semantic.py

### Tests

**Wave 1 — independent (different files):**

- [x] **T002** [P] [US2] Schema tests:
  - Migration 4 `hybrid search text` is recorded.
  - `ccctx_symbols.search_text` exists as a CLOB.
  - The `embedding` column and `ccctx_symbols_embedding_ix` are gone.
  - A symbol row inserted before migration 4 has its `search_text` backfilled as `kind name in path\nsource` (FR-013).
  - `migrate` run 3 times is a no-op.

  · tests/test_schema.py
- [x] **T003** [P] [US1] [US2] [US3] [US4] Semantic tests, against a throwaway `t-` repository pair (`t-a`, `t-b`) inserted with `search_text`, skipping unless the hybrid index exists:
  - **Setup checks:**
    - `require_model` checks the hybrid index.
    - `load_model` run again reports "already present".
    - A row committed in the test is found by text search immediately (SYNC ON COMMIT, FR-014).
  - **Definitions:**
    - In hybrid mode, `url_for` puts the `url_for` definition (function) and `App.url_for` (method) above `redirect_home`, which only calls it.
    - The qualified name `App.url_for` ranks that method first.
    - An identifier defined nowhere gets no boost.
  - **Modes:**
    - Text mode returns only rows containing every word.
    - Vector mode drops below the floor and ranks by meaning.
    - Each result carries `score`, `keyword_rank` and `semantic_rank`, with `None` where absent.
  - **Repositories:**
    - `repos=["t-b"]` returns only `t-b` rows.
    - `repos=["t-a", "t-b", "t-a"]` searches both, once each.
    - An unknown name raises `RegistryError` before searching.
  - **Literal input:** `a_b`, `x-y`, `(foo)`, `c&d`, `50%` and `"quoted"` never raise (FR-011).
  - **Refusals and cap:** an unknown mode raises `ValueError`, an empty question raises `ValueError`, and there are at most 10 results.

  · tests/test_semantic.py

### Implementation

**⟶ Wait for Wave 1 to finish, then:**

**Wave 2 — independent (different files):**

- [x] **T004** [P] [US2] Migration 4 `hybrid search text`, per contracts/schema.md:
  1. Drop `ccctx_symbols_embedding_ix`, tolerating ORA-01418.
  2. Drop the column `embedding`, tolerating ORA-00904.
  3. Add `search_text clob`.
  4. Backfill rows where `search_text is null` from the files join.

  Add the tolerated codes to `ALREADY_EXISTS` (FR-001, FR-013) · src/golestan_code_mcp/schema.py
- [x] **T005** [P] [US1] [US2] [US3] [US4] Semantic module:
  - **Constants and types:** `INDEX = CCCTX_SYMBOLS_HYBRID_IX` and `MODES`. `Result` is `rank, score, similarity, keyword_rank, semantic_rank, repo, kind, name, path, start_line, end_line`.
  - **Setup:** `_state` and `require_model` look for the hybrid index. `load_model` creates the hybrid index with `SYNC (ON COMMIT)`.
  - **`search(conn, question, repos=None, mode="hybrid", env=None)`:**
    1. Validate the question, the mode and the repositories (each through `registry.repo_id`) before searching.
    2. Build the request: RRF and UNION, brace-escaped words joined with AND, `score_weight`s and `topN` from config.
    3. Parse the LOB, map rowids to symbols in the chosen repositories, de-duplicate, and apply the vector floor in vector mode.
    4. Put definition matches first in hybrid and text modes.
    5. Cap at 10.

  (FR-001 to FR-012) · src/golestan_code_mcp/semantic.py

**⟶ Wait for Wave 2 to finish, then:**

- [x] **T006** [US2] On the development database:
  1. Run `migrate` (migration 4 backfills about 3,000 symbols).
  2. Run `load_model` to build the hybrid index, timed.
  3. Run `uv run pytest tests/test_schema.py tests/test_semantic.py` until green.

  · src/golestan_code_mcp/semantic.py

**Checkpoint**: one hybrid index serves all three modes, and definitions come first.

## Phase 3: US2 (Priority: P1): ingest keeps the hybrid index current

Files: src/golestan_code_mcp/ingest.py, tests/test_ingest.py

### Tests

**Wave 1:**

- [x] **T007** [US2] Ingest tests:
  - The fixture skips unless the hybrid index exists.
  - After an ingest, every symbol has `search_text` equal to `kind name in path\nsource`.
  - A symbol from the fresh ingest is found by `semantic.search(..., mode="text")` straight after `ingest()` returns (FR-014).
  - Replace the step 4 embedding assertions.
  - The missing-model refusal and the rollback tests still pass.

  · tests/test_ingest.py

### Implementation

**⟶ Wait for T007, then:**

- [x] **T008** [US2] `_insert_symbols` stores `search_text` and no longer calls `VECTOR_EMBEDDING`. Both CLOB binds, `search_text` then `source`, come last. Remove `EMBED_CHARS` (FR-014) · src/golestan_code_mcp/ingest.py

**⟶ Wait for T008, then:**

- [x] **T009** [US2] Run `uv run pytest tests/test_ingest.py` until green · src/golestan_code_mcp/ingest.py

**Checkpoint**: a finished ingest is fully searchable through the hybrid index.

## Phase 4: US1 to US4 (Priority: P1/P2): `ccctx search --mode --repo`

Files: src/golestan_code_mcp/cli.py, tests/test_cli.py

### Tests

**Wave 1:**

- [x] **T010** [US1] [US3] [US4] CLI tests per contracts/cli.md:
  - The header is `RANK SCORE KEYWORD SEMANTIC REPO KIND NAME PATH LINES`, with `-` for a missing rank.
  - `--mode text`, `--mode vector` and the hybrid default pass through.
  - `--mode bogus` exits 1 before connecting and lists the valid modes.
  - `--repo a --repo b` and `--repo a,b` both narrow, and an unknown repository exits 1.
  - The vector floor message and an empty question behave as before.
  - Update the step 4 `SIMILARITY` assertions.

  · tests/test_cli.py

### Implementation

**⟶ Wait for T010, then:**

- [x] **T011** [US1] [US3] [US4] `search` gets `--mode` (validated before connecting, exit 1) and `--repo` (`action="append"`, split on commas, de-duplicated). `_search` passes `repos`, `mode` and `environment()` and formats the new columns (FR-004, FR-007, FR-009, FR-010) · src/golestan_code_mcp/cli.py

**⟶ Wait for T011, then:**

- [x] **T012** [US1] [US3] [US4] Run `uv run pytest tests/test_cli.py` until green · src/golestan_code_mcp/cli.py

**Checkpoint**: the request's commands work from the CLI.

## Phase 5: US5 (Priority: P2): MCP search with mode and repositories

Files: src/golestan_code_mcp/server.py, tests/test_server.py

### Tests

**Wave 1:**

- [x] **T013** [US5] Server tests per contracts/search-tool.md:
  - The `search` input schema has `question` (required) and optional `repo`, `repos` and `mode`.
  - The results match `semantic.search` field for field, for `url_for` in hybrid mode and with `repos` (SC-008).
  - A single `repo` still works.
  - An unknown mode, an unknown repository, an empty question and an unreachable database each return `status: "unavailable"` with a reason and no error.

  · tests/test_server.py

### Implementation

**⟶ Wait for T013, then:**

- [x] **T014** [US5] `search(question, repo=None, repos=None, mode="hybrid")` merges `repo` into `repos`. `SearchHit` adds `score`, `keyword_rank` and `semantic_rank` (nullable) and keeps `similarity`. Update the tool description (FR-015) · src/golestan_code_mcp/server.py

**⟶ Wait for T014, then:**

- [x] **T015** [US5] Run `uv run pytest tests/test_server.py` until green · src/golestan_code_mcp/server.py

**Checkpoint**: agents get the same hybrid search.

## Phase 6: Polish

- [x] **T016** Document the modes, `--repo`, the definition rule, the result columns, the three settings with their defaults, and the one-time `ccctx model load` re-run that builds the hybrid index · README.md

**⟶ Wait for T016, then:**

- [x] **T017** Run `uv run pytest` with the database up and again with it stopped. Both must be green.

**⟶ Wait for T017, then:**

- [x] **T018** Walk through the request:
  1. `ccctx search "url_for"`: a definition at rank 1, and both definitions above call sites (SC-001).
  2. The same query with `--mode vector`, `--mode text` and `--mode hybrid` (SC-006).
  3. `ccctx search "middleware chain" --repo gin`: all results from gin (SC-004).
  4. The routing question (SC-003).
  5. The sourdough question: 3 or fewer results (SC-005).
  6. Search 10 defined identifiers across flask and gin, with a definition at rank 1 for at least 9 (SC-002).
  7. Time the searches (SC-007).
  8. Compare MCP over stdio with the CLI (SC-008).
  9. Sweep for secrets.

## Dependencies & Execution Order

- Setup → Foundational → {Ingest, CLI, MCP} → Polish. The three story phases own disjoint files and depend only on Foundational.
- **Setup**: T001.
- **Foundational**: Wave 1 (T002, T003), then Wave 2 (T004, T005), then T006.
- **Ingest**: T007, then T008, then T009.
- **CLI**: T010, then T011, then T012.
- **MCP**: T013, then T014, then T015.
- **Polish**: T016, then T017, then T018.

## Phase 7: Convergence

- [x] **T019** CRITICAL: Add a versioned retrieval evaluation set as a constant in `tests/test_eval.py` (query, mode, repos → expected repo, path and symbol name) covering `url_for` (SC-001), 10 identifiers defined in flask or gin (SC-002), the routing question (SC-003) and the sourdough question (SC-005). Add a DB-backed test that skips unless flask and gin are ingested, asserts each threshold and reports top-1 and top-5 hit rates · tests/test_eval.py per Constitution VI, plan: Constitution Check VI (missing)
- [x] **T020** CRITICAL: Log each MCP tool call (`health`, `list_repositories`, `search`) as one structured JSON line on stderr with tool, latency, result count and status, never the question or source text. Test it in tests/test_server.py · src/golestan_code_mcp/server.py, tests/test_server.py per Constitution: Technology & Data Constraints, structured logging (missing)
