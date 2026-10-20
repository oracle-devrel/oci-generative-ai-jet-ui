# Tasks: Code Relationship Graph

**Spec**: [code-graph.spec.md](./code-graph.spec.md) | **Plan**: [plan.md](./plan.md) | **Contracts**: [cli.md](./contracts/cli.md), [graph-tools.md](./contracts/graph-tools.md), [schema.md](./contracts/schema.md)

**Scale note**: 13 files across parsing, schema, ingest, a new graph module, and the CLI and MCP surfaces. Watch the ingest seam: refs are written per re-read file, and edges are always rebuilt from refs, so an edited callee's new symbol id never strands an unchanged caller.

US1, US2 and US3 share one phase. All three questions live in `graph.py` and `cli.py`, so splitting them would give those files three owners.

## Phase 1: Foundational

Extraction and storage that every question reads. No story work starts until this phase is done.

**Wave 1 — independent (different files):**

- [x] **T001** [P] Tests for `parse()`, written to fail first. Python: a bare call, an `attr` call keeping its receiver, a `self.x()` call, a decorator call credited to the enclosing scope rather than the decorated function, a class-body call credited to the class, a nested-function call credited to the enclosing symbol, and no calls from comments, docstrings or strings. Imports: `import a.b`, `from a.b import c`, `from . import x` (level 1) and `from ..m import y` (level 2), each with its bound name. Go: a call, a selector call, and `import_spec` with and without an alias. JavaScript: a call, a member call, `new X()`, relative `import … from` and `require("./x")`, and a bare package import ignored. A file with a syntax error yields no calls or imports · tests/test_chunker.py
- [x] **T002** [P] `chunker.parse(language, text)` returns the chunks, the calls `(caller, name, form, receiver, line)` and the imports `(module, rel_level, bound)` from one tree. The caller is the qualified name of the innermost definition node by byte range, or `None` at module level. Subscript calls, calls of calls and function literals are skipped. `chunk()` becomes a wrapper returning only the chunks. The `has_error` gate returns nothing for all three · src/golestan_code_mcp/chunker.py
- [x] **T003** [P] Tests for migration 6, written to fail first: the five tables and `extract_version` exist; `ccctx_call_refs_form_ck` rejects a form other than `bare`/`attr`; `ccctx_imports_pair_uk` rejects a duplicate pair; deleting a file cascades its refs and every edge touching it or its symbols; `ccctx_graph` exists and a one-hop `graph_table` query over `calls` returns an inserted edge · tests/test_schema.py
- [x] **T004** [P] Migration 6 "code graph" exactly as contracts/schema.md: `ccctx_call_refs`, `ccctx_import_refs`, `ccctx_calls`, `ccctx_file_calls`, `ccctx_imports` with their constraints and indexes, `ccctx_repos.extract_version`, and `create or replace property graph ccctx_graph` · src/golestan_code_mcp/schema.py

**Checkpoint**: `uv run pytest -q tests/test_chunker.py tests/test_schema.py` passes. Calls and imports are extracted and the graph schema exists.

## Phase 2: Callers, calls and impact (US1, US2, US3, all P1) 🎯 MVP

Files: src/golestan_code_mcp/graph.py, src/golestan_code_mcp/ingest.py, src/golestan_code_mcp/cli.py, tests/test_graph.py, tests/test_cli.py

**Goal**: ingest fills the graph, and `ccctx callers`, `ccctx calls` and `ccctx impact` answer from it.

**Independent Test**: ingest flask, then run `ccctx callers url_for`, `ccctx calls url_for` and `ccctx impact url_for --depth 3`, and compare with `grep -rn "url_for" ~/ccctx-repos/flask`.

### Tests

Written to fail first, against small repositories built in the test.

- [x] **T005** [P] [US1] [US2] [US3] `graph` tests. Resolution: rules 1 to 4 (bare call to a function or class; `flask.url_for` through an imported module treated as bare; `self.x` preferring the enclosing class; other `attr` to `*.x` methods), then the same-file, imported-file, whole-repo order. An unresolved call has no edge, and no edge crosses repositories. Imports: a Python absolute and a relative import, a Go package import yielding one row per file in the directory, a JavaScript relative path. Callers: a bare name lists callers of the function and of the method, each labeled with its callee; `Type.method` narrows to the method; a module-level call is kind `file`, name `(module)`. Calls: a function calling only the standard library returns nothing. Impact: hop counts on a chain, the shortest hop on a diamond, a cycle and a recursive function each listed once, and depth 1 equal to the callers set. Refusals: an unknown name, an empty name, depth 0, 6 and -1. `repos=` limits every question · tests/test_graph.py
- [x] **T006** [P] [US1] [US2] [US3] CLI tests per contracts/cli.md: the three headers and their empty-result messages, `--repo` repeated, `--depth` defaulting to 3, a bad depth exiting 1 with `depth must be between 1 and 5` before connecting, and `no symbol named '<name>'` exiting 1 · tests/test_cli.py

### Implementation

**Wave 1 — independent (different files):**

