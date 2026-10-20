# Tasks: Module Wiki

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data model**: [data-model.md](./data-model.md) | **Contracts**: [cli.md](./contracts/cli.md), [tools.md](./contracts/tools.md)

US1, US2 and US3 share Phase 3, because all three live in `wiki.py`.
- That phase also owns the chunker and ingestion. Pages need the docs those store.
- The chunker's `parse` gains a 4th return value, which `ingest.py` unpacks, so splitting them would break ingestion between phases.

US4 is split by surface:
- search in Phase 4;
- the CLI in Phase 5;
- the MCP server in Phase 6.

Each surface file then has one owner.

## Phase 1: Setup

- [x] **T001** Version `1.1.0` in `pyproject.toml` and `__version__`, then `uv lock`. The tool contract only gains things (constitution III) · pyproject.toml, src/golestan_code_mcp/__init__.py, uv.lock

## Phase 2: Foundational

The tables and the import resolver every story reads. No story work starts until this phase is done.

**Wave 1 — independent (different files):**

- [x] **T002** [P] Migration 7 tests, written to fail first, per data-model.md:
  - **The columns:** `ccctx_files.doc`, `ccctx_symbols.doc`, `ccctx_repos.wiki_at`, and the `ccctx_wiki_pages` and `ccctx_wiki_citations` tables, with their columns.
  - **Constraints refuse bad rows:** `state` outside fresh and stale, `symbols` below 10, an unknown `role`, a `key` citation with a `file_id`, and a duplicate `(repo_id, directory)` or `(repo_id, name)`.
  - **Delete behavior:**
    - deleting a symbol or a file sets the citations that point at it to null and keeps the citation rows;
    - deleting a page removes its citations;
    - deleting a repository removes its pages.
  - **Re-running** the migrations is a no-op.
  - File: tests/test_schema.py
- [x] **T003** [P] Migration 7, "module wiki", per data-model.md: the doc columns, `wiki_at`, both tables with their named constraints, and indexes on `page_id`, `symbol_id` and `file_id`. The page index is not created here (research R8) · src/golestan_code_mcp/schema.py
- [x] **T004** [P] `graph.external_imports` tests, written to fail first, per research R5:
  - Python: `import json`, `import werkzeug.http` and `from typing import Any` are external, as `json`, `werkzeug` and `typing`. A relative import never is, and an import resolved to an indexed file never is.
  - Go: `net/http` is external, while the repository's own module path is not.
  - The existing graph tests still pass.
  - File: tests/test_graph.py
- [x] **T005** [P] `graph.external_imports(cur, repo_id) -> dict[int, set[str]]`. `_imports` is reshaped so `rebuild` and it share one resolution loop, with no copied rules · src/golestan_code_mcp/graph.py

**Checkpoint**: `uv run pytest -q tests/test_schema.py tests/test_graph.py` passes.

## Phase 3: Pages, citations and staleness (US1, US2, US3) 🎯 MVP

Files: src/golestan_code_mcp/chunker.py, src/golestan_code_mcp/ingest.py, src/golestan_code_mcp/wiki.py, tests/test_chunker.py, tests/test_ingest.py, tests/test_wiki.py

**Goal**: `wiki.build` writes a page per qualifying directory with cited symbols. An ingestion that changes a cited symbol marks the page stale and recompiles it.

**Independent Test**:
1. Ingest a fixture repository with a 10-definition package and build its wiki.
2. Read the page and its citations through `wiki`'s read functions.
3. Edit and commit a cited function, ingest again, and check `Summary.wiki`.

### Tests

- [x] **T006** [P] [US1] Chunker doc tests, written to fail first, per research R2:
  - **Python:** the symbol docstring, and the module docstring as the file doc.
  - **Go:**
    - a symbol doc is the `//` run ending on the line above;
    - the package doc is the run just above `package`, skipping `//go:build`;
    - a header separated by a blank line is not attached.
  - **JavaScript:** the `/** */` comment just above the definition.
  - **Cleaning:** the first paragraph only, comment markers removed, whitespace collapsed, at most 1000 characters.
  - **No doc:** a definition without a doc gives `None`.
  - **Unchanged chunks:** every chunk's lines and source are the same as before.
  - File: tests/test_chunker.py
