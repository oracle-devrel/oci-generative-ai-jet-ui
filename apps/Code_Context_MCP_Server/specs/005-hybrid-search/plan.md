# Implementation Plan: Hybrid Code Search

**Branch**: `005-hybrid-search` | **Date**: 2026-10-11 | **Spec**: [hybrid-search.spec.md](./hybrid-search.spec.md)

## Summary

One hybrid vector index replaces step 4's embedding column and HNSW index.

- **Index and text**: the index is created by `ccctx model load` over a new `ccctx_symbols.search_text` column (kind, name, path and source) with `MODEL ALL_MINILM_L12_V2 VECTOR_IDXTYPE HNSW SYNC (ON COMMIT)`. It serves both keyword and semantic matching, and a committed ingest is searchable at once. Migration 4 adds and backfills `search_text`, so symbols stored before this step become searchable without re-ingesting, and drops the old embedding column and its index.
- **Query**: `semantic.search(conn, question, repos, mode, env)` calls `DBMS_HYBRID_VECTOR.SEARCH` with `search_scorer` `RRF` and `search_fusion` `UNION` in hybrid mode, the vector side alone in vector mode, and the text side alone in text mode. The text side is built from the question's words, each escaped in braces and joined with AND.
- **Ranking**: candidates are mapped back to symbols by rowid and filtered to the chosen repositories. Symbols whose name, or its last dotted part, equals an identifier query are put first. The list is capped at 10.
- **Interfaces**: `ccctx search` gains `--mode` and a repeatable, comma-separated `--repo`. The MCP tool gains `mode` and `repos` and keeps `repo`.

## Technical Context

- **Probed on the running database** (23.26.3):
  - The app user can create a hybrid vector index.
  - `DBMS_HYBRID_VECTOR.SEARCH` returns a LOB of JSON rows with `rowid`, `score`, `vector_score`, `text_score`, `vector_rank`, `text_rank`, `chunk_text` and `chunk_id`.
  - Text-only and vector-only requests work. `score_weight` per side is accepted and changes the fused order.
  - `{term}` searches a term literally. Without braces `_` acts as a wildcard and `url_for` matches nothing.
  - `for` is a stopword.
  - With the default index, a committed row is not searchable until a sync. `SYNC (ON COMMIT)` or `ctx_ddl.sync_index` fixes that.
  - A `filter_by` key is rejected, so repository filtering happens after the search.
- **No new dependency.**
- **Performance**: under 2 s per search (SC-007). Each search asks for `CCCTX_SEARCH_CANDIDATES` rows (default 100), so repository filtering and the definition boost have enough rows to work with.

## Constitution Check

| Principle | Assessment |
|---|---|
| I. Database-Native Intelligence | PASS. Keyword and semantic matching both run inside Oracle from one index, vectorized in the database with the same ONNX model. |
| II. Structure-Aware Ingestion | PASS. Each indexed row is one syntactic chunk. Its searchable text adds kind, name and path to the source. |
| III. MCP as the Single Interface | PASS. The CLI and the MCP tool both call `semantic.search`. The tool only gains optional inputs (`mode`, `repos`) and additive output fields. |
| IV. Hybrid, Explainable Retrieval | PASS, closing step 4's justified violation. The default search fuses keyword and semantic results with RRF. Each result shows its fused score and its keyword and semantic ranks. `CCCTX_TEXT_WEIGHT` and `CCCTX_VECTOR_WEIGHT` are configurable, with defaults of 1 documented in the README. |
| V. Self-Improvement with Provenance | PASS. No learned state in this step. |
| VI. Measured Quality (Test-First) | PASS. Tests for each mode, the definition boost, repository scoping, escaping, sync-on-commit and the tool contract come first. The step 4 questions plus `url_for` and 10 defined identifiers are the evaluation set (SC-002). |
| VII. Safety & Simplicity | PASS. One index replaces two mechanisms. Migration 4 is ordered and re-runnable. The dropped embedding column is derived data that the index recomputes. |

Re-checked after Phase 1 design: unchanged.

## Project Structure

```text
src/golestan_code_mcp/
  config.py        # + search_candidates, text_weight, vector_weight
  schema.py        # + migration 4: drop HNSW index and embedding column, add + backfill search_text
  semantic.py      # hybrid index in _state/require_model/load_model; search(conn, question, repos, mode, env)
  ingest.py        # insert search_text (CLOB) instead of VECTOR_EMBEDDING
  cli.py           # search --mode, --repo (repeatable, comma-separated), new result columns
  server.py        # search tool: mode, repos (+ repo kept), score and rank fields
tests/
  test_config.py, test_schema.py, test_semantic.py, test_ingest.py, test_cli.py, test_server.py
README.md          # modes, --repo, weights, re-run of ccctx model load
```

**Structure Decision**: `semantic.py` stays the single owner of the model, the index and the query. The CLI and MCP tool only parse arguments and format results.

## Success Criteria Verification

| Criterion | How it is checked |
|---|---|
| SC-001 | Walkthrough: `ccctx search "url_for"` puts a definition at rank 1, and both definitions come before any call site. A test checks the same on a throwaway repository. |
| SC-002 | Walkthrough script over 10 defined identifiers from flask and gin. |
| SC-003 | Walkthrough: the routing question in hybrid mode returns flask and gin routing code in the top 10. |
| SC-004 | `test_semantic` with two throwaway repositories, plus the walkthrough with `--repo gin`. |
| SC-005 | Walkthrough: the sourdough question returns 3 or fewer. |
| SC-006 | `test_semantic` text mode, plus the walkthrough. |
| SC-007 | Time the walkthrough searches. |
| SC-008 | `test_server` compares the tool with `semantic.search`. |
