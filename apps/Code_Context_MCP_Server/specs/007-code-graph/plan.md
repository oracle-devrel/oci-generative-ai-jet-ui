# Implementation Plan: Code Relationship Graph

**Spec**: [code-graph.spec.md](./code-graph.spec.md) | **Research**: [research.md](./research.md)

**Scale note**: this touches about 13 files across five areas: parsing, ingest, schema, a new graph module, and the CLI and MCP surfaces. Watch two seams.
- **Ingest.** Symbol ids change on edit, so edges must be rebuilt from stored references, never kept.
- **Call resolution.** It is a name heuristic, and the module-qualified form (`flask.url_for`) is the common case in flask.

## Summary

Ingest already parses every Python, Go and JavaScript file with tree-sitter. The same parse now also yields each call (caller, called name, bare or attribute form, receiver, line) and each import. These are stored as references per file and replaced whenever the file is re-read. After every write, the repository's call and import edges are rebuilt from the references by a name-resolution pass, so an incremental graph always equals a full one.

Migration 6 adds the reference and edge tables and `ccctx_graph`, a property graph whose vertices are `ccctx_files` and `ccctx_symbols`. The `defines` edge is `ccctx_symbols.file_id` itself. A new `graph.py` answers callers, calls and depth-limited impact with `GRAPH_TABLE … MATCH` queries. These are exposed as `ccctx callers`, `ccctx calls` and `ccctx impact`, and as MCP tools of the same names.

## Project Structure

```text
src/golestan_code_mcp/
  chunker.py    parse(): chunks plus calls and imports from one tree
  schema.py     migration 6: ref and edge tables, extract_version, ccctx_graph
  ingest.py     store refs per re-read file, rebuild edges, extract_version refresh
  graph.py      NEW: resolve refs to edges; callers, calls, impact via GRAPH_TABLE
  cli.py        callers, calls, impact commands
  server.py     callers, calls, impact MCP tools
tests/
  test_chunker.py   call and import extraction per language, comments and docstrings ignored
  test_schema.py    migration 6 tables and the property graph
  test_graph.py     NEW: resolution rules, callers, calls, impact hops and cycles, repo scoping, refusals
  test_ingest.py    refs replaced on re-read, incremental graph equals full, version refresh without re-embed
  test_cli.py       command output and refusals
  test_server.py    the three tools match the core; tool list updated
README.md           "Code relationships" section
```

**Structure Decision**: resolution and queries live together in `graph.py`. Extraction stays in `chunker.py`, beside the parse it reuses. Ingest only stores references and calls `graph.rebuild`.

## Constitution Check

| Principle | Assessment |
|---|---|
| I. Database-Native Intelligence | PASS. Relationships live in the same database as a SQL property graph over the existing tables. There is no separate graph store and no copy. |
| II. Structure-Aware Ingestion | PASS. Calls and imports come from the real parse tree. Re-ingestion stays incremental: references are replaced only for re-read files, and stale edges cannot survive because edges are rebuilt from references. |
| III. MCP as the Single Interface | PASS. `callers`, `calls` and `impact` are MCP tools on the same core as the CLI. Every result carries repository, path and lines. Adding tools is not a breaking change. |
| IV. Hybrid, Explainable Retrieval | PASS. Ranking is untouched. Impact reports its distance, which is the explanation the request asks for. |
| V. Self-Improvement with Provenance | PASS. No notes yet. |
| VI. Measured Quality (Test-First) | PASS. Extraction, resolution, queries and the incremental-equals-full property get integration tests against the database first. Each new MCP tool gets a contract test. |
| VII. Safety & Simplicity | PASS. Parsing is read-only. One deliberate simplification is recorded in research: edges are rebuilt for the whole repository on each ingest. |

Re-checked after design: unchanged.

## Verifying the success criteria

- **SC-001 and SC-002**: a script classifies every `grep -rn "url_for"` hit in flask as a call in Python code, or as a comment, docstring, docs or template. Compare it with `ccctx callers url_for`: recall must be at least 90%, and zero non-code hits may appear.
- **SC-003**: compare `ccctx impact url_for --depth 1 | wc -l` with `--depth 3`.
- **SC-004**: time each command against the flask and gin index.
- **SC-005**: `test_ingest` compares `ccctx_calls` and `ccctx_imports` (by names and paths, not ids) after incremental and full ingests.
- **SC-006**: `test_server` compares each tool with the core function.
