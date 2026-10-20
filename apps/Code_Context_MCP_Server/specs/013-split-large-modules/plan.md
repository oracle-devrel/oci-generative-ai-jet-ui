# Implementation Plan: Split Large Modules

**Branch**: `013-split-large-modules` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/013-split-large-modules/spec.md`

## Summary

Nine source files are 364 to 916 lines long, and eleven test files are 341 to 930. This feature splits them into
files of at most 300 lines, each holding one concern, grouped into eight area folders: `parsing`, `indexing`,
`search`, `graph`, `wiki`, `memory`, `server` and `cli`. The tests mirror the same folders.

The split is a move, not a rewrite:
- **One home per name.** Every name keeps its name and lives in exactly one file. Package `__init__.py` files
  re-export nothing (research R2).
- **Imports.** Callers reach functions through their module, so the tests' patches still hit what the code calls
  (research R4).
- **Installed commands.** The entry-point strings are unchanged (research R3).

Three checks prove nothing else changed:
- **Move check.** A script compares every definition of master and the branch by syntax tree (R9).
- **Behavior baseline.** It records tools, CLI output, parse output, stored rows and eval, with master and the branch
  run one after the other on the same database (R10).
- **Layout test.** It keeps the files small and the README's layout list correct (R12).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: no new ones. The existing ones are `python-oracledb`, `tree-sitter` with its grammars,
`mcp` (FastMCP) and `oracleagentmemory`. `pytest-randomly` is used once, through `uv run --with`, without being
added.

**Storage**: Oracle AI Database 26ai, unchanged: same schema version 10, no migration.

**Testing**: pytest. It gains `--import-mode=importlib` and `pythonpath = ["tests"]` (research R11), and a new
`tests/test_layout.py`.

**Target Platform**: Windows and Linux developer machines, with the database in a container (Rancher Desktop here).

**Project Type**: a single Python package, with a CLI and an MCP server over stdio.

**Performance Goals**: none new. The test suite may take at most 10% longer than master's, measured on the same
database (research R14).

**Constraints**:
- **Behavior frozen.** Behavior stays identical (spec FR-001).
- **No reinstall.** Existing installs and MCP registrations keep working without `uv sync` (FR-008).
- **Size.** No file over 300 lines.

**Scale/Scope**:
- **Source.** 16 files and 6,075 lines become 69 files (63 in eight folders, 6 at the top level).
- **Tests.** 17 files and 7,516 lines become about 65 files.
- **Size of the work.** 554 top-level definitions move, and 42 test patches are retargeted.

## Constitution Check

*GATE: checked before Phase 0 research, and again after Phase 1 design.*

| Principle | Effect | Status |
|---|---|---|
| I. Database-Native Intelligence | Nothing new is sent anywhere. Indexing and memory code move unchanged. | Pass |
| II. Structure-Aware Ingestion | The chunker's rules move file by file. The baseline compares the parse output of every file of three repositories and the fixtures, and the language tables, key by key in order (R6, R10). | Pass |
| III. MCP as the Single Interface | Same nine tools in the same order, with the same schemas and results (contracts/interfaces.md). Every tool keeps its contract tests, moved to `tests/server/`. | Pass |
| IV. Hybrid, Explainable Retrieval | Ranking code moves unchanged. The quality gate requires the retrieval evaluation when ranking or chunking code changes: `ccctx eval` is part of the baseline, and must match master's on the same database. | Pass |
| V. Self-Improvement with Provenance | Memory code moves unchanged. Facts keep their provenance. The version bump comes last, so stored consolidator values change only with it (R13). | Pass |
| VI. Measured Quality (Test-First) | The new layout test is written first and fails on master: 20 files over the limit. The existing suite, moved, is the regression net; the move check proves that no test was dropped or weakened (R9). | Pass |
| VII. Safety & Simplicity | No abstraction layer, plugin system or new dependency. Folders hold plain files, `__init__.py` files are empty apart from two entry points, and `register()` already exists. The late import that fills the language tables is today's pattern, kept (R6). | Pass |

**Re-check after Phase 1**: Pass. The design adds folders and files, not layers. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/013-split-large-modules/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R14: layout, imports, cycles, ordering, move check, baseline
├── data-model.md        # the module map: where each definition and test goes
├── quickstart.md        # how to validate
├── contracts/
│   ├── interfaces.md    # what must not change
│   └── conventions.md   # the layout rules
├── checklists/requirements.md
├── movecheck.py         # created by /speckit-implement (R9)
├── baseline.py          # created by /speckit-implement (R10)
├── moves.md             # created by /speckit-implement (data-model Section 4)
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/golestan_code_mcp/
├── __init__.py  config.py  db.py  registry.py  samples.py  schema.py    # unchanged apart from imports
├── parsing/      tables.py  common.py  chunks.py
│   └── languages/   python.py  go.py  javascript.py  csharp.py  typescript.py  c_family.py
│                    java.py  kotlin.py  rust.py  php.py  ruby.py  swift.py
├── indexing/     files.py  write.py  ingest.py
├── search/       model.py  candidates.py  ranking.py  query.py  feedback.py  evaluation.py
├── graph/        imports.py  build.py  queries.py
├── wiki/         text.py  compile.py  store.py  build.py  read.py
├── memory/       store.py  runs.py  findings.py  distill.py  consolidate.py  recheck.py  recall.py
├── server/       __main__.py  app.py  search_tools.py  graph_tools.py  wiki_tools.py
│                 repository_tools.py  memory_tools.py
└── cli/          __main__.py  format.py  index_commands.py  search_commands.py  wiki_commands.py
                  memory_commands.py  parser.py  main.py

tests/
├── conftest.py  support.py  test_layout.py
├── test_config.py  test_db.py  test_registry.py  test_samples.py
├── test_schema.py  test_schema_graph.py  test_schema_wiki.py  test_schema_memory.py
├── fixtures/                                   # unchanged
├── parsing/      test_tables.py  test_chunks.py
│   └── languages/   test_<language>.py, one per language file
├── indexing/     conftest.py  test_files.py  test_write.py  test_ingest*.py
├── search/       test_model.py  test_candidates.py  test_ranking.py  test_query.py  test_feedback*.py
│                 test_evaluation.py
├── graph/        conftest.py  test_imports.py  test_build.py  test_queries.py
├── wiki/         test_text.py  test_compile.py  test_store.py  test_build.py  test_read.py
├── memory/       test_runs.py  test_findings.py  test_distill.py  test_consolidate.py  test_recheck.py
│                 test_recall.py
├── server/       test_app.py  test_search_tools.py  test_graph_tools.py  test_wiki_tools.py
│                 test_repository_tools.py  test_memory_tools.py
└── cli/          test_format.py  test_index_commands.py  test_search_commands.py  test_wiki_commands.py
                  test_memory_commands.py  test_parser.py  test_main.py
```

Every area folder has an `__init__.py` holding its docstring. `cli/` and `server/` also expose `main`. The test
folders have no `__init__.py`; they rely on `importlib` mode (R11).

**Structure Decision**: one package with area subpackages (research R1). [data-model.md](data-model.md) gives each
file's contents and estimated size, and the test grouping.

### Order of work

1. **Guards first.** The layout test (failing), the move check, the behavior baseline recorded on master, and the
   shared test setup (`conftest.py`, `support.py`, pytest settings), with the current tests moved onto it.
2. **Source, one area at a time**, from the leaves up, so each step leaves a working tree:
   1. `parsing`
   2. `indexing`'s helpers
   3. `search`
   4. `graph`
   5. `wiki`
   6. `memory`
   7. `indexing/ingest.py`
   8. `server`
   9. `cli`

   After each area: retarget imports and patches, run that area's tests and the import check, then run the move
   check.
3. **Tests, one area at a time**, into the mirrored folders, keeping each file under the limit.
4. **Documentation.** The README Layout section, and the move record.
5. **Verification.** The full baseline comparison against master on the same database, the full and random-order
   suite, and the runtime comparison. Then the version bump to 1.4.1, last (R13).

## Complexity Tracking

Empty: no Constitution Check violation needs justifying.
