---

description: "Task list for splitting the large source and test files"
---

# Tasks: Split Large Modules

**Input**: Design documents from `specs/013-split-large-modules/`

**Prerequisites**:
- plan.md
- spec.md
- research.md (R1–R14)
- data-model.md (the module map)
- contracts/interfaces.md
- contracts/conventions.md
- quickstart.md

**Tests**: The feature's own check, `tests/test_layout.py`, is written first and fails on master (constitution VI,
research R12). The existing suite is the regression net. Every test is kept (FR-006).

**Organization**: Tasks are grouped by user story. Each story ends at a checkpoint that can be verified on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1, US2 or US3, from spec.md
- **Paths**: relative to the repository root. `src/golestan_code_mcp/` is shortened to `pkg/` in the descriptions.

## Rules for every move task

These apply to each task of Phases 3 and 4, and are not repeated in them.

- **Move, don't change.** Definitions move unchanged, with their names (research R8). The only edits are import
  lines and module-qualified references.
- **Docstrings.** Every new file opens with a module docstring whose first line states what it holds (FR-003).
  Every new area folder's `__init__.py` holds only a docstring (research R2).
- **Imports.** Functions and module-level values from another file are used through their module (`runs.record`).
  Classes, exceptions and result types may be imported by name. Imports are absolute (research R4).
- **Late imports.** A late import keeps its reason comment, retargeted (research R5).
- **Logger names.** Each area's logger name stays as it is today (research R7).
- **Remove the old file.** When a source file is emptied, delete it. Then retarget every importer in `src/` and
  `tests/`, including `monkeypatch.setattr` targets, which must name the module that defines the name (contracts
  conventions 10).
- **Verify before ticking.** A task is done when its area's tests pass, `movecheck.py --imports` passes, and
  `movecheck.py` shows no missing, changed or duplicated definition for that area.

---

## Phase 1: Setup

**Purpose**: The reference copy of master that the checks compare against.

- [X] T001 Create the master worktree with `git worktree add %TEMP%\ccctx-master master`, and copy `.env` into it. It
  is removed in T049.
- [X] T002 Record master's test inventory and runtime, for later comparison (research R14):
  - **Test ids.** Save `uv run pytest --collect-only -q` to `%TEMP%\ccctx-before\tests.txt`.
  - **Runtime and counts.** Run the full suite with `--durations=0`. Save the wall time and the pass, skip and fail
    counts to `%TEMP%\ccctx-before\suite.txt`.

---

## Phase 2: Foundational (blocks every story)

**Purpose**: The three checks that prove the split changed nothing, written before any code moves.

- [X] T003 Write `tests/test_layout.py` (research R12, contracts/conventions.md 1–3). It has three tests:
  - **Size.** A test parametrized over every `.py` file under `src/` and `tests/`, except `tests/fixtures/`. It fails
    for a file over 300 lines.
  - **Docstring.** A test that each such file opens with a module docstring.
  - **README.** A test that the README's `## Layout` section lists exactly the source and test files on disk, no more
    and no fewer. The failure names the extra or missing ones.

  Its own docstring explains the rules. Run it, and confirm it fails on today's files: 9 source and 11 test files are
  over the limit, and the README doesn't match.
- [X] T004 Write `specs/013-split-large-modules/movecheck.py` (research R9).
  - **Inputs.** `movecheck.py <master-root> <branch-root>` parses every top-level function, class and assignment of
    `src/golestan_code_mcp/**/*.py` in both trees.
  - **Normalizing.** First it drops docstrings, then reduces references to project modules (`x.name` where `x` is an
    imported project module) to the bare name.
  - **Matching.** It matches definitions by name. A name defined at several places on master, such as `_plural` in
    both `wiki.py` and `memory.py`, is matched by old file and new area.
  - **Report.** It prints missing, changed and duplicated definitions, then `N missing, N changed, N duplicated`, and
    allows the expected differences of data-model.md Section 3.
  - **`--tests`.** Does the same for test functions in `tests/**/*.py`, keyed by test name. Fixtures moved to a
    shared `conftest.py` are allowed.
  - **`--report`.** Prints the old→new tables for `moves.md`, and the underscore names now used from another file.
  - **`--imports`.** Imports every module under `pkg/` alone, in a fresh `python -c` process. It then checks that
    `parsing.tables`' tables are not empty.

  Run it with the master worktree as both trees: it reports 0 differences.
