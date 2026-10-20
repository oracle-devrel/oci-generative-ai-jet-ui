# Tasks: Semantic Code Search

**Input**: [semantic-search.spec.md](./semantic-search.spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

Tests come first in each phase and must fail before the code they cover exists (constitution VI). Database tests skip with a reason when the database is unreachable. Tests that need embeddings also skip with a reason when the model is not loaded.

`semantic.py` holds the model name, the model check, the model load and the search query, and every story uses it. So it is foundational. The command line serves US1 (`model load`) and US3 (`search`) from one file, so those two share a phase.

## Phase 1: Setup

**Wave 1 — independent (different files):**

- [x] **T001** [P] [US1] Ignore the model cache directory `.cache/` · .gitignore
- [x] **T002** [P] [US1] Add `model_url(env)` (`CCCTX_MODEL_URL`, default the OML-ai-models `all_MiniLM_L12_v2.onnx` URL from research.md) and `model_cache(env)` (`CCCTX_MODEL_CACHE`, default `<project>/.cache/models`, relative paths resolved against the project root), with tests for the defaults and overrides (FR-002) · src/golestan_code_mcp/config.py, tests/test_config.py
- [x] **T003** [P] [US2] Startup script, run as sysdba in the CDB root:
  - When the spfile `vector_memory_size` is 0, set `256M` with `scope=spfile`, run `alter pluggable database freepdb1 save state`, then `shutdown immediate` and `startup`.
  - Otherwise do nothing.
  - Bash with `set -euo pipefail` and LF line endings, in the style of `01_app_user.sh`.

  Also add one comment line in `compose.yaml` about the one-time restart (FR-006) · db/startup/02_vector_memory.sh, compose.yaml

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T004** [US2] Restart the container. Check that the log runs to `DATABASE IS READY TO USE!`, that `vector_memory_size` reads 256M afterwards, that FREEPDB1 is open, and that `uv run golestan-check-db` passes. Restart once more and check the script now does nothing · db/startup/02_vector_memory.sh

## Phase 2: Foundational (US1, US2, US3): schema and the semantic core

Files: src/golestan_code_mcp/schema.py, src/golestan_code_mcp/semantic.py, tests/test_schema.py, tests/test_semantic.py

### Tests

**Wave 1 — independent (different files):**

- [x] **T005** [P] [US2] Schema tests:
  - Migration 3 is recorded as version 3.
  - `ccctx_symbols.embedding` exists, is nullable and has type `VECTOR(384, FLOAT32)`.
  - `ccctx_embedding_model` exists.
  - `migrate` run 3 times is still a no-op.

  · tests/test_schema.py
- [x] **T006** [P] [US1] [US3] Semantic tests:
  - **Without the database:** an empty or blank question raises `ValueError`.
  - **Model checks** (skip unless the model is loaded):
    - `require_model` passes.
    - `ccctx_embedding_model` has `('ALL_MINILM_L12_V2', 384)`.
    - The index `ccctx_symbols_embedding_ix` exists.
    - `load_model` run again reports "already present" and changes nothing.
    - The request's two SQL checks return the model and 384 elements (SC-001).
  - **Search** (skip unless the model is loaded), against a throwaway `t-` repository whose symbols are inserted with `VECTOR_EMBEDDING`, for example `route_request` and `bake_bread`:
    - A routing question ranks `route_request` first.
    - At most 10 results come back, in descending similarity, each with similarity of at least 0.3 (SC-005).
    - An unrelated question returns fewer results.
    - `repo=` filters to that repository.
    - An unknown repository raises `RegistryError`.
  - **Missing model:** `require_model` raises `ModelError` naming `ccctx model load` when the model record is missing. Simulate this with a monkeypatched model name.

  · tests/test_semantic.py

### Implementation

**⟶ Wait for Wave 1 to finish, then:**

**Wave 2 — independent (different files):**

- [x] **T007** [P] [US2] Migration 3 `symbol embedding`: add the nullable column `embedding vector(384, float32)` and create `ccctx_embedding_model` (FR-003, FR-007) · src/golestan_code_mcp/schema.py
- [x] **T008** [P] [US1] [US3] Semantic module:
  - Constants: `MODEL`, `DIMENSION=384`, `LIMIT=10`, `FLOOR=0.3`, `INDEX`.
  - `ModelError(ValueError)` and `Result(rank, similarity, repo, kind, name, path, start_line, end_line)`.
  - `require_model(conn)`: the model is in `user_mining_models`, the record has dimension 384, and the index exists.
  - `load_model(conn, env) -> str`:
    1. Download to the cache, unless it is already there at the expected size.
    2. BLOB-load with `DBMS_VECTOR.LOAD_ONNX_MODEL` and the research.md metadata.
    3. Check the dimension.
    4. Record the model.
    5. Create the HNSW index with `ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95`.

    Each step is skipped when already done, and it returns the status line.
  - `search(conn, question, repo=None) -> list[Result]` using the research.md query.

  (FR-001, FR-002, FR-006, FR-007, FR-009, FR-010, FR-013) · src/golestan_code_mcp/semantic.py

**⟶ Wait for Wave 2 to finish, then:**

- [x] **T009** [US1] Load the model into the development database with `semantic.load_model`, then run `uv run pytest tests/test_schema.py tests/test_semantic.py` until green · src/golestan_code_mcp/semantic.py

**Checkpoint**: the database embeds text on its own, and the search query works.

## Phase 3: US2 (Priority: P1): every ingested symbol gets an embedding

Files: src/golestan_code_mcp/ingest.py, tests/test_ingest.py

### Tests

**Wave 1:**

- [x] **T010** [US2] Ingest tests:
  - The `conn` fixture also skips when the model is not loaded.
  - After an ingest, every stored symbol has a non-null 384-element embedding (SC-002).
  - A monkeypatched `semantic.require_model` that raises `ModelError` makes ingest fail before anything changes: the previous rows are untouched and no chunking runs (FR-008).
  - The existing replace and rollback tests still pass.

  · tests/test_ingest.py

### Implementation

**⟶ Wait for T010, then:**

- [x] **T011** [US2] Call `semantic.require_model(conn)` first in `ingest()`. Switch `_insert_symbols(cur, rows)` to named binds, with `embedding = VECTOR_EMBEDDING(<MODEL> USING :kind || ' ' || :name || ' in ' || :path || chr(10) || :source AS data)`, `source` bound once as a CLOB, and `path` added to each row (FR-004, FR-005, FR-008) · src/golestan_code_mcp/ingest.py

**⟶ Wait for T011, then:**

- [x] **T012** [US2] Run `uv run pytest tests/test_ingest.py` until green · src/golestan_code_mcp/ingest.py

**Checkpoint**: ingest stores an embedding for every symbol and refuses without the model.

## Phase 4: US1 + US3 (Priority: P1): `ccctx model load` and `ccctx search`

Files: src/golestan_code_mcp/cli.py, tests/test_cli.py

### Tests

**Wave 1:**

- [x] **T013** [US1] [US3] CLI tests per contracts/cli.md:
  - **`model load`:** prints `model ALL_MINILM_L12_V2 already present (384 dimensions)` and exits 0 when loaded. It is not blocked by the automatic migrate.
  - **Search output:** for a throwaway repository, the header is `RANK SIMILARITY REPO KIND NAME PATH LINES` and similarity has three decimals.
  - **Search refusals:**
    - An empty question exits 1 before connecting (`DB_PORT=1`).
    - Nothing above the floor prints `no symbols similar enough (similarity >= 0.30)` and exits 0.
    - An unknown `--repo` exits 1.
    - A monkeypatched missing model exits 1 with the `ccctx model load` hint.
    - `DB_PORT=1` exits 2 in under 5 s with no password in the output.

  · tests/test_cli.py

### Implementation

**⟶ Wait for T013, then:**

- [x] **T014** [US1] [US3] Add the `model load` group and the `search <question> [--repo]` subcommand.
  - The empty-question check runs before connecting.
  - `ModelError` exits 1.
  - Format search results with `format_table`, with `RANK` and `SIMILARITY` right-aligned.

  (FR-001, FR-009 to FR-014) · src/golestan_code_mcp/cli.py

**⟶ Wait for T014, then:**

- [x] **T015** [US1] [US3] Run `uv run pytest tests/test_cli.py` until green · src/golestan_code_mcp/cli.py

**Checkpoint**: the model loads from one command, and plain-English search works from the CLI.

## Phase 5: US4 (Priority: P2): search over MCP

Files: src/golestan_code_mcp/server.py, tests/test_server.py

### Tests

**Wave 1:**

- [x] **T016** [US4] Server tests per contracts/search-tool.md:
  - The tool list is `["health", "list_repositories", "search"]`.
  - `search` has a required `question` and an optional `repo`. The other two tools still take no input.
  - `call()` accepts arguments.
  - When the model is loaded, the tool returns `status: "ok"` and results identical to `semantic.search`, field for field (SC-008).
  - `DB_PORT=1`, an empty question and an unknown repository each return `status: "unavailable"` with a reason, `results: []`, no error and no password.

  · tests/test_server.py

### Implementation

**⟶ Wait for T016, then:**

- [x] **T017** [US4] Add the pydantic models `SearchHit` and `SearchResults`, and a `search(question, repo=None)` tool that calls `semantic.search`. Map `ConfigError`, `ValueError` (which includes `ModelError` and `RegistryError`) and `oracledb.Error` to `unavailable` (FR-015) · src/golestan_code_mcp/server.py

**⟶ Wait for T017, then:**

- [x] **T018** [US4] Run `uv run pytest tests/test_server.py` until green · src/golestan_code_mcp/server.py

**Checkpoint**: agents can search with the same results as the CLI.

## Phase 6: Polish

- [x] **T019** Document `ccctx model load` (one-time download and the cache), the one-time database restart for the vector memory pool, `ccctx search` and its floor, the MCP `search` tool, `CCCTX_MODEL_URL` and `CCCTX_MODEL_CACHE`, and the layout · README.md

**⟶ Wait for T019, then:**

- [x] **T020** Run `uv run pytest` with the database up and again with it stopped. Both must be green, with DB tests skipped in the second.

**⟶ Wait for T020, then:**

- [x] **T021** Walk through the request:
  1. Run the two SQL checks (SC-001).
  2. Re-ingest flask and gin, timed (SC-007), and count null embeddings (SC-002).
  3. Search the routing question and confirm flask and gin routing or dispatch code in the top 10 (SC-003), timed (SC-006).
  4. Search the sourdough question and confirm 3 or fewer results (SC-004).
  5. Compare the MCP tool with the CLI for the routing question (SC-008).
  6. Sweep for secrets.

## Dependencies & Execution Order

- Setup → Foundational → {Ingest, Commands, MCP} → Polish. The three story phases own disjoint files and depend only on Foundational, so they can run in any order or in parallel.
- **Setup**: Wave 1 (T001, T002, T003) in parallel, then T004.
- **Foundational**: Wave 1 (T005, T006), then Wave 2 (T007, T008), then T009.
- **Ingest**: T010, then T011, then T012.
- **Commands**: T013, then T014, then T015.
- **MCP**: T016, then T017, then T018.
- **Polish**: T019, then T020, then T021.
