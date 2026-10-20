# Research: Split Large Modules

Decisions made while planning. They resolve the questions the spec left to the plan: how the folders are wired, how
the move is proved, and what must be kept identical.

## R1. Area folders, and what stays at the top level

**Decision**: Eight area folders under `src/golestan_code_mcp/`:

- `parsing/`: the chunker, and one file per language.
- `indexing/`: ingest.
- `search/`: semantic search, usage feedback and the gold evaluation.
- `graph/`, `wiki/` and `memory/`: one folder each.
- `server/`: the MCP tools.
- `cli/`: the `ccctx` command.

`config.py`, `db.py`, `registry.py`, `samples.py` and `schema.py` stay at the top level. They are already under 300
lines and serve every area.

**Rationale**: The user chose folders by area (spec, Clarifications). The areas match the project's features and the
README's sections, so a maintainer who knows the feature knows the folder. `parsing` is its own area rather than part
of `indexing`: it has 15 files, and nesting it would put the language files three folders deep.

**Alternatives considered**:
- One flat folder with about 45 files: rejected by the user.
- `parsing` nested under `indexing`: deeper paths for no gain, since only ingest, search and the wiki use the parser.

## R2. One home per name: no re-exports

**Decision**: Each area folder's `__init__.py` holds only a docstring that describes the area. Code imports the file
that defines a name, for example `from golestan_code_mcp.memory import runs` and then `runs.record(...)`. No
`__init__.py` re-exports names from its files.

There are two exceptions, both forced by the installed commands (R3):
- `cli/__init__.py` makes `main` importable from the package.
- `server/__init__.py` makes `main` importable, and also imports the tool files in listing order and applies the
  strict-arguments rule (R6).

**Rationale**:
- **Patching.** Tests replace functions during a test (spec, Edge Cases). If `memory.record` were also re-exported
  from the package, a test could patch the package's copy while the code calls the other one. The test would pass
  without testing anything.
- **Finding things.** With one name in one place, a search for a name finds exactly one definition.
- **Speed.** An empty `__init__.py` also keeps imports cheap and avoids new import cycles. Loading one file of an area
  does not load all the others.

**Alternatives considered**:
- `__init__.py` re-exporting each area's public names, so `memory.record` keeps working: rejected, for the double
  names above.
- Re-export with a check that tests patch the defining file: it checks for a trap that need not exist.

## R3. Installed commands and `python -m`

**Decision**: The four `[project.scripts]` strings in `pyproject.toml` stay exactly as they are:
`golestan_code_mcp.cli:main`, `golestan_code_mcp.server:main`, `golestan_code_mcp.db:main` and
`golestan_code_mcp.samples:main`. They still resolve, because `cli` and `server` become packages whose `__init__.py`
exposes `main` (R2). `cli/__main__.py` and `server/__main__.py` keep `python -m golestan_code_mcp.cli` and
`python -m golestan_code_mcp.server` working. Feature 008's tasks used the second form.

**Rationale**: FR-008 requires no change on the user's side.
- **Installed wrappers.** An editable install wrote the console-script wrappers when it was installed. An MCP client
  starts `.venv\Scripts\ccctx.exe` directly, without `uv sync`, so changing an entry-point string would break the
  client until the next sync.
- **Unchanged strings.** With the strings unchanged, the existing wrappers keep working with no reinstall.

**Alternatives considered**:
- Point the scripts at `golestan_code_mcp.cli.main:main`: this needs a reinstall, and silently breaks registered MCP
  clients until it happens.

## R4. How files import each other

**Decision**:
- **Functions and values from another file** are used through that file's module:
  `from golestan_code_mcp.search import query` and then `query.search(...)`. This covers module-level values such as
  `INDEX` or `LIMIT`.
- **Classes, exceptions and result types** may be imported by name, for example
  `from golestan_code_mcp.search.model import ModelError`.
- **Inside one file**, names are used bare, as today.
- **All imports are absolute**, with no relative imports, matching the current code.

**Rationale**:
- **Patching.** `monkeypatch.setattr(module, name, ...)` only affects code that looks the name up on that module when
  it runs. 42 patches in today's tests depend on this: `semantic.search`, `ingest.discover`, `server.LIMIT` and others.
  Going through the module keeps every patch effective, and the patched module is always the one that defines the
  name.
- **Classes are not patched.** No test replaces a class, so importing classes by name is safe and reads better in
  annotations.

**Alternatives considered**:
- Import every name directly: this breaks patches as soon as the caller and the definition sit in different files.
- Import modules for everything, classes included: it makes annotations long (`model.ModelError`) for no safety gain.

## R5. Import cycles

