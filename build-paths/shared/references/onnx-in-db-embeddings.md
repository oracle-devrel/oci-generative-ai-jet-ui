# ONNX in-DB embeddings

For advanced users who want **no external embedding API** — embeddings happen inside the Oracle Database itself, on insert and on query, via a registered ONNX model. No Python embedder process to keep alive, no network round-trips per query, no data leaving the DB.

## Recommended path: `onnx2oracle` (canonical exemplar, now a PyPI CLI)

The canonical reference [`github.com/jasperan/onnx2oracle`](https://github.com/jasperan/onnx2oracle) ships as a `pip`-installable command-line tool that does export-and-register in one shot. **Use it instead of the manual three-step pipeline below** unless you have a reason not to.

```bash
pip install onnx2oracle
onnx2oracle load all-MiniLM-L6-v2 \
    --name MY_MINILM_V1 \
    --dsn "$DB_USER/$DB_PASSWORD@$DB_DSN" \
    --force
```

The `--dsn` flag takes a single connection string in the form `user/password@host:port/service`. There are NO separate `--user` / `--password` flags. `--force` re-registers if a model of the same name already exists.

After registration, smoke with:

```sql
SELECT VECTOR_EMBEDDING(MY_MINILM_V1 USING 'test' AS data) FROM dual;
-- Returns a 384-dim vector for MiniLM-L6-v2.
```

### Required GRANTs

The user running `onnx2oracle load ...` must have:

- `CREATE MINING MODEL` (granted to the app user during `oracle-aidb-docker-setup` Step 6).
- `EXECUTE ON SYS.DBMS_VECTOR` (also granted in Step 6; if your build refuses, connect as `SYS AS SYSDBA` and run the GRANT manually — `26ai Free` typically allows it from `SYSTEM`).

If `onnx2oracle` exits with `ORA-29516` or `ORA-01031`, the GRANT chain is incomplete — check `oracle-aidb-docker-setup`'s Step 6 ran fully.

## Manual three-step pipeline (appendix)

Keep this for users who can't add `onnx2oracle` as a dependency. The CLI does these three things internally; if you must do them by hand, here they are.

## When to use

| Use it when | Don't use it when |
| --- | --- |
| Data sensitivity matters and you don't want text leaving the DB. | You want bleeding-edge embedders that don't have ONNX exports. |
| You're committed to Oracle as the only state store and external embedders feel inconsistent. | You want SentencePiece tokenizers (T5, XLM-R) — they fail at load. |
| You want SQL-side embedding (`VECTOR_EMBEDDING(model USING text)`). | You're in beginner / intermediate land. This is overkill. |

## Pipeline (HF → ONNX → Oracle)

The conversion has three concrete steps. Skipping any one of them produces a model that loads but returns garbage embeddings.

### 1. Export the HF model to ONNX

```python
from optimum.onnxruntime import ORTModelForFeatureExtraction
from transformers import AutoTokenizer

model_id = "sentence-transformers/all-MiniLM-L6-v2"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = ORTModelForFeatureExtraction.from_pretrained(model_id, export=True)
tokenizer.save_pretrained("./onnx_model")
model.save_pretrained("./onnx_model")
```

### 2. Wrap with the tokenizer + post-processing into one ONNX graph

Oracle's `DBMS_VECTOR.LOAD_ONNX_MODEL` expects a *single* `.onnx` file that does tokenization + transformer + L2-norm in one graph. `onnxruntime_extensions` provides the tokenizer wrapping.

This is the gnarly part. Source: `~/git/personal/onnx2oracle/src/onnx2oracle/pipeline.py:1-100`. The advanced skill copies that script verbatim into the user's project — it's not a thing the user should rewrite.

### 3. Register in Oracle

```sql
BEGIN
  DBMS_VECTOR.LOAD_ONNX_MODEL(
    directory => 'ONNX_DIR',
    file_name => 'all-MiniLM-L6-v2.onnx',
    model_name => 'MY_MINILM',
    metadata => JSON('{
      "function": "embedding",
      "embeddingOutput": "embedding",
      "input": {"input": ["DATA"]}
    }')
  );
END;
/
```

`ONNX_DIR` is an Oracle DIRECTORY object pointing at a host filesystem path the DB can read. The advanced skill creates the directory + grants reads as part of scaffolding.

Source: `~/git/personal/onnx2oracle/src/onnx2oracle/loader.py:15-70`.

## Using the registered model

### Inline at insert

```sql
INSERT INTO my_docs (content, embedding)
VALUES (
    :content,
    VECTOR_EMBEDDING(MY_MINILM USING :content AS data)
);
```

No Python embedder needed. The DB tokenizes, runs inference, and stores the vector in one round-trip.

### Inline at query

```sql
SELECT id, content
FROM my_docs
ORDER BY VECTOR_DISTANCE(
    embedding,
    VECTOR_EMBEDDING(MY_MINILM USING :query AS data),
    COSINE
)
FETCH FIRST :k ROWS ONLY;
```

Cleaner than the Python-side embed-then-bind pattern. Lower latency too — no `array.array("f", ...)` round-trip.

## Constraints (the gotchas)

| Constraint | Why | Implication |
| --- | --- | --- |
| **BertTokenizer only** | `onnxruntime_extensions` ships BertTokenizer. SentencePiece (T5, XLM-R, MPNet variants) fails at `LOAD_ONNX_MODEL`. | Pick a sentence-transformers model with a Bert-family tokenizer. `all-MiniLM-L6-v2` is the safe default. |
| **ONNX opset ≤ 14** | Oracle's runtime is pinned. | When exporting, pin `opset=14`. Optimum sometimes defaults higher. |
| **Model file size** | The free DB has a model-size limit. | `all-MiniLM-L6-v2` (90MB) fits. `all-mpnet-base-v2` (420MB) is borderline. |
| **One model per `model_name`** | `LOAD_ONNX_MODEL` doesn't versioning. | Skill picks a name like `<PROJECT>_EMBED_V1` so re-loads are explicit. |

## LangChain integration

The advanced skill writes a small `Embeddings` subclass that calls `VECTOR_EMBEDDING(...)` via SQL instead of an external API:

```python
class InDBEmbeddings(Embeddings):
    def __init__(self, conn, model_name: str):
        self.conn = conn
        self.model_name = model_name

    def embed_documents(self, texts):
        # batch via VECTOR_EMBEDDING + UNION ALL or per-row INSERT-then-SELECT
        ...

    def embed_query(self, text):
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT VECTOR_EMBEDDING({self.model_name} USING :t AS data) FROM dual",
                t=text,
            )
            return list(cur.fetchone()[0])
```

This plugs into `OracleVS` like any other `Embeddings`. The user's DB column dim must match the registered model's output dim (384 for MiniLM-L6-v2).

## Don't do these

- Don't try to register an LLM as an embedder. `LOAD_ONNX_MODEL` rejects it; the metadata schema is different.
- Don't rebuild the same model under a different name "for safety." Drop and reload — orphan models eat space.
- Don't skip the L2-norm step in the ONNX graph. Without it, your distances are meaningless.

## Exemplars

| Step | File |
| --- | --- |
| HF → ONNX pipeline | `~/git/personal/onnx2oracle/src/onnx2oracle/pipeline.py:1-100` |
| `LOAD_ONNX_MODEL` registration | `~/git/personal/onnx2oracle/src/onnx2oracle/loader.py:15-70` |
| End-to-end test | `~/git/personal/onnx2oracle/tests/test_loader_integration.py` |
