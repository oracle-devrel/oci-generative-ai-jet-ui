# Implementation Plan: Semantic Code Search

**Branch**: `004-semantic-search` | **Date**: 2026-10-11 | **Spec**: [semantic-search.spec.md](./semantic-search.spec.md)

## Summary

A new `semantic` module owns the model and the search.

- **Model setup**: `ccctx model load` downloads Oracle's prebuilt `all_MiniLM_L12_v2.onnx` once into a git-ignored cache, uploads it to the database as a BLOB and loads it with `DBMS_VECTOR.LOAD_ONNX_MODEL` as `ALL_MINILM_L12_V2`. It then records the model and its dimension, and builds the HNSW cosine index.
- **Embeddings**: migration 3 adds a nullable `VECTOR(384, FLOAT32)` column. Ingest fills it inside its existing insert with `VECTOR_EMBEDDING`, from the symbol's kind, name, path and source, so the text never leaves the database to be embedded.
- **Search**: `ccctx search` and a new MCP `search` tool share one query. It embeds the question in the database, takes the 10 approximate nearest neighbours by cosine distance, and keeps those with similarity 0.3 or more.
- **Database setting**: a new startup script enables the vector memory pool. The probe showed it cannot be raised on a running database (ORA-51950), so it is written to the server parameter file and the instance restarts once.

## Technical Context

- **Language**: Python 3.11, uv project. No new Python dependency: the download uses `urllib.request`.
- **Storage**: Oracle AI Database 26ai Free (23.26.3). The app user already has `CREATE MINING MODEL`, but `vector_memory_size` is 0 today.
- **Model file**: 133,322,334 bytes from Oracle's object storage (`OML-ai-models/all_MiniLM_L12_v2.onnx`). The URL can be overridden with `CCCTX_MODEL_URL`.
- **Testing**: pytest. Tests that need embeddings skip with a reason when the model is not loaded, just as database tests skip when the database is down.
- **Performance**: search answers in under 2 s (SC-006) through the in-memory HNSW index. Ingest of flask or gin with embeddings must finish in under 5 min (SC-007), with embedding cost paid by the database per inserted row.

## Constitution Check

| Principle | Assessment |
|---|---|
| I. Database-Native Intelligence | PASS. The ONNX model runs inside Oracle. Embeddings are computed by `VECTOR_EMBEDDING` in SQL, and no API key is involved. The only network call downloads the published model file, and it carries no code. |
| II. Structure-Aware Ingestion | PASS. Each embedding is attached to an existing syntactic chunk. Fallback chunks keep kind `chunk` and are labelled as such in results. |
| III. MCP as the Single Interface | PASS. A `search` MCP tool returns the same results as the CLI, both through `semantic.search`. Results are structured, capped at 10, and carry repository, path and line range. |
| IV. Hybrid, Explainable Retrieval | **Justified violation**, see Complexity Tracking. Search here is semantic only. Each result exposes its semantic similarity score. |
| V. Self-Improvement with Provenance | PASS. No learned state in this step. |
| VI. Measured Quality (Test-First) | PASS. Tests for the model check, embedded inserts, search ranking and floor, the CLI and the MCP tool contract come first. The evaluation set starts with the two questions in the request. |
| VII. Safety & Simplicity | PASS. The model name and dimension are recorded in `ccctx_embedding_model`, and ingest refuses on a mismatch, so vectors from two models never mix. Migration 3 is ordered and re-runnable. There is one new module. |

### Complexity Tracking

| Violation | Why needed | Simpler alternative rejected |
|---|---|---|
| Default search is semantic only, not fused keyword + semantic (IV) | This step's request asks for semantic search and its tests check that behaviour. Keyword fusion needs its own design (Oracle Text index, rank fusion, weights). | Adding a quick keyword half now would ship untuned, undocumented weights. Each result already carries its semantic score, so fusion can add the keyword score alongside it. |

Re-checked after Phase 1 design: unchanged.

## Project Structure

```text
compose.yaml                          # unchanged mounts; comment on the one-time restart
db/startup/02_vector_memory.sh        # new: vector_memory_size=256M in spfile, restart once if it was 0
.gitignore                            # + .cache/
src/golestan_code_mcp/
  config.py                           # + model_url(env), model_cache(env)
  schema.py                           # + migration 3: embedding column, ccctx_embedding_model
  semantic.py                         # new: MODEL, ModelError, load_model, require_model, search
  ingest.py                           # require_model before discover; insert with VECTOR_EMBEDDING
  cli.py                              # + model load, search
  server.py                           # + search tool
tests/
  test_semantic.py                    # new: model record, embeddings present, ranking, floor, repo filter
  test_schema.py                      # + migration 3
  test_ingest.py                      # skip when model missing; every symbol has an embedding
  test_cli.py                         # + search output, empty question, model-missing message
  test_server.py                      # tool list + search tool contract
README.md                             # model load, search, the one-time restart
```

**Structure Decision**: one `semantic` module holds the model name, the model check and the search query. `ingest`, `cli` and `server` call it, so the model name and the query exist in exactly one place.

## Success Criteria Verification

| Criterion | How it is checked |
|---|---|
| SC-001 | Run the two SQL checks from the request after `ccctx model load`. |
| SC-002 | `test_ingest` and the walkthrough count symbols with a null embedding: 0. |
| SC-003 | Walkthrough: the routing question's top 10 includes routing or dispatch code from flask and from gin. |
| SC-004 | Walkthrough: the sourdough question returns 3 or fewer. |
| SC-005 | `test_semantic` asserts every result is at least 0.3 and in descending order. |
| SC-006 | Time `ccctx search` over both repositories. |
| SC-007 | Time `ccctx ingest flask` and `ccctx ingest gin`. |
| SC-008 | `test_server` compares the tool with `semantic.search`, field for field. |