**Decision**: Six imports today are deliberately late, written inside a function with a comment giving the reason:
- `cli` imports `server` late.
- `feedback` imports `semantic` late.
- `schema` imports `memory` late.
- `semantic` imports `wiki` late twice, and `memory` and `feedback` once each.

Each stays late, retargeted to the new file, with its comment. A late import may become an ordinary one only if the
split removed its cycle, which the import check below proves. No new cycle may appear.

**Check**: In a fresh interpreter, import every module of the package alone, one per process. A cycle, or a table read
before it is filled (R6), fails there.

**Rationale**: Cycles are the main way a split can break loading. A full test run imports everything in one order and
can hide a cycle that another order hits. That would make some command fail on its first import.

## R6. Order-dependent setup: language tables and tool registration

**Language tables.** The chunker's tables map each language to its pieces: `GRAMMARS`, `EXTENSIONS`, `NAMES`,
`WALKERS`, `CALLS`, `IMPORTS`, `SYMBOL_DOCS`, `FILE_DOCS`, `NAMESPACES` and `LEADING`.

- **Where they live.** The tables move to `parsing/tables.py`, with `register()`, which is today's
  `languages._register`, made public.
- **How they fill.** At its end, `tables.py` imports `parsing.languages`, whose `__init__.py` imports each language
  file. Each language file registers itself. This is the pattern `chunker.py` uses today, with the same late import.
  So any file that imports `tables` sees complete tables. This matters because `search` computes its language list
  from `EXTENSIONS` when it loads.
- **Order.** Python, Go and JavaScript register first, as today, through the same `register()` call as the others.
  The ten other languages follow in today's order: C#, TypeScript, C and C++, Java, Kotlin, Rust, PHP, Ruby, Swift.
- **Check.** The baseline (R10) records every table's keys in order, and each value's identity: the function's module
  path is excluded, its name included. Before and after must match.

**MCP tools.** The tools register with the server when their file loads.
- **Order.** `server/__init__.py` imports the tool files in today's listing order: `search_code`, `get_symbol`,
  `find_callers`, `find_callees`, `impact_of`, `read_wiki`, `list_repositories`, `recall`, `mark_used`.
- **Strict arguments.** After those imports, it runs today's strict-arguments loop (FastMCP drops undeclared
  arguments, and the loop makes it refuse them instead). It must run after every tool is registered.

**Rationale**: Both are behavior that depends on load order. They are the places where a pure move could still
change what users see: a tool listed in a different order, or a language missing.

## R7. Logger names and paths derived from files

**Logger names.** The four loggers already have explicit names: `golestan_code_mcp.ingest`, `.memory`, `.server` and
`.wiki`.

- **Unchanged.** Every file of an area keeps its area's current logger name. For example, every `memory/` file uses
  `logging.getLogger("golestan_code_mcp.memory")`.
- **Shared handlers.** The CLI attaches its stderr handler to these loggers, so the printed structured records stay
  identical.

**Paths.** Only `config.PROJECT_ROOT` derives a path from its file's location (`Path(__file__).parents[2]`).
`config.py` does not move, so the path does not change.

## R8. Names stay as they are

**Decision**: Every function, class and constant keeps its exact name, including a leading underscore, even when
another file now uses it. Renaming is left to a separate change.

**Rationale**:
- **Provable move.** With unchanged names, the move check (R9) can prove that each definition moved unchanged.
- **Small test edits.** Tests that refer to private helpers (`graph._files`, `wiki._is_test`, `semantic._place` and
  others) only need their module path changed.

**Recorded.** Every name with an underscore that another file now uses goes into the move record, as a list for a
later clean-up.

**Alternatives considered**:
- Drop the underscore on names now shared across files. This is cleaner, but it mixes a rename into a move, and the
  move check could no longer match definitions by name.

## R9. The move check: moved, not changed

**Decision**: A script in the feature folder, `specs/013-split-large-modules/movecheck.py`, compares master's source
with the branch's, definition by definition.

- **What it compares.** Every top-level function, class and assignment.
- **Normalizing first.** References to project modules are reduced to the bare name, so `semantic.search`,
  `query.search` and `search` all compare equal.
- **Passing.** Each definition from master appears exactly once on the branch, with an equal syntax tree. The
  exceptions are listed in data-model.md, Section 3: language registration calls, the server's `__init__`, the CLI
  entry, and moved late imports.
- **Tests.** The same script compares test functions. Each master test appears once with an equal body. Fixture
  definitions merged into the shared setup are listed exceptions.

**Rationale**: This proves FR-001, FR-006 and FR-012 mechanically, for every definition rather than a sample. It runs
in seconds and needs no database.

**Alternatives considered**:
- Rely on the test suite alone: tests do not cover every line, and a dropped helper used on an untested path would
  pass.