- [X] T005 Write `specs/013-split-large-modules/baseline.py` (research R10, contracts/interfaces.md). Running
  `--out DIR` records:
  - **Tools.** The MCP tool listing: names in order, descriptions, input and output schemas, annotations. The server
    is started with `python -m golestan_code_mcp.server` over stdio.
  - **Language tables.** Every key in order, with each value's function name and grammar module.
  - **CLI.** About 130 `ccctx` commands, run in-process through the CLI's `main`, with their stdout, stderr and exit
    code: help for every subcommand, each argument error, repo list, symbols, stats, search in each mode, callers,
    calls, impact, wiki list, show and citations, memory list and facts, feedback list, and eval.
  - **Parse output.** The output of every file of flask, gin and selenium-e2e and of `tests/fixtures/`.
  - **Stored rows.** After `ingest --full` and `wiki build` of a `t-` copy of a sample repository. Large text is
    hashed.
  - **Retrieval.** `ccctx eval --gold gold.json`.

  It masks durations, timestamps and memory facts. `--compare A B` prints the differences, or `no differences`. A
  step that fails with ORA-51815 is retried once.
- [X] T006 Record master's baseline: with `PYTHONPATH=%TEMP%\ccctx-master\src`, run
  `baseline.py --out %TEMP%\ccctx-before\baseline`. Then run it once more on master and compare the two. Any
  difference here is noise from the database, not the code: note the affected items in
  `specs/013-split-large-modules/moves.md` under "Baseline noise", and mask them.
- [X] T007 Create `specs/013-split-large-modules/moves.md`, with these sections, empty:
  - Source moves
  - Test moves
  - Cross-file private names
  - Bugs found, not fixed
  - Baseline noise
  - Verified

**Checkpoint**: the three checks run on master. `test_layout.py` fails as expected, `movecheck.py` reports 0 against
itself, and the baseline repeats on master apart from the noise noted.

---

## Phase 3: User Story 1 - Find and change one concern in a small source file (Priority: P1) 🎯 MVP

**Goal**: Every source file is under 300 lines and holds one concern, in the eight area folders of data-model.md
Section 1. Behavior is identical.

**Independent Test**:
- **Layout.** `pytest tests/test_layout.py -k src` passes.
- **Move check.** `movecheck.py` reports `0 missing, 0 changed, 0 duplicated`, and `--imports` passes.
- **Suite.** The full suite passes. The test files themselves are not split yet; only their imports and patch targets
  are retargeted.
- **Baseline.** `baseline.py --compare` against master on the same database shows no differences.

### parsing/ (from chunker.py and languages.py)

- [X] T008 [US1] Create `pkg/parsing/__init__.py` and `pkg/parsing/common.py`. Move into `common.py`, from
  `chunker.py` and `languages.py`, the shared definitions of data-model.md:
  - **Types.** `Chunk`, `Call`, `Import`, `Found`, `Hit`.
  - **Constants.** `DOTTED`, `COMMENTS`.
  - **Tree helpers.** `_name`, `_definition`, `_text`, `_calls`, `_walk_calls`, `_dotted`, `_child`, `_above`,
    `_modifiers`.
  - **Doc helpers.** `_clean`, `_docstring`, `_alone`, `_comments_above`, `_uncomment`, `_block_doc`.

  Leave the old names importable from `chunker.py` for now, so the tree stays working until T012.