- [x] **T007** [P] [US1] [US2] [US3] Wiki tests through `wiki` directly, against a fixture repository written to fail first. Per research R1, R3, R4, R6, R7, R8 and R11 and contracts/cli.md:
  - **Threshold and naming:**
    - a directory with 10 named definitions gets a page and one with 9 does not;
    - line windows never count;
    - `src/pkg/sub` is named `pkg/sub` and the root is named after the repository;
    - a `src/x` and `x` clash uses full paths.
  - **The text:**
    - a structural sentence with correct counts, then the quoted docs, then the stated no-documentation sentence when there are none;
    - at most 10 key symbols, types first and ranked by callers from outside the directory;
    - Depends on and Used by, from the import edges, plus the outside packages;
    - Sphinx roles reduced;
    - no indexed file name or `line <n>` anywhere in the text, even when a docstring contains one.
  - **Citations:**
    - every key symbol and every named module has a citation;
    - each records the symbol's or file's `commit_sha` and `content_hash`;
    - read back, each gives the current path and line range.
  - **Build behavior:**
    - two builds give the same text and citations, and the second does not rewrite `search_text`;
    - `wiki_at` is set;
    - an unknown or unindexed repository is refused with the contract reason;
    - when the model is loaded, the page index exists after the build.
  - **Staleness:**
    - `mark_stale` marks a page whose cited symbol changed commit or is gone, with the contract `stale_reason`, and leaves the others fresh;
    - `refresh` recompiles stale pages, adds newly qualifying ones and removes ones that no longer qualify, and returns `Refresh`;
    - `refresh` leaves pages stale if it fails part-way;
    - repositories without `wiki_at` are untouched.
  - **Reading:** list, read and citations follow the contract order, refuse an ambiguous name, and refuse an unknown page.
  - **Logging:** one `wiki` record per repository.
  - File: tests/test_wiki.py
- [x] **T008** [P] [US3] Ingest tests, written to fail first:
  - **Docs stored:** docs are written on insert and on a changed file's update. A kept symbol's doc follows a Go comment edit while the symbol's row id stays the same.
  - **The re-read:** a repository stored at `EXTRACT_VERSION` 1 is re-read once, with no new symbol rows.
  - **With a wiki:**
    - editing and committing a cited function gives `Summary.wiki` with that page stale for the contract reason and recompiled;
    - a commit changing only an uncited file marks nothing stale;
    - an ingestion that changes nothing gives no stale pages;
    - a full re-ingestion marks every page stale and recompiles them all.
  - **Without a wiki:** `Summary.wiki` is `None` and no pages are created.
  - **A failed recompile** (monkeypatched) keeps the ingestion committed, leaves the pages stale, and sets `error`.
  - File: tests/test_ingest.py

### Implementation

**Wave 1 — independent (different files):**

- [x] **T009** [P] [US1] Chunker docs per research R2: `Chunk.doc` (default `None`) and the file doc as `parse`'s 4th element, for Python, Go and JavaScript symbols and for Python and Go files, with the cleaning rules. The JS file doc carries the `simplified` comment from R2 · src/golestan_code_mcp/chunker.py
- [x] **T010** [P] [US1] [US2] `wiki.py` build and read, per research R1, R3, R4, R6, R8, R9 and R11 and data-model.md:
  - **Constants:** `COMPILER = "ccctx-wiki/1"`, `THRESHOLD = 10`, `INDEX = "CCCTX_WIKI_HYBRID_IX"`.
  - **The index:** `ensure_index(cur)` creates the page index with `semantic.MODEL` and `semantic.LEXER` when the model is loaded. `wiki` imports `semantic`, never the other way at module level.
  - **Naming:** the page-name rule.
  - **Compiling:**
    - qualifying directories;
    - the text sections and cleaning;
    - key symbols by external callers;
    - dependencies from `ccctx_imports` and `graph.external_imports`;
    - `calls` citations from the call edges.
  - **Building:** `build(conn, repo=None)` upserts pages, writes `search_text` only when the text changed, replaces citations, deletes pages that no longer qualify, sets `wiki_at`, logs, and returns per-repository counts.
  - **Reading:**
    - `pages(conn, repo)`;
    - `read(conn, page, repo) -> Page` with `CitationView`s read through the keys;
    - `WikiError(ValueError)` refusals with the contract wording.
  - File: src/golestan_code_mcp/wiki.py

**⟶ Wait for Wave 1 to finish, then:**

**Wave 2 — independent (different files):**

