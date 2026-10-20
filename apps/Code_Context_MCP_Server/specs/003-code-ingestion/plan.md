# Implementation Plan: Code Ingestion and Chunking

**Branch**: `003-code-ingestion` | **Date**: 2026-10-10 | **Spec**: [code-ingestion.spec.md](./code-ingestion.spec.md)

## Summary

`ccctx ingest <name>` lists the repository's files through read-only git commands. That gives `.gitignore` handling, nested ignore files included, the same way git applies it. It then skips vendored, oversized, binary and symlinked files, and hands each remaining file to a new `chunker` module. The chunker uses tree-sitter to cut Python, Go and JavaScript at definition boundaries, and falls back to 60-line windows every 50 lines when a file has no grammar or has a syntax error. A new `ingest` module replaces the repository's files and symbols in one transaction, stamping every symbol with the HEAD commit (migration 2 adds `commit_sha`). It returns a summary that the CLI prints and logs. `ccctx symbols` and `ccctx stats --by-language` read the result back. The one new dependency is `tree-sitter-javascript`.

## Technical Context

- **Language**: Python 3.11, uv project.
- **Dependencies**: `tree-sitter` 0.26 with `tree-sitter-python` and `tree-sitter-go` 0.25, already installed. Adds `tree-sitter-javascript>=0.25`. Uses `git` on PATH, already a phase 1 prerequisite.
- **Storage**: Oracle tables from step 2, plus `ccctx_symbols.commit_sha` from migration 2.
- **Testing**: pytest. Parser tests use fixtures and need no database. Ingest tests build throwaway git repositories under `tmp_path` and skip their database half when the database is down.
- **Performance**: ingest flask and gin in under 60 s each (SC-001). Each file gets one insert. Symbols go in one `executemany` per run, with `source` bound as a CLOB.
- **Constraints**: read-only toward the repository. Git runs with `core.fsmonitor` disabled and without optional locks, so it neither writes `.git` nor runs a program configured by the repository.

## Constitution Check

| Principle | Assessment |
|---|---|
| I. Database-Native Intelligence | PASS. Chunks are stored in Oracle. Nothing leaves the machine. |
| II. Structure-Aware Ingestion | PASS. Chunks follow tree-sitter definitions. Fallback windows are only for files with no grammar or a syntax error, and are flagged as `chunk`. Each chunk carries repository (via file), path, language, name, kind, line range and content hash. This step replaces a repository's index in full on each run. Incremental, hash-aware re-ingestion is step 5, and `commit_sha` is the hook for it. |
| III. MCP as the Single Interface | PASS. Ingestion and inspection are CLI administration, which the constitution allows. The CLI calls `ingest` and `chunker`, which the MCP server can reuse. Symbol lookup over MCP arrives with search. |
| IV. Hybrid, Explainable Retrieval | PASS. No retrieval in this step. |
| V. Self-Improvement with Provenance | PASS. No learned state in this step. |
| VI. Measured Quality (Test-First) | PASS. Chunker fixture tests, ingest tests with temporary repositories, and CLI output tests are written before the code. |
| VII. Safety & Simplicity | PASS. Files are only read. Git runs read-only with repository-configured programs disabled. `.gitignore` plus a configurable vendored list are honoured, and binaries are skipped. Each run emits one structured log record. Migration 2 is ordered and re-runnable. |

Re-checked after Phase 1 design: still PASS.

## Project Structure

```text
pyproject.toml                        # + tree-sitter-javascript
src/golestan_code_mcp/
  config.py                           # + max_file_bytes(env), vendor_dirs(env)
  schema.py                           # + migration 2 (commit_sha); ORA-01430/02264 tolerated
  registry.py                         # + get_repo(conn, name) -> (id, path)
  chunker.py                          # new: language detection, tree-sitter chunking, line windows
  ingest.py                           # new: discover files, skip rules, store in one transaction, summary
  cli.py                              # + ingest, symbols, stats; generalised format_table
tests/
  fixtures/sample.py, sample.go       # extended with methods, struct/interface, grouped types
  fixtures/sample.js, broken.py       # new
  test_chunker.py                     # replaces test_parser.py
  test_ingest.py                      # new: temp git repos, skip reasons, commit, replace, rollback
  test_schema.py                      # + migration 2; add_symbol passes commit_sha
  test_cli.py                         # + ingest summary, symbols and stats output
README.md                             # ingest, symbols, stats
```

**Structure Decision**: `chunker` is pure, with no database and no file system, so it can be tested on bytes. `ingest` owns the file system walk and the database writes. `cli` only parses arguments and formats output.

## Success Criteria Verification

| Criterion | How it is checked |
|---|---|
| SC-001 | Time `ccctx ingest flask` and `ccctx ingest gin`. |
| SC-002 | A test picks 10 random parsed symbols from the live index and checks each range against the file: first line is the definition or its decorator, last line closes it, and the stored source equals those lines. |
| SC-003 | `test_chunker` compares each fixture's full `(name, kind, start, end)` set. |
| SC-004 | `test_chunker` windows a 130-line input into 1-60, 51-110 and 101-130. |
| SC-005 | `test_ingest` ingests twice and compares counts. |
| SC-006 | `test_ingest` checks every symbol's `commit_sha` equals `git rev-parse HEAD`. |
| SC-007 | `test_ingest` checks scanned = indexed files + skipped, and indexed symbols = rows stored. |
| SC-008 | `test_ingest` asserts no stored path is under `.git`, a vendored directory or a gitignored path. |