- [X] T009 [US1] Create `pkg/parsing/tables.py`. It holds:
  - **The tables.** `GRAMMARS`, `EXTENSIONS` (with the non-code languages, in today's order), `NAMES`, `WALKERS`,
    `CALLS`, `IMPORTS`, `SYMBOL_DOCS`, `FILE_DOCS`, `NAMESPACES`, `LEADING`.
  - **`register()`.** Today's `languages._register`, renamed.
  - **The late import.** At the end, `from golestan_code_mcp.parsing import languages  # noqa: E402`, with today's
    reason comment (research R6).
- [X] T010 [US1] Create `pkg/parsing/languages/__init__.py`, and the Python, Go and JavaScript files
  `pkg/parsing/languages/python.py`, `go.py` and `javascript.py`, moving their walkers, import readers and doc readers
  from `chunker.py`. Each registers through `tables.register(...)`, with exactly the values of today's dict literals,
  in the order Python, Go, JavaScript.
- [X] T011 [P] [US1] Create the other language files from `languages.py`: `pkg/parsing/languages/csharp.py`,
  `typescript.py` (imports `javascript.py` for `_js_imports`, `_js_doc` and `JS_CALLS`), `c_family.py` (registers C
  and C++), `java.py`, `kotlin.py`, `rust.py`, `php.py`, `ruby.py` and `swift.py`. Each holds one language's
  definitions and its registration call, unchanged. Import them in `languages/__init__.py` in today's order: C#,
  TypeScript, C and C++, Java, Kotlin, Rust, PHP, Ruby, Swift.
- [X] T012 [US1] Create `pkg/parsing/chunks.py` with `detect_language`, `_parser`, `_public`, `_start`, `parse`,
  `chunk` and `windows`.
  - **Remove** `pkg/chunker.py` and `pkg/languages.py`, and the merge loop with them.
  - **Retarget the importers** in `pkg/ingest.py`, `pkg/semantic.py`, `pkg/wiki.py`, `tests/test_chunker.py`,
    `tests/test_languages.py`, `tests/test_wiki.py`, `tests/test_ingest.py` and `tests/test_semantic.py`.
- [X] T013 [US1] Check parsing:
  - **Tests.** Run `tests/test_chunker.py`, `tests/test_languages.py` and `tests/test_wiki.py`.
  - **Move check.** Run `movecheck.py` and `--imports`.
  - **Baseline.** Run the baseline's parse and language-table steps on the branch, and compare them with T006.
    Language order and parse output must be identical.

### search/ (from semantic.py and feedback.py)

- [X] T014 [US1] Create `pkg/search/__init__.py`, `pkg/search/model.py` and `pkg/search/candidates.py` with the
  definitions of data-model.md. Keep `semantic.py`'s late imports of `wiki` and `memory` as late imports in the files
  that now hold their callers.
- [X] T015 [US1] Create `pkg/search/ranking.py` and `pkg/search/query.py`.
  - **`ranking.py`** takes `_boosts`, `_boost`, `_fuse`, `MODULE_WORDS`, `names_module` and `_place`.
  - **`query.py`** takes `LIMIT`, `MAX_LIMIT`, `LANGUAGES`, `SNIPPET_*`, `FLOOR`, `MODES`, `Result`, `check_limit`,
    `check_language`, `_snippet` and `search`.

  Then remove `pkg/semantic.py`.
- [X] T016 [US1] Create `pkg/search/feedback.py` (uses, weights, boost, listing, add, reset) and
  `pkg/search/evaluation.py` (`load_gold`, `matches`, `Evaluation`, `evaluate`). Keep `feedback.py`'s late import of
  `semantic`, retargeted to `search.query`. Remove `pkg/feedback.py`.
- [X] T017 [US1] Retarget every importer of `semantic` and `feedback`:
  - **Source.** `pkg/memory.py`, `pkg/wiki.py`, `pkg/ingest.py`, `pkg/server.py` and `pkg/cli.py`.
  - **Tests.** Every test file. This includes the patches `semantic.search` and `semantic.require_model`, the two
    `INDEX` patches, and `feedback.write_use`, `feedback.add`, `feedback.reset`, `feedback.load_gold` and
    `feedback.evaluate`. Each moves to the module that defines it.

  Run `tests/test_semantic.py`, `tests/test_feedback.py`, `tests/test_eval.py` and `tests/test_cli.py`, then the move
  checks.

### graph/ (from graph.py)

- [X] T018 [US1] Create `pkg/graph/__init__.py`, `pkg/graph/imports.py`, `pkg/graph/build.py` and
  `pkg/graph/queries.py` with the definitions of data-model.md. Remove `pkg/graph.py`.
- [X] T019 [US1] Retarget the importers of `graph`:
  - **Source.** `pkg/ingest.py`, `pkg/wiki.py`, `pkg/memory.py`, `pkg/server.py` and `pkg/cli.py`.
  - **Tests.** The patches `graph.rebuild`, `graph.callers`, `graph.calls` and `graph.impact`, and the private
    helpers used by `tests/test_graph.py`.

  Run `tests/test_graph.py`, `tests/test_ingest.py` and `tests/test_server.py`, then the move checks.

### wiki/ (from wiki.py)

- [X] T020 [US1] Create `pkg/wiki/__init__.py`, `pkg/wiki/text.py`, `pkg/wiki/compile.py`, `pkg/wiki/store.py`,
  `pkg/wiki/build.py` and `pkg/wiki/read.py` with the definitions of data-model.md. Every file logs to
  `golestan_code_mcp.wiki`. Remove `pkg/wiki.py`.
- [X] T021 [US1] Retarget the importers of `wiki`:
  - **Source.** The late imports in `pkg/search/model.py` and `pkg/search/candidates.py`, and `pkg/memory.py`,
    `pkg/ingest.py`, `pkg/server.py` and `pkg/cli.py`.
  - **Tests.** The patches `wiki._write_page`, `wiki._compile`, `wiki.pages`, `wiki.ensure_index` and `wiki.INDEX`.

  Run `tests/test_wiki.py`, `tests/test_ingest.py`, `tests/test_semantic.py` and `tests/test_cli.py`, then the move
  checks.

### memory/ (from memory.py)

- [X] T022 [US1] Create `pkg/memory/__init__.py`, `pkg/memory/store.py`, `pkg/memory/runs.py` and
  `pkg/memory/findings.py` with the definitions of data-model.md.
- [X] T023 [US1] Create `pkg/memory/distill.py`, `pkg/memory/consolidate.py`, `pkg/memory/recheck.py` and
  `pkg/memory/recall.py`. Every memory file logs to `golestan_code_mcp.memory`. Remove `pkg/memory.py`.
- [X] T024 [US1] Retarget the importers of `memory`:
  - **Source.** The late imports in `pkg/schema.py` (to `memory.store.create_package_schema`) and
    `pkg/search/query.py` (to `memory.recall`), and `pkg/ingest.py`, `pkg/server.py` and `pkg/cli.py`.
  - **Tests.** `tests/conftest.py`'s memory guard, which now patches `memory.runs.record`. The patches
    `memory.record`, `memory.model`, `memory.consolidate` and `memory.store_runs`.

  Run `tests/test_memory.py`, `tests/test_schema.py`, `tests/test_ingest.py`, `tests/test_server.py` and
  `tests/test_cli.py`, then the move checks.

### indexing/ (from ingest.py)

- [X] T025 [US1] Create `pkg/indexing/__init__.py`, `pkg/indexing/files.py`, `pkg/indexing/write.py` and
  `pkg/indexing/ingest.py` with the definitions of data-model.md. Every file logs to `golestan_code_mcp.ingest`.
  Remove `pkg/ingest.py`.
- [X] T026 [US1] Retarget the importers of `ingest`:
  - **Source.** `pkg/cli.py`.
  - **Tests.** Every test file that ingests. This includes the patches `ingest.discover` (now `files.discover`),
    `ingest._insert_symbols` (now `write._insert_symbols`) and `ingest.ingest`.

  Run `tests/test_ingest.py`, `tests/test_cli.py` and `tests/test_graph.py`, then the move checks.

### server/ (from server.py)

- [X] T027 [US1] Create `pkg/server/app.py` with `NAME`, `INSTRUCTIONS`, `mcp`, `READ_ONLY`, `SESSION`, `LIMIT`,
  `log`, `_returned`, `_client`, `_use`, `_opened`, `_logged`, `_answer`, `_repos` and `main`.
- [X] T028 [US1] Create the tool files from data-model.md: `pkg/server/search_tools.py`, `graph_tools.py`,
  `wiki_tools.py`, `repository_tools.py` and `memory_tools.py`. Each one's tools are registered on `app.mcp`.
- [X] T029 [US1] Create `pkg/server/__init__.py`. It does three things:
  - **Loads the tools** by importing the tool files in listing order: search, graph, wiki, repository, memory.
  - **Applies the strict-arguments loop** unchanged, after the tools are loaded.
  - **Exposes `main`.**

  Create `pkg/server/__main__.py`, which runs `main()`. Remove `pkg/server.py`. Retarget:
  - **CLI.** The late import in `pkg/cli.py`.
  - **Tests.** `server.mcp`, `server.get_symbol`, `server._returned`, `server.SESSION`, `server.LIMIT` and
    `server.main`, plus the result models used by `tests/test_memory.py`.

  Run `tests/test_server.py`, `tests/test_memory.py` and `tests/test_cli.py`. Then run the baseline's tools step and
  compare it with T006: same tools, in the same order, with the same schemas.

### cli/ (from cli.py)

- [X] T030 [US1] Create `pkg/cli/format.py`, `pkg/cli/index_commands.py`, `pkg/cli/search_commands.py`,
  `pkg/cli/wiki_commands.py` and `pkg/cli/memory_commands.py` with the definitions of data-model.md. A helper used by
  several command files lives in one of them, and the others import it (FR-012).
- [X] T031 [US1] Create:
  - **`pkg/cli/parser.py`**, with `KINDS`, the argument checks and `parser`. It points `set_defaults(run=...)` at the
    command files.
  - **`pkg/cli/main.py`**, with `main`.
  - **`pkg/cli/__init__.py`**, which exposes `main`.
  - **`pkg/cli/__main__.py`**, which runs `main()`.

  Remove `pkg/cli.py`. Retarget `tests/test_cli.py`, and every test that calls `cli.main`, `cli.format_table` or
  `cli.format_summary`. Check that `.venv\Scripts\ccctx.exe --help` works without `uv sync`, and that
  `git diff master -- pyproject.toml` shows `[project.scripts]` unchanged (contracts/interfaces.md).

### US1 checkpoint

- [X] T032 [US1] Verify US1:
  - **Move check.** `movecheck.py %TEMP%\ccctx-master .` reports `0 missing, 0 changed, 0 duplicated`, and
    `--imports` passes.
  - **Layout.** `pytest tests/test_layout.py -k src` passes: every source file is under 300 lines and has a
    docstring.
  - **Suite.** The full suite passes. The only expected failures are the test-file size and README checks of
    `test_layout.py`, which pass after US2 and US3.
  - **Baseline.** Record the branch's baseline to `%TEMP%\ccctx-after\baseline`, right after rerunning master's to
    `%TEMP%\ccctx-before\baseline` on the same database state. Then run `--compare`, which must show no differences.
  - **Record.** Fill moves.md's "Source moves" and "Cross-file private names" from `movecheck.py --report`.

**Checkpoint**: the source is split. Users notice nothing, and a maintainer can open the file named for a concern.

---

## Phase 4: User Story 2 - Find the tests for one concern in a small test file (Priority: P2)

**Goal**: The tests mirror the source folders, in files under 300 lines named for what they test. Setup is shared,
and every test is kept.

**Independent Test**:
- **Layout.** `pytest tests/test_layout.py -k tests` passes.
- **Move check.** `movecheck.py --tests` reports 0 missing and 0 changed.
- **Test count.** `pytest --collect-only -q` has the same count as T002, plus the layout tests.
- **Order.** The suite passes in random order, and file by file.

- [X] T033 [US2] Write the shared setup (research R11):
  - **`tests/conftest.py`** holds the module-scoped `conn` fixture: connect, migrate, and skip when the database is
    unreachable. A file marked `pytest.mark.needs_model` also requires the embedding model, and skips with "embedding
    model not loaded: run `ccctx model load`". At teardown it deletes the `t-%` repositories. It also keeps the memory
    guard and `real_recording`.
  - **`tests/support.py`** holds `git`, `commit`, `write_files` and `make_repo`.
  - **`pyproject.toml`** registers the `needs_model` marker, and sets `addopts = "--import-mode=importlib"` and
    `pythonpath = ["tests"]`.

  Run the suite once: it still passes with the old test files.
- [X] T034 [US2] Move `tests/test_config.py`, `tests/test_db.py`, `tests/test_registry.py` and
  `tests/test_samples.py` onto the shared `conn` and `support` helpers. Remove their copies of the fixture and
  helpers. Run them.
- [X] T035 [US2] Split `tests/test_schema.py` into four files, `tests/test_schema.py`, `test_schema_graph.py`,
  `test_schema_wiki.py` and `test_schema_memory.py`, along the groups of data-model.md Section 2. They use the shared
  `conn`. Run them.
- [X] T036 [P] [US2] Create `tests/parsing/` from `tests/test_chunker.py` and `tests/test_languages.py`:
  - `tests/parsing/test_chunks.py`;
  - `tests/parsing/test_tables.py`, for the checks across languages;
  - `tests/parsing/languages/test_<language>.py`, one per language file.

  Remove the two old files. Run `tests/parsing/`.
- [X] T037 [P] [US2] Create `tests/indexing/` from `tests/test_ingest.py`:
  - `tests/indexing/conftest.py`, for the fixtures several new files share, with `package` scope;
  - `test_files.py` and `test_write.py`;
  - `test_ingest.py`, plus `test_ingest_<concern>.py` files as the 300-line limit requires.

  Remove the old file. Run `tests/indexing/`.
- [X] T038 [P] [US2] Create `tests/search/` from `tests/test_semantic.py`, `tests/test_feedback.py` and
  `tests/test_eval.py`. It holds `test_model.py`, `test_candidates.py`, `test_ranking.py`, `test_query.py`,
  `test_feedback.py` (split by concern if over the limit) and `test_evaluation.py`, plus a `conftest.py` for shared
  fixtures. Remove the old files. Run `tests/search/`.
- [X] T039 [P] [US2] Create `tests/graph/` from `tests/test_graph.py`: `conftest.py` (its module fixtures, with
  `package` scope), `test_imports.py`, `test_build.py` and `test_queries.py`. Remove the old file. Run `tests/graph/`.
- [X] T040 [P] [US2] Create `tests/wiki/` from `tests/test_wiki.py`: `test_text.py`, `test_compile.py`,
  `test_store.py`, `test_build.py` and `test_read.py`, with a `conftest.py` if fixtures are shared. Remove the old
  file. Run `tests/wiki/`.
- [X] T041 [P] [US2] Create `tests/memory/` from `tests/test_memory.py`: `test_runs.py`, `test_findings.py`,
  `test_distill.py`, `test_consolidate.py`, `test_recheck.py` and `test_recall.py`, with a `conftest.py` if fixtures
  are shared. Remove the old file. Run `tests/memory/`.
- [X] T042 [P] [US2] Create `tests/server/` from `tests/test_server.py`: `test_app.py`, `test_search_tools.py`,
  `test_graph_tools.py`, `test_wiki_tools.py`, `test_repository_tools.py` and `test_memory_tools.py`, with a
  `conftest.py` for the shared session fixtures. Remove the old file. Run `tests/server/`.
- [X] T043 [P] [US2] Create `tests/cli/` from `tests/test_cli.py`: `test_format.py`, `test_index_commands.py`,
  `test_search_commands.py`, `test_wiki_commands.py`, `test_memory_commands.py`, `test_parser.py` and `test_main.py`,
  with a `conftest.py` if fixtures are shared. Remove the old file. Run `tests/cli/`.
- [X] T044 [US2] Verify US2:
  - **Move check.** `movecheck.py --tests %TEMP%\ccctx-master .` reports 0 missing and 0 changed.
  - **Test count.** `pytest --collect-only -q` matches T002's count, plus the layout tests.
  - **Layout.** `pytest tests/test_layout.py -k tests` passes.
  - **Random order.** `uv run --with pytest-randomly pytest -q -p randomly` passes.
  - **File by file.** Every test file passes when run alone.
  - **Runtime.** The full suite's time is at most 10% over T002's, on the same database (research R14). If not, move
    the expensive fixtures that are built again into the folder's `conftest.py` with `package` scope.
  - **Record.** Fill moves.md's "Test moves" from `movecheck.py --tests --report`, marking renamed and merged tests.

**Checkpoint**: each concern's tests are in a small file named for it, and run alone.

---

## Phase 5: User Story 3 - Keep the documentation in step with the new layout (Priority: P3)

**Goal**: The README's Layout section lists every file with its purpose, and the layout test keeps it correct.

**Independent Test**:
- **README.** `pytest tests/test_layout.py` passes in full.
- **Failure.** Adding an unlisted file makes it fail with that file's name.

- [X] T045 [US3] Rewrite the `## Layout` section of `README.md`. List every source file by folder, and every test
  file by folder, each with a one-line purpose. Use the first line of the file's docstring where it fits. Keep the
  lines that aren't Python (compose.yaml, db/startup, gold.json, tests/fixtures/).
- [X] T046 [US3] Update the other references to the old file names:
  - **README.** Mentions such as `chunker.py` or `semantic.py` in its other sections.
  - **Source and tests.** Docstrings and comments in `src/` and `tests/` that name a removed file, such as "chunker.py
    merges these tables".

  Docstrings are ignored by `movecheck.py`, so its result stays 0. Then run `pytest tests/test_layout.py` (all pass).
  Add an empty `pkg/search/extra.py`, see the test fail naming it, and remove the file.

**Checkpoint**: the documentation matches the layout, and a test keeps it that way.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T047 Finish `specs/013-split-large-modules/moves.md`. Add any bugs found during the work under "Bugs found,
  not fixed" (behavior is frozen). Check that every test id in `%TEMP%\ccctx-before\tests.txt` appears in "Test
  moves", or under its unchanged id.
- [X] T048 Final verification, with every step of `specs/013-split-large-modules/quickstart.md` 1–6:
  - **Comparison.** The baseline comparison against master, run one after the other on the same database.
  - **Suite.** The full suite, and the suite in random order.
  - **Runtime.** The suite's time, against T002's.

  Record the results, counts and times in moves.md's "Verified" section.
- [X] T049 Bump the version to 1.4.1 in `pyproject.toml` and `pkg/__init__.py`, last (research R13). Add
  "**Changed in 1.4.1.** The code is reorganized into smaller files; no tool, command or stored value changed." to
  the MCP section of `README.md`. Run `uv sync`, then the full suite once more. Remove the master worktree with
  `git worktree remove --force %TEMP%\ccctx-master`, which also deletes its copied `.env`.

---

## Dependencies & Execution Order

### Phases

- **Setup (T001–T002)**: first.
- **Foundational (T003–T007)**: after Setup. It blocks every story, because the checks must exist before code moves.
- **US1 (T008–T032)**: after Foundational. The areas go in sequence, since each removes a module that later areas
  import: parsing, then search, graph, wiki, memory, indexing, server and cli.
- **US2 (T033–T044)**: after US1. The tests are split along the final source layout, and their imports must already
  point at it. T033–T035 come first, then T036–T043 in parallel, then T044.
- **US3 (T045–T046)**: after US2, since the README lists the final test files. T045 can be drafted for the source
  after US1.
- **Polish (T047–T049)**: last. T049 (the version bump) is the final task.

### Inside US1

Within an area, the tasks are sequential: they edit the same old file. T011 is the one parallel task, since its
language files are independent. Every area ends with its tests and the move checks passing, so the tree works after
each area.

### Parallel opportunities

- **T011**: the nine language files can be written in parallel.
- **T036–T043**: the eight test folders, each built from its own old test files.
- **T045**: the source part of the README can be drafted while US2 runs.

## Parallel Example: User Story 2

```text
After T033–T035, start together:
  T036 tests/parsing/   T037 tests/indexing/   T038 tests/search/   T039 tests/graph/
  T040 tests/wiki/      T041 tests/memory/     T042 tests/server/   T043 tests/cli/
Then T044 checks them together.
```

## Implementation Strategy

### MVP first (User Story 1 only)

1. Setup and Foundational: the checks, and master's baseline.
2. US1, area by area. Each area leaves a working, verified tree.
3. Stop at T032. The source is split and proved unchanged. This alone answers the main complaint, that the source
   files are too big.

### Incremental delivery

1. **US1**: the source is split. Its tests still live in the old files, retargeted.
2. **US2**: the tests are split and share their setup.
3. **US3**: the README matches, and the layout test passes in full.
4. **Polish**: final verification, then the version bump.

### Notes

- **Commits.** Commit only when the user asks. A natural point to offer one is after each area's checks pass.
- **Low memory.** If Claude Code stops a long run for low memory, report it and do not restart it unasked.
- **Running with an MCP client open.** `uv run` may fail while an MCP client holds `ccctx.exe`. Use
  `.venv\Scripts\python -m pytest` then.