- [x] **T011** [P] [US1] Ingest stores docs: `ccctx_files.doc` on insert and update, `ccctx_symbols.doc` on insert, and `doc` in `_keep_unchanged`'s update. `_prepare` and `_write` take `parse`'s 4th element. `EXTRACT_VERSION = 2` · src/golestan_code_mcp/ingest.py
- [x] **T012** [P] [US3] `wiki.mark_stale(cur, repo_id) -> list[tuple[str, str]]` and `wiki.refresh(conn, repo_id) -> Refresh`, per research R7 and the data-model state transitions:
  - `mark_stale` marks only fresh pages of repositories with `wiki_at` set, naming the first offending citation.
  - `refresh` recompiles every stale page, adds and removes pages, runs in its own transaction, and rolls back and returns `error` on failure.
  - File: src/golestan_code_mcp/wiki.py

**⟶ Wait for Wave 2 to finish, then:**

- [x] **T013** [US3] Ingest calls the wiki, per research R7:
  - `mark_stale` runs inside the transaction after `_write`.
  - `refresh` runs after `conn.commit()` and catches its own failure.
  - `Summary` gains `wiki: Refresh | None`, None without a wiki or in `current` mode. The stale list comes from `mark_stale`.
  - File: src/golestan_code_mcp/ingest.py

**Checkpoint**: `uv run pytest -q tests/test_chunker.py tests/test_wiki.py tests/test_ingest.py` passes. Pages are built, cited and kept current by ingestion.

## Phase 4: Pages in search (US4)

Files: src/golestan_code_mcp/semantic.py, tests/test_semantic.py

**Goal**: hybrid search returns page hits placed by semantic similarity, with the definitions block still first.

**Independent Test**: build a fixture wiki and search a module question. The page ranks above its directory's symbols, and an identifier query still puts its definitions first.

### Tests

- [x] **T014** [P] [US4] Search tests, written to fail first, per research R8 and contracts/tools.md `search_code`:
  - **The hit:** a page hit has `kind` `page`, the page name, the directory as `path`, null line range, `state`, and a snippet of the text's first 10 lines.
  - **Placement:** a page lands above the first non-definition hit with a lower similarity. A module question puts the page above its directory's symbols, and an identifier query keeps its definitions first.
  - **Filters:** `repos` and `language` filter pages, using the page's language.
  - **The floor:** the keyword-or-floor rule drops weak pages, so an out-of-domain question gets no page.
  - **No page index:** without it, search returns symbols only.
  - **`load_model`** also creates the page index, and is still idempotent.
  - **Symbol hits** have `state` None and are unchanged otherwise.
  - File: tests/test_semantic.py

### Implementation

- [x] **T015** [US4] `semantic.search` page hits and the page index, per research R8:
  - `Result` gains `state` and allows `None` lines.
  - `load_model` calls `wiki.ensure_index`.
  - `search` runs the request against `wiki.INDEX` when it exists, and resolves and scopes the pages.
  - Pages are placed by similarity after the definitions block, then the list is cut to `limit`.
  - `wiki` is imported inside the functions that use it, because `wiki` imports `semantic`.
  - File: src/golestan_code_mcp/semantic.py

**Checkpoint**: `uv run pytest -q tests/test_semantic.py tests/test_eval.py` passes.

## Phase 5: The CLI (US1, US2, US3, US4)

Files: src/golestan_code_mcp/cli.py, tests/test_cli.py

**Goal**: `ccctx wiki build|list|show|citations`, the wiki lines in the ingest summary, and page rows in `ccctx search`, exactly as contracts/cli.md.

**Independent Test**: run the commands from the contract against a fixture repository and compare each output with the core functions.

### Tests

- [x] **T016** [P] [US1] [US2] [US3] [US4] CLI tests per contracts/cli.md:
  - **`wiki build`:** its lines, and the no-model note.
  - **`wiki list`:** its columns and order, and `no wiki pages`.
  - **`wiki show`:**
    - the header;
    - the stored text unchanged;
    - Sources rendered from the citations;
    - `gone` for a missing record.
  - **`wiki citations`:** its columns.
  - **Refusals:** every failure row exits 1 with its message, and the database down exits 2.
  - **Ingest summary:** the per-page `Wiki` lines and the counts line, `not recompiled` with the warning on a failed recompile, and no `Wiki` lines without a wiki.
  - **`ccctx search`:** page rows show `KIND` `page` or `page (stale)` and `LINES` `-`.
  - **Logging:** the `wiki` record on standard error.
  - File: tests/test_cli.py

### Implementation

- [x] **T017** [US1] [US2] [US3] [US4] The `wiki` command group with `build`, `list`, `show` and `citations` and their `--repo`, calling `wiki`. Also the ingest summary's wiki lines, the search page rows, and the `wiki` logger wired to standard error like `ingest.log` · src/golestan_code_mcp/cli.py

