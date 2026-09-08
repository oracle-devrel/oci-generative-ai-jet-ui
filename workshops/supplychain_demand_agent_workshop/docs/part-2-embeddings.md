# Part 2 — In-DB embeddings with `OracleEmbeddings`

## Why in-database embeddings?

Most LangChain examples embed text by calling out to a remote API:

```python
from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")  # ← HTTP round-trip per call
```

Every `embed_query` and `embed_documents` call is a network hop to
OpenAI (or whoever). For a workshop this is fine. For a production
agent that's also running the database **on the same node**, it's
absurd — you'd send the text to OpenAI just to get a vector back, then
write that vector into Oracle, when Oracle already has an embedding
function sitting next to your data.

Oracle's in-database ONNX embedder fixes this. The model lives **inside
the database**, the embedding call is a SQL function, and your
LangChain code never knows the difference.

## `ALL_MINILM_L12_V2` — what's loaded

| Property             | Value                              |
| -------------------- | ---------------------------------- |
| Model name in Oracle | `ALL_MINILM_L12_V2`                |
| Architecture         | MiniLM (sentence-transformers)     |
| Embedding dimension  | **384**                            |
| File size            | ~117 MB                            |
| Loaded by            | `app/scripts/onnx_setup.py`        |
| Loaded via           | `DBMS_VECTOR.LOAD_ONNX_MODEL(...)` |

After the load step, you can verify it directly in SQL:

```sql
SELECT VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING 'football cleats' AS DATA) FROM dual;
-- returns a 384-element VECTOR — no network call left the database.
```

## How `OracleEmbeddings` wraps it

`langchain_oracledb.OracleEmbeddings` is a normal LangChain `Embeddings`
subclass — it can be passed to `OracleVS`, `OracleSemanticCache`, or
`AsyncOracleStore` like any other embedder. Internally it just runs the
SQL above for every text it's given.

```python
from langchain_oracledb import OracleEmbeddings

embeddings = OracleEmbeddings(
    conn=oracle_client,                                          # sync handle
    params={"provider": "database", "model": "ALL_MINILM_L12_V2"},
)
```

The `params` dict tells `OracleEmbeddings` _where_ the model lives.
`"provider": "database"` means "the model is already loaded in this
schema; don't try to download anything." `"model": "ALL_MINILM_L12_V2"`
is the name we used in the `LOAD_ONNX_MODEL` step.

## What you'll build in TODO 1

Construct `embeddings` per the snippet above. The hard-stop checkpoint
embeds a short string and asserts the resulting vector has the expected
**384** dimensions. If it doesn't, you've either pointed the embedder
at the wrong model or the model wasn't loaded.

## Solution

Drop this into the TODO 1 cell, replacing the `embeddings = None` line:

```python
from langchain_oracledb import OracleEmbeddings

embeddings = OracleEmbeddings(
    conn=oracle_client,
    params={"provider": "database", "model": ONNX_MODEL},
)
```

## Next

→ **[Part 3 — `OracleVS`](part-3-vector-store.md)** — use this embedder to power the vector knowledge base.
