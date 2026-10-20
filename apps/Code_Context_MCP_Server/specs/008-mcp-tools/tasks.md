# Tasks: Code Context Tools for AI Clients

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contracts**: [tools.md](./contracts/tools.md), [cli.md](./contracts/cli.md)

US1, US2 and US3 share one phase. All three are tools in `server.py`, so splitting them would give that file three owners. The CLI's search options (US1) live in the US4 phase, because `cli.py` also carries `ccctx mcp`.

## Phase 1: Setup

- [x] **T001** Version `1.0.0` in `pyproject.toml` and `__version__`: the tool rename is a breaking change (constitution III) · pyproject.toml, src/golestan_code_mcp/__init__.py

## Phase 2: Foundational

The core functions every tool and the CLI call. No story work starts until this phase is done.

**Wave 1 — independent (different files):**

- [x] **T002** [P] Search tests, written to fail first, per contracts/tools.md `search_code`:
  - `language="python"` returns only Python hits, and `repo` plus `language` together still fill `limit` when enough exist.
  - `limit=3` returns at most 3. `limit` 0, 51 and a non-integer are refused with `limit must be between 1 and 50`.
  - An unknown language is refused with the list of valid languages, before connecting (`DB_PORT=1`).
  - Every hit has `language`. Its `snippet` is the opening of the stored source: at most 10 lines and 800 characters, no trailing newline.
  - Without `language` and `limit`, the hits are the same as before this step.
  - File: tests/test_semantic.py
