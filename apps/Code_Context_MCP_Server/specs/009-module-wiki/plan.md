# Implementation Plan: Module Wiki

**Branch**: `009-module-wiki` | **Date**: 2026-10-11 | **Spec**: [spec.md](./spec.md)

## Summary

A new `wiki` module compiles one Markdown page per directory with at least 10 named definitions. It writes the page from the index alone:
- the docstrings and doc comments the chunker now stores;
- the key symbols, ranked by their callers in the code graph;
- the import edges, grouped by directory.

Each page's citations are rows with foreign keys to `ccctx_symbols` and `ccctx_files`, set to null when the record goes away. Each citation records the cited symbol's commit and content hash. An ingestion compares the recorded commits with the stored ones and marks pages stale inside its own transaction. After committing, it recompiles those pages in a second transaction.

Pages get their own table and their own hybrid vector index. Search runs the same request against that index. It places each matching page above the first symbol hit whose semantic similarity is lower than the page's, so a question about a module lands on its page and an identifier still lands on its definitions. `ccctx wiki build|list|show|citations` and a `read_wiki` MCP tool read the pages. The server moves to 1.1.0.

## Project Structure

```text
src/golestan_code_mcp/
├── wiki.py        # new: naming, compile, store, mark stale, recompile, read
├── schema.py      # migration 7: doc columns, wiki tables, repos.wiki_at
├── chunker.py     # Chunk.doc and the file's doc, for Python and Go
├── ingest.py      # store docs, EXTRACT_VERSION 2, mark stale in the transaction, recompile after commit
├── graph.py       # external_imports: the import refs that resolve to no indexed file
├── semantic.py    # the page index (load and require), page hits merged into search
├── cli.py         # wiki build|list|show|citations, wiki lines in the ingest summary, page rows in search
├── server.py      # read_wiki, page hits in search_code, 1.1.0
└── __init__.py    # 1.1.0
tests/
├── test_wiki.py      # new: compile, citations, staleness, recompile, naming
├── test_chunker.py   # docs
├── test_ingest.py    # docs stored, stale marked, recompiled, summary
├── test_semantic.py  # page hits, filters, ordering
├── test_cli.py       # wiki commands, search page rows
└── test_server.py    # read_wiki contract, page hits
README.md, pyproject.toml, uv.lock
```

**Structure Decision**: The wiki gets one new module, because it is a new capability with its own tables. It is called from `ingest.py`, `semantic.py`, `cli.py` and `server.py`, the way `graph.py` is.

## Constitution Check

| Principle | Assessment |
|---|---|
| I. Database-native intelligence | PASS. Pages are compiled from the index by local code, with no language model and no outside service. The database embeds them, using the model already loaded. |
| II. Structure-aware ingestion | PASS. Docs come from the same tree-sitter parse. `EXTRACT_VERSION` 2 re-reads every file once and keeps every unchanged symbol, so nothing is re-embedded. |
| III. MCP as the single interface | PASS. `read_wiki` is added and `search_code` gains page hits, both additive, so the version is 1.1.0 (MINOR). The CLI calls the same `wiki` functions. Every result is bounded. Page hits carry a repository and directory, and their citations carry a path and line range. A page hit's own line range is null, because a page has no lines in the code (research R9). |
| IV. Hybrid, explainable retrieval | PASS. Page hits come from the same hybrid query with the same weights. They show their keyword rank, semantic rank and similarity, and the similarity is what places them. |
| V. Self-improvement with provenance | PASS. Each page records its author (compiler and version) and compile time. Each citation records the commit and content hash it was compiled against. Changed code marks a page stale instead of serving it as current. No source is ever altered. |
| VI. Measured quality | PASS. Tests are written first: a contract test for `read_wiki` and integration tests against the database. The retrieval evaluation is rerun, because ranking changes. |
| VII. Safety and simplicity | PASS. Indexed code is only read. The live staleness check edits a scratch clone, never `../ccctx-repos`. One module, two tables and one index are added, with no plugin or generator abstraction. |

Re-checked after Phase 1: no change. The second hybrid index lives in the same database and uses the same model, so it adds no infrastructure.

## Phase 0 and Phase 1

- [research.md](./research.md): the decisions behind the plan (R1 to R11).
- [data-model.md](./data-model.md): the tables and columns.
- [contracts/cli.md](./contracts/cli.md), [contracts/tools.md](./contracts/tools.md): the commands, outputs and the `read_wiki` tool.