- A text diff: lines move between files and import lines change, so the diff is noise.

## R10. The behavior baseline: same database state, run one after the other

**Decision**: A script, `specs/013-split-large-modules/baseline.py`, records the observable behavior. It is run on
master from a git worktree, with `.env` copied in and `PYTHONPATH` pointing at the worktree's `src`, and then on the
branch, one after the other on the same database. It records:

- the MCP tool listing (names, order, descriptions, input schemas);
- the output of a fixed set of about 130 `ccctx` commands;
- the parse output (chunks, calls, imports, docs) of every file of flask, gin and selenium-e2e and of the test
  fixtures;
- the language tables (R6);
- the stored rows after `ingest --full` and `wiki build` of one repository;
- `ccctx eval`.

It masks durations and timestamps, and leaves out memory facts, which change with every run.

**Rationale**: Search results depend on the database's index state, such as vector index rebuilds and text index
statistics. A comparison against an older recording can differ for reasons that have nothing to do with the code.
Running master and the branch one after the other removes that.

**Known effects of the database**:
- **Stale vector index.** On the freshly rebuilt Rancher database, ORA-51815 (HNSW vector index snapshot is too old)
  sometimes interrupts the eval tests.
- **Retry once.** A baseline step that hits it is retried once. The baseline only counts as a difference if master and
  the branch disagree.

## R11. The tests: mirrored folders, shared setup

**Folders.** The tests mirror the source folders: `tests/parsing/`, `tests/indexing/` and so on. Tests of the
top-level files stay in `tests/`. Test data stays in `tests/fixtures/`.

**File names.**
- A test file is named for the source file it tests: `tests/memory/test_runs.py` tests `memory/runs.py`.
- When one source file's tests exceed 300 lines, they split by concern as `test_<file>_<concern>.py`.

**Pytest settings.** `pyproject.toml` sets `addopts = "--import-mode=importlib"` and `pythonpath = ["tests"]`.
- **`importlib` mode.** Two folders may then hold test files of the same name.
- **Python path.** Every test file can `import support`, wherever it is.

**Shared setup.**
- **`tests/conftest.py`** holds what most files repeat: the database connection fixture, which skips with a reason when
  the database or the model is missing, and today's memory guard. The memory guard is retargeted to patch
  `memory.runs.record`.
- **`tests/support.py`** holds the plain helpers that are copied today: `git`, `commit`, `write_files` and
  `make_repo`.

**Expensive fixtures.** A fixture that builds and ingests a repository, used by several files of one split, moves to
that folder's `conftest.py`. There it gets `package` scope, so it is still built once, not once per new file.

**Rationale**:
- **`importlib` mode.** It is pytest's recommended mode for new layouts, and lets the names mirror the source without
  a prefix per folder.
- **`package` scope.** Without it, splitting `test_graph.py` (eight module-scoped fixtures) into three files would
  build the same repositories three times. The suite already takes 53 minutes on the Rancher database.

**Alternatives considered**:
- `__init__.py` in every test folder: works too, but makes the test folders packages for no other reason.
- Unique prefixed names such as `test_memory_runs.py`: these repeat the folder in every name.

## R12. Keeping the files small: a layout test

**Decision**: A new test file, `tests/test_layout.py`, fails when any of these does not hold:

- **Line limit.** Every `.py` file under `src/` and `tests/` is at most 300 lines. `tests/fixtures/` is exempt.
- **Opening docstring.** Every such file opens with a module docstring stating its purpose (FR-003).
- **README.** The README's Layout section lists exactly the source and test files on disk, no more and no fewer
  (FR-010). Each one-line purpose is also checked.

It is written first, and fails on master: 20 files are over the limit, and the README lists neither the new files nor
the test files. Each split then makes it pass for more files.

**Rationale**: FR-011 and FR-010 need a check that keeps working after this feature, or files grow again. A plain test
needs no new tool.

**Alternatives considered**:
- A linter rule for file length: it adds a dependency for one number.
- A pre-commit hook: it is easy to bypass and not run by the suite.

## R13. Version bump last

**Decision**: The version (`pyproject.toml` and `__init__.__version__`) goes from 1.4.0 to 1.4.1 as the last task,
after the baseline comparison.

**Rationale**: `memory.CONSOLIDATOR` is `f"memory/{__version__}"`, and it is stored with every fact. Bumping first
would make every stored fact differ in the comparison for a reason unrelated to the split.

## R14. Suite runtime

**Decision**: The full suite may take at most 10% longer than on master, measured one after the other on the same
database.

**Rationale**: More files mean more module-scoped fixtures. R11's `package` scope is how this is kept. On the Rancher
database the suite takes about 53 minutes today, so the comparison is made on the same machine.