- [x] **T003** [P] `semantic.search(conn, question, repos, mode, env, language=None, limit=10)` per research R5 and R6:
  - Add `LANGUAGES` (the chunker's values plus `text`) and `check_limit` / `check_language`, raising `ValueError` with the contract reasons, so the CLI and server can check before connecting.
  - A hit is in scope when its repository and language both match. Pool widening counts in-scope hits against `limit`.
  - `Result` gains `language` and `snippet`, read in the existing symbol query with `f.language` and `dbms_lob.substr(s.source, 800, 1)`.
  - File: src/golestan_code_mcp/semantic.py
- [x] **T004** [P] `graph.definitions` tests, written to fail first, per contracts/tools.md `get_symbol`:
  - A qualified name returns exactly that definition with its stored source and line range.
  - A bare name returns the function and the method, each with its qualified name.
  - `repos=` limits the matches, and an unknown repository is refused first.
  - With more than 5 matches: 5 returned, ordered by repo, path and start line, with `total` the full count.
  - A 450-line definition comes back as its first 400 lines with `cut` true and its full `end_line`.
  - Line windows never match. An empty name and an unknown name are refused.
  - File: tests/test_graph.py
- [x] **T005** [P] `graph.definitions(conn, name, repos=None) -> tuple[list[Definition], int]` per research R7: the `_targets` name rules, the first 5 by repo, path and start line, each source cut at 400 lines with `cut`, plus the total. The frozen `Definition` dataclass has `name`, `kind`, `repo`, `path`, `start_line`, `end_line`, `source` and `cut` · src/golestan_code_mcp/graph.py

**Checkpoint**: `uv run pytest -q tests/test_semantic.py tests/test_graph.py` passes. Search filters by language and count with snippets, and definitions read back in full.

## Phase 3: The tools (US1, US2, US3) 🎯 MVP

Files: src/golestan_code_mcp/server.py, tests/test_server.py

**Goal**: the server lists the six tools of contracts/tools.md, with their descriptions, and each answers from the core.

**Independent Test**: list the tools through an in-memory client, then call `search_code` with `{"query": "how are requests routed", "repo": "flask"}`, `get_symbol` with `{"name": "Flask.dispatch_request"}` and `find_callers` with `{"name": "url_for", "repo": "flask"}`, and compare each with the core.

### Tests

- [x] **T006** [P] [US1] [US2] [US3] Server contract tests through the in-memory client:
  - **The tool list:**
    - exactly `search_code`, `get_symbol`, `find_callers`, `find_callees`, `impact_of`, `list_repositories`, in that order;
    - each description and each parameter description equals contracts/tools.md;
    - parameters, required names and defaults as in its table;
    - `readOnlyHint` true on every tool.
  - **Parity with the core:**
    - `search_code` equals `semantic.search` for the same query, repo, language and limit;
    - `get_symbol` equals `graph.definitions`, with `total` and `truncated`;
    - `find_callers`, `find_callees` and `impact_of` equal `graph.callers`, `graph.calls` and `graph.impact`;
    - every item carries a repo, a path and lines;
    - the 200-row cap still holds.
  - **Refusals are `unavailable` results:** an empty query, a bad limit, an unknown language, an unknown repo, an empty name, a bad depth, an unknown name, a missing model and an unreachable database. A call made after an unreachable one succeeds without a restart.
  - **An unknown argument** (`repos`, `question`) is refused, naming the argument.
  - **The logging test** covers the new tool names.
  - File: tests/test_server.py
- [x] **T007** [P] [US1] [US2] [US3] Rewrite the tools per contracts/tools.md:
  - **Removed:** `health`, `search`, `callers`, `calls`, `impact`, and the `repos` parameter.
  - **Added:**
    - `search_code(query, repo, language, limit)` returning `SearchResults` of `SearchHit` with `language` and `snippet`;
    - `get_symbol(name, repo)` returning `SymbolResults` with `total` and `truncated`;
    - `find_callers(name, repo)`, `find_callees(name, repo)` and `impact_of(name, depth, repo)` on the existing `_graph` envelope;
    - `list_repositories` with the new description.
  - **For every tool:**
    - its description is verbatim from the contract;
    - each parameter is `Annotated[..., Field(description=...)]`;
    - it carries `ToolAnnotations(readOnlyHint=True)`;
    - extra arguments are forbidden on each tool's argument model (research R3).
  - **Checks:** limit, language, depth and name are checked before connecting.
  - File: src/golestan_code_mcp/server.py

**Checkpoint**: `uv run pytest -q tests/test_server.py` passes. An MCP client sees six well-described tools that return the same answers as the core.

## Phase 4: Plugging into a client (US4), with the CLI search options (US1)

Files: src/golestan_code_mcp/cli.py, tests/test_cli.py

**Goal**: `ccctx mcp` starts the server from any directory, and `ccctx search` takes the same language and count as `search_code`.

**Independent Test**: start `ccctx mcp` as a child process with an MCP stdio client, list the tools, and call `search_code`. Then compare with `ccctx search "how are requests routed" --repo flask`.

### Tests

- [x] **T008** [P] [US4] [US1] CLI tests per contracts/cli.md:
  - **`ccctx mcp` without a database:** with `DB_PORT=1`, it starts the server without connecting (`server.main` monkeypatched) and exits 0.
  - **A real child process:** started as `python -m golestan_code_mcp.cli mcp` from a temporary working directory and driven by `mcp.client.stdio`, it lists the six tools. This proves that standard output carries only the protocol and that settings are found outside the project.
  - **Search options:** `ccctx search --language` and `--limit` print the same rows as the core.
  - **Refusals:** a bad `--limit` and an unknown `--language` exit 1 with the contract messages before connecting.
  - File: tests/test_cli.py
- [x] **T009** [P] [US4] [US1] CLI changes:
  - `ccctx mcp` calls `server.main()` before `main()` connects or migrates.
  - `ccctx search` gains `--language` and `--limit` (default 10), passed to `semantic.search`.
  - Bad values exit 1 through `semantic.check_limit` and `check_language`, checked before connecting.
  - File: src/golestan_code_mcp/cli.py

**Checkpoint**: `uv run pytest -q tests/test_cli.py` passes. A client can start the server as `ccctx mcp`.

## Phase 5: Polish

**Wave 1 — independent:**

- [x] **T010** [P] Live checks against flask and gin, results recorded in this step's capture:
  - **SC-001:** `npx @modelcontextprotocol/inspector --cli` runs `uv run ccctx mcp` with `tools/list`. All six tools appear, with every parameter described.
  - **SC-002:** `search_code` for `{"query": "how are requests routed", "repo": "flask"}` lists the same 10 symbols in the same order as `ccctx search "how are requests routed" --repo flask`.
  - **SC-005:** a timed call of each tool, and the time from start to tool list.
  - **SC-006:** every tool returns its reason within 10 s against an unreachable port.
  - Files: scratchpad only
- [x] **T011** [P] Tool-choice evaluation (SC-003, SC-004, research R8):
  - Run the five questions with `claude -p`, using `--strict-mcp-config`, `--tools ""` and `--output-format stream-json`, from an empty scratch directory. The server config uses an absolute `uv run --directory` command.
  - Record the order of tool calls and the routing answer.
  - If a question picks the wrong tool first, fix that tool's description in contracts/tools.md and server.py, then rerun the question.
  - Files: scratchpad, and server.py and the contract only when a description changes

**⟶ Wait for Wave 1 to finish, then:**

- [x] **T012** README, per FR-016:
  - Install with `uv tool install --editable .`. For a non-editable install, pass settings with `claude mcp add -e`.
  - `ccctx mcp`, the Inspector command, and `claude mcp add ccctx -- ccctx mcp`.
  - The six tools with their parameters, and the rename from the previous step's tool names.
  - The new `ccctx search` options.
  - What the client chose in the tool-choice evaluation, from T011.
  - File: README.md

**⟶ Wait for T012, then:**

- [x] **T013** Suites:
  - `uv run pytest -q` with the database up, then with `DB_PORT=1` so the database tests skip cleanly.
  - `uvx ruff check src tests` against the 25-finding baseline.
  - The retrieval evaluation (`tests/test_eval.py`), whose top-5 hit rate must not drop.

## Dependencies & Execution Order

- **Phase order:** Setup, then Foundational. After that, Phases 3 and 4 own different files and can run in either order or together. Polish runs after both.
- **Phase 1:** T001 alone.
- **Phase 2:** one wave, T002 to T005, test and implementation pairs on separate files.
- **Phase 3:** one wave, T006 and T007.
- **Phase 4:** one wave, T008 and T009.
- **Phase 5:** T010 and T011 together, then T012, then T013. T011 is the only Polish task that may edit `server.py`, and only after Phase 3 is done.
