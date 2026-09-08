# Issue: Oracle Hybrid Vector Indexes Do Not Support External Embedding Models

**Date:** 2026-03-14
**Status:** Open
**Severity:** Limitation — restricts embedding model experimentation

## Problem

Oracle's `CREATE HYBRID VECTOR INDEX` requires an **in-database ONNX embedding model** specified via the `MODEL` parameter. It does not support external embedding services (Ollama, OpenAI, Cohere, etc.). This means you cannot use an external embedding API and still benefit from hybrid search — the index must own the embedding pipeline end-to-end.

This is a constraint when you want to:
- Try different embedding models quickly (e.g., swap between nomic-embed-text, BGE, E5, etc.)
- Use a cloud-hosted embedding service alongside Oracle's hybrid search
- Keep embedding model management outside the database

## How It Works

When creating a hybrid vector index, Oracle requires an ONNX model loaded into the database:

```sql
-- The MODEL parameter is mandatory — no external embedding alternative
CREATE HYBRID VECTOR INDEX POLICY_HYBRID_IDX
ON POLICY_DOCS(content)
PARAMETERS('MODEL ALL_MINILM_L12_V2 VECTOR_IDXTYPE HNSW MAINTENANCE AUTO');
```

At both ingestion and query time, the index uses this in-database model to compute embeddings. The `DBMS_HYBRID_VECTOR.SEARCH` function accepts `search_text` (raw text) and embeds it automatically using the model bound to the index — there is no option to pass a pre-computed `search_vector` from an external source.

## Impact on This Project

The previous setup used **nomic-embed-text (768-dim) via Ollama** for embeddings. Migrating to hybrid search forced a switch to an in-database ONNX model, which limited options to:

| Option | Model | Dimensions | Setup Complexity |
|--------|-------|------------|-----------------|
| A (chosen for POC) | `all-MiniLM-L12-v2` | 384 | Low — Oracle provides a pre-built ONNX file, direct load via `DBMS_VECTOR.LOAD_ONNX_MODEL` |
| B | `nomic-embed-text-v1.5` | 768 | High — requires OML4Py Client 2.1 (Python 3.12) to convert Hugging Face model into Oracle's augmented ONNX format |

Any model not on [Oracle's supported models list](https://docs.oracle.com/en/database/oracle/oracle-database/26/prvai/available-embedding-models.html) or not convertible via OML4Py cannot be used with hybrid indexes.

## Workarounds

### 1. Use Oracle's pre-built ONNX models (current approach)

Accept the model limitation and pick from Oracle's supported list. For a POC, `all-MiniLM-L12-v2` works fine. Trade-off: you're locked to what Oracle provides pre-built.

### 2. Convert models with OML4Py

Use OML4Py Client 2.1 to convert Hugging Face models into Oracle's augmented ONNX format (adds tokenization + post-processing). This expands the options but adds a Python-based conversion step and not all models are compatible.

### 3. Skip hybrid indexes, do hybrid search manually

Instead of `CREATE HYBRID VECTOR INDEX`, run two separate queries — one vector similarity search (using external embeddings via `VECTOR_DISTANCE`) and one Oracle Text keyword search (via `CONTAINS`) — then fuse the results in Java using Reciprocal Rank Fusion (RRF). This lets you keep any external embedding model but loses the single-call convenience and database-optimized fusion of `DBMS_HYBRID_VECTOR.SEARCH`.

## References

- [Oracle Hybrid Vector Index documentation](https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/manage-hybrid-vector-indexes.html)
- [Oracle supported ONNX embedding models](https://docs.oracle.com/en/database/oracle/oracle-database/26/prvai/available-embedding-models.html)
- [DBMS_VECTOR.LOAD_ONNX_MODEL](https://docs.oracle.com/en/database/oracle/oracle-database/26/arpls/dbms_vector1.html)
- Implementation plan: [`docs/todos/hybrid-vector-search-implementation.md`](../todos/hybrid-vector-search-implementation.md)