**Checkpoint**: `uv run pytest -q tests/test_cli.py` passes.

## Phase 6: The MCP tools (US4)

Files: src/golestan_code_mcp/server.py, tests/test_server.py

**Goal**: seven tools. `read_wiki` lists and reads pages, and `search_code` returns page hits, exactly as contracts/tools.md.

**Independent Test**: through the in-memory client, list the tools, call `read_wiki` with and without a page, and call `search_code` for a module question. Compare each with the core.

### Tests

- [x] **T018** [P] [US4] Server contract tests:
  - **The tool list:** seven tools, in order.
  - **`read_wiki`:** its description and parameter descriptions equal contracts/tools.md, with the read-only annotation.
  - **`search_code`:** its new description, and the schema's `start_line`/`end_line` as `integer | null` and `state`.
  - **Parity:** `read_wiki` with a page equals `wiki.read`, and without one equals `wiki.pages`, both capped at 200 with `truncated`. A `search_code` page hit equals the core hit.
  - **Refusals are `unavailable` results:** an empty page name (checked before connecting with `DB_PORT=1`), an unknown repository, an unknown page, an ambiguous name and an unreachable database.
  - **An unknown argument** is refused.
  - **Logging** covers `read_wiki`.
  - File: tests/test_server.py
- [x] **T019** [US4] `read_wiki(page, repo)` returning `WikiResults`, the `SearchHit` change (nullable lines, `state`), and the new `search_code` description, verbatim from the contract. The strict-arguments loop covers the new tool · src/golestan_code_mcp/server.py

**Checkpoint**: `uv run pytest -q tests/test_server.py` passes.

## Phase 7: Polish

**Wave 1 — independent:**

- [x] **T020** [P] Live checks against flask and gin, recorded in this step's capture:
  - **SC-001:** `ccctx wiki build` times, and the page sets for flask and gin.
  - **SC-002:** the `flask/json` page's purpose and at least 5 real symbols.
  - **SC-003:** every citation of every page resolves, and no page text contains a path or line number.
  - **SC-005:** the four search questions.
  - **SC-007:** `read_wiki` through the Inspector CLI, timed, compared with `ccctx wiki show flask/json`.
  - **If SC-005 fails:** apply research R8's fallback in `semantic.py` and its test, rerun, and record the outcome. This is the only Polish task that may edit `semantic.py`.
  - Files: scratchpad, plus src/golestan_code_mcp/semantic.py and tests/test_semantic.py only for the fallback
- [x] **T021** [P] Staleness live check per research R10 (SC-004):
  1. `git clone --local` flask into the scratchpad and register it as `wiki-flask`.
  2. Ingest it, then build its wiki.
  3. Edit `dumps` in `src/flask/json/__init__.py`, then commit.
  4. Ingest, and record the summary and `ccctx wiki list --repo wiki-flask`.
  5. Remove the repository and the clone.
  - Files: scratchpad only

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T022** README:
  - the wiki commands, with an example page;
  - how citations and staleness work;
  - the one-time re-read on the first ingest after upgrading;
  - `read_wiki`, and page hits in search, with SC-005's results;
  - the 1.1.0 change note;
  - the user's own staleness steps.
  - File: README.md

**⟶ Wait for T022, then:**

- [x] **T023** Suites:
  - `uv run pytest -q` with the database up, then with `DB_PORT=1` so the database tests skip cleanly;
  - `uvx ruff check src tests` against the 28-finding baseline;
  - the retrieval evaluation (`tests/test_eval.py`), whose top-5 hit rate must not drop (SC-006).

## Dependencies & Execution Order

- **Phase order:**
  - Setup, then Foundational, then Phase 3.
  - Phase 4 needs Phase 3, for `wiki.INDEX` and `wiki.ensure_index`.
  - Phases 5 and 6 need Phases 3 and 4. They own different files, so they run together.
  - Polish runs last.
- **Phase 1:** T001 alone.
- **Phase 2:** one wave, T002 to T005, test and implementation pairs on separate files.
- **Phase 3:**
  - Tests T006 to T008 come first.
  - Wave 1 is T009 and T010. It blocks Wave 2, T011 and T012.
  - Wave 2 blocks T013.
- **Phase 4:** T014, then T015.
- **Phase 5:** T016, then T017.
- **Phase 6:** T018, then T019.
- **Phase 7:**
  - T020 and T021 run together, then T022, then T023.
  - Only T020 may touch `semantic.py`, for the R8 fallback.