- [x] **T007** [P] [US1] `graph.rebuild(cur, repo_id)`: read the repository's refs, symbols and file paths, resolve imports (Python dotted module and relative level to a file path, Go package directory to its files, JavaScript relative path), then resolve calls by the four rules and the tie-break order. It deletes and bulk-inserts `ccctx_imports`, `ccctx_calls` and `ccctx_file_calls` for the repository. Mark the per-repository rebuild with `# simplified: whole repository rebuilt each ingest, rebuild only the affected names when it shows up in timings` · src/golestan_code_mcp/graph.py
- [x] **T008** [P] [US1] Ingest stores refs and rebuilds edges. Switch to `chunker.parse`. For each re-read file, replace its `ccctx_call_refs` and `ccctx_import_refs`, mapping each call's caller to the id of the kept or inserted symbol. After the lock, an `extract_version` other than `EXTRACT_VERSION = 1` treats every listed file as changed and disables the `current` short-circuit. `_keep_unchanged` still keeps unchanged symbols, so nothing is re-embedded. The write sets `extract_version` and calls `graph.rebuild` in the same transaction · src/golestan_code_mcp/ingest.py

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T009** [US1] [US2] [US3] `graph.callers`, `graph.calls` and `graph.impact` with `Caller`, `Callee` and `Impact` results as data-model.md. Each runs a `graph_table … match` query: callers runs one query per source label, symbol and `code_file`; impact uses `-[e is calls]->{1,N}` with `count(e.line)` as hops, then `min(hops)` per symbol, nearest first. Names are case-sensitive: a qualified name matches exactly, a bare name matches `x` or `*.x`. Depth is checked as an integer from 1 to 5 before it is written into the SQL. The `repos` filter applies to the matched name and to the results. No embedding model is needed · src/golestan_code_mcp/graph.py

**⟶ Wait for T009 to finish, then:**

- [x] **T010** [US1] [US2] [US3] `ccctx callers <name>`, `ccctx calls <name>` and `ccctx impact <name> [--depth N]` with `--repo`, formatted as contracts/cli.md. Depth is checked before connecting · src/golestan_code_mcp/cli.py

**Checkpoint**: `uv run pytest -q tests/test_graph.py tests/test_cli.py` passes. After `ccctx ingest flask`, all three commands answer from the graph.

## Phase 3: The graph stays current (US4, P2)

Files: tests/test_ingest.py

**Goal**: an incremental ingest leaves the same relationships as a full rebuild.

**Independent Test**: delete a caller and re-ingest; then compare the graph after an incremental ingest with the graph after `--full`.

- [x] **T011** [US4] Ingest tests, compared by names and paths, never ids: a deleted caller disappears from callers; editing a callee in another file keeps its unchanged callers; refs and edges after an incremental ingest equal those after `--full` across an added, edited, deleted and renamed caller and callee; a repository with `extract_version` NULL re-reads every file, keeps every symbol id, and ends at version 1; a failed run leaves the version as it was. Update existing tests the new tables affect. A failure here is fixed in ingest.py or graph.py, which Phase 2 has finished with · tests/test_ingest.py

**Checkpoint**: `uv run pytest -q tests/test_ingest.py` passes.

## Phase 4: Agents can ask too (US5, P2)

Files: src/golestan_code_mcp/server.py, tests/test_server.py

**Goal**: MCP tools `callers`, `calls` and `impact` return what the CLI returns.

**Independent Test**: call each tool on `url_for` and compare it with the core function.

**Wave 1 — independent (different files):**

- [x] **T012** [P] [US5] Server tests per contracts/graph-tools.md: each tool equals its `graph` function; the `{status, reason, results, truncated}` envelope; results capped at 200 with `truncated` set; refusals come back as status `unavailable` with the reason; the tool list includes the three tools · tests/test_server.py
- [x] **T013** [P] [US5] The `callers`, `calls` and `impact(name, depth=3, repo, repos)` MCP tools on the `graph` core · src/golestan_code_mcp/server.py

**Checkpoint**: `uv run pytest -q tests/test_server.py` passes.

## Phase 5: Polish

**Wave 1:**

- [x] **T014** Live validation against the flask and gin index. Re-ingest both and record the time of the version upgrade and that no symbol was re-embedded. Classify every `grep -rn "url_for" ~/ccctx-repos/flask` hit with a scratchpad script as a call inside a Python function or method, or as a comment, docstring, string, docs or template line. Compare it with `ccctx callers url_for`: recall of at least 90% (SC-001) and no non-code hit (SC-002). Compare `ccctx impact url_for --depth 1 | wc -l` with `--depth 3` (SC-003). Time each of the three commands, under 2 s (SC-004). Compare the MCP tools with the CLI on `url_for` (SC-006) · scratchpad only

**⟶ Wait for T014 to finish, then:**

- [x] **T015** README "Code relationships" section: what is extracted, the three commands with sample output from T014, `--depth` 1 to 5, name matching, and the limits (name-based resolution, no dynamic calls, line-window files contribute nothing) · README.md

**⟶ Wait for T015 to finish, then:**

- [x] **T016** Run the suites: `uv run pytest -q` with the database and with `DB_PORT=1`, and `uvx ruff check` with no findings beyond the 22 accepted ones (SC-005 runs inside the suite) · no file

## Dependencies & Execution Order

- **Foundational** blocks everything. Its one wave builds T001 to T004 together.
- **Phase 2 (US1–US3)** needs Foundational. Wave 1 (T007, T008) blocks T009, which blocks T010. T005 and T006 are written with Wave 1.
- **Phase 3 (US4)** and **Phase 4 (US5)** both need Phase 2 and share no file, so they run in parallel. Phase 4 builds T012 and T013 together.
- **Polish** needs every story. T014 blocks T015, which blocks T016.
