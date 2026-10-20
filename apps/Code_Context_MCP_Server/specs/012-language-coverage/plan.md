# Implementation Plan: Language Coverage

**Branch**: `012-language-coverage` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/012-language-coverage/spec.md`

## Summary

Teach the chunker ten more languages at the level of Python, Go and JavaScript: TypeScript, TSX, C#, C, C++, Java,
Kotlin, Rust, PHP, Ruby and Swift. For each it extracts named definitions, doc comments, calls and imports. Each
language gets the same four pieces the existing three have:
- a walker for definitions
- a call extractor
- an import extractor
- a doc reader

They sit in one new module, `languages.py`, and register into the chunker's existing tables, so the chunker's shared
machinery and the three existing languages are untouched (FR-017).

The graph learns each language's import resolution. Most are path rules (Java packages, C includes, Rust modules,
Ruby `require_relative`, PHP's PSR-4). C# `using` resolves through the namespaces each file declares, recorded at
ingest.

The wiki ranks key symbols by a per-symbol `exported` flag computed at parse time, because C#, Java and Ruby
visibility can't be read from a name.

Existing indexes convert on the next ordinary ingest: an unchanged file is re-read when its stored language differs
from the language it is assigned now (FR-016). For every newly supported extension, that's exactly the files that
were `text` before.

Every grammar is a prebuilt package that runs locally: no network, no compiler (constitution I). All ten load under
the pinned `tree-sitter` 0.25 (research R1).

## Technical Context

**Language/Version**: Python 3.11 (unchanged).

**Primary Dependencies**: existing `tree-sitter` 0.25 (pinned below 0.26, which crashes on Windows). New grammar
packages, versions verified in research R1:
- `tree-sitter-typescript` 0.23 (TypeScript and TSX)
- `tree-sitter-c-sharp` 0.23
- `tree-sitter-c` 0.24
- `tree-sitter-cpp` 0.23
- `tree-sitter-java` 0.23
- `tree-sitter-kotlin` 1.1
- `tree-sitter-rust` 0.24
- `tree-sitter-php` 0.25
- `tree-sitter-ruby` 0.23
- `tree-sitter-swift` 0.7

**Storage**: Oracle AI Database 26ai. Migration 10, "language coverage":
- `ccctx_files.namespaces`: JSON, null. The namespaces a file declares (C#).
- `ccctx_symbols.exported`: boolean, null. Backfilled for existing symbols by today's name rule, so flask and gin
  wiki pages are unchanged.

**Testing**: pytest against the local database, as for 001–011. Rules are tested on inline sources per language in
`test_languages.py`. A fixture repository with every language goes through ingest, the graph and the wiki in
`test_ingest.py` and `test_graph.py`. The existing gold set and identifier evaluation must hold (SC-005).

**Target Platform**: Windows 11 developer machine (also Linux). All grammar packages ship prebuilt wheels.

**Project Type**: single Python package (MCP server and CLI).

**Performance Goals**: ingesting flask and gin from scratch takes at most 10% longer (SC-006). Grammars load lazily,
on the first file of their language, so a repository that has none of a language never loads it.

**Constraints**:
- **Shapes**: no tool or CLI result shape changes (FR-018).
- **Existing languages**: Python, Go and JavaScript are indexed exactly as before (FR-017).
- **Server**: never parses code. Only ingest does, so lazy grammar loading can't hit the Windows stdio import hang
  found in 011.

**Scale/Scope**: ten languages, each with a walker, a call extractor, an import extractor and a doc reader. There are
11 grammars, because TypeScript and TSX are separate. Fixtures cover the constructs the acceptance scenarios list.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan satisfies it | Status |
|---|---|---|
| I. Database-Native Intelligence | Grammars run locally in-process. No code or text leaves the machine, and parsing uses no network (FR-019). Embedding is unchanged. | PASS |
| II. Structure-Aware Ingestion | This feature exists for II: ten languages move from line windows to syntactic chunks. A file that doesn't parse falls back to windows, flagged and counted (FR-006). Chunks carry repo, path, language, name, kind, lines and hash, as today. Re-ingestion stays incremental: only files whose language gained rules are re-read (FR-016). | PASS |
| III. MCP as the Single Interface | No tool's name, input or output shape changes. Only the `language` values grow, and descriptions listing them are updated. Server 1.4.0 (MINOR). The CLI keeps calling the same core. | PASS |
| IV. Hybrid, Explainable Retrieval | Ranking is untouched. New definitions are embedded and fused like any other. | PASS |
| V. Self-Improvement with Provenance | Memory and feedback are unchanged. A window that becomes definitions is removed code to them: its facts go stale and its feedback boosts nothing (US3, scenario 3). | PASS |
| VI. Measured Quality (Test-First) | Each language's rules get failing tests first, then the fixture repository through ingest, graph and wiki. Every tool's contract test still passes. The gold set and the identifier evaluation must hold at 0.90 and 10/10 (SC-005). | PASS |
| VII. Safety & Simplicity | Indexing stays read-only: files are parsed, never run or imported. One new module holds the new languages as entries in the chunker's existing tables, so there is no plugin system and no class hierarchy. The two new columns each answer one requirement. | PASS |

**Post-design re-check**: still PASS. The design adds no tool, no endpoint and no new kind of storage beyond two
nullable columns. Its one judgment call is C# namespace resolution (research R6), which FR-013 calls best effort.

## Project Structure

### Documentation (this feature)

```text
specs/012-language-coverage/
├── plan.md              # this file
├── research.md          # Phase 0: grammars, naming, re-indexing, resolution, docs, visibility
├── data-model.md        # Phase 1: migration 10, chunk and import shapes, language table
├── quickstart.md        # Phase 1: live checks (fixtures, Selenium-E2E, flask/gin unchanged)
├── contracts/
│   ├── cli.md           # ingest summary's Reparsed line, search --language values
│   └── tools.md         # search_code language values; server 1.4.0
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
pyproject.toml                    # ten grammar dependencies; version 1.4.0
src/golestan_code_mcp/
├── __init__.py                   # __version__ 1.4.0
├── chunker.py                    # EXTENSIONS and file names; Chunk.exported; parse() returns namespaces; lazy
│                                 #   grammar loading; tables extended from languages.py
├── languages.py                  # NEW: walkers, call, import and doc rules, and visibility for the ten languages
├── schema.py                     # migration 10 (namespaces, exported + backfill)
├── ingest.py                     # stored-language re-read rule; Summary.reparsed; store namespaces and exported
├── graph.py                      # import resolution per new language; outside imports; self receivers
├── wiki.py                       # language names, exported from the stored flag, test-file patterns
├── cli.py                        # ingest summary's Reparsed line
└── server.py                     # descriptions list the new language values
tests/
├── test_languages.py             # NEW: per-language definitions, names, kinds, docs, calls, imports, exported
├── test_chunker.py               # parse() shape; existing languages unchanged
├── test_ingest.py                # fixture repository with all languages; re-read of language-gained files
├── test_graph.py                 # callers and imports across the new languages
├── test_wiki.py                  # a page for a C# folder; exported ranking
├── test_schema.py                # migration 10
├── test_semantic.py              # LANGUAGES list
├── test_cli.py                   # Reparsed line; --language values
└── test_server.py                # language values in the contract
```

**Structure Decision**: The existing single package gains one module. The new languages live in `languages.py` as
functions and dicts merged into the chunker's `GRAMMARS`, `WALKERS`, `CALLS`, `IMPORTS` and `SYMBOL_DOCS`, the same
way the three existing languages are registered. Python, Go and JavaScript stay where they are, unchanged.

## Complexity Tracking

No constitution violations. Two choices are worth noting:

| Choice | Why | Simpler alternative rejected because |
|---|---|---|
| `languages.py`, a second module beside `chunker.py` | About 900 lines of per-language rules would double `chunker.py` and bury its shared machinery | One module per language: ten files of one pattern each, for no benefit in reading or testing |
| A stored `exported` flag (migration 10) | C#, Java, Kotlin, Swift, PHP and Ruby visibility is in modifiers or `private` sections, not in the name. The parser sees them; the wiki doesn't load source | A regex over each symbol's source at wiki compile time: it would load every symbol's source and still can't see Ruby's `private` sections |
