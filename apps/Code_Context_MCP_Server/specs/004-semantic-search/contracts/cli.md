# Contract: `ccctx model load`, `ccctx search`

Extends the step 3 CLI contract (`specs/003-code-ingestion/contracts/cli.md`). Exit codes (`0` ok, `1` refused, `2` database unreachable or starting), `error: <reason>` on stderr, the no-password rule and the migrate-first pre-step are unchanged.

## Settings

Read from `.env` and the environment. Not command-line flags.

| Variable | Default | Meaning |
|---|---|---|
| `CCCTX_MODEL_URL` | `https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/iPX9W0MZeRkwJKWdFmdJCemmN-iKAl_bFvNGYLW7YqIrw4kKsukL24J2q93Beb9S/n/adwc4pm/b/OML-ai-models/o/all_MiniLM_L12_v2.onnx` | Where the published ONNX `all_MiniLM_L12_v2` file is fetched from. |

Cache: `.cache/models/all_MiniLM_L12_v2.onnx` under the project root (git-ignored). Reused when it exists with the expected size (133,322,334 bytes).

## `ccctx model load`

Loads the model with `DBMS_VECTOR.LOAD_ONNX_MODEL` as `ALL_MINILM_L12_V2` (BLOB overload, metadata `{"function":"embedding","embeddingOutput":"embedding","input":{"input":["DATA"]}}`), records it in `ccctx_embedding_model` with dimension `384`, and creates `ccctx_symbols_embedding_ix`. Each part is skipped when already done.

Success, exit `0`, stdout, one of:

```text
model ALL_MINILM_L12_V2 loaded (384 dimensions)
model ALL_MINILM_L12_V2 already present (384 dimensions)
```

Refusals, exit `1`, database unchanged:

| Cause | stderr |
|---|---|
| Download fails | `error: could not download all_MiniLM_L12_v2.onnx from <url>: <reason>` |
| Model loaded but dimension is not 384 | `error: model ALL_MINILM_L12_V2 has <n> dimensions, expected 384` |
| Vector memory pool disabled (index build fails) | `error: vector memory pool is not enabled; restart the database container once` |

Checks after success:

```sql
SELECT model_name FROM user_mining_models;                                  -- lists ALL_MINILM_L12_V2
SELECT VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING 'hello world' as data) AS v; -- 384 elements
```

## `ccctx ingest <name>` (changed)

Output unchanged. Before discovery it now runs the model check; when the model, its `ccctx_embedding_model` record (dimension 384) or the index is missing it exits `1`, changing nothing:

```text
error: embedding model ALL_MINILM_L12_V2 is not set up; run `ccctx model load`
```

## `ccctx search "<question>" [--repo <name>]`

Examples: `ccctx search "how are incoming requests routed to handlers"`, `ccctx search "recipe for sourdough bread"`, `ccctx search "router" --repo gin`.

Embeds the question in the database with `ALL_MINILM_L12_V2`, takes the `10` approximate nearest symbols by cosine distance, and keeps those with similarity (`1 - cosine distance`) `>= 0.3`. The floor is applied after the top 10 and never relaxed.

Success, exit `0`, stdout, a `format_table` table ordered by similarity descending:

```text
RANK  SIMILARITY  REPO   KIND      NAME                 PATH                LINES
   1       0.612  flask  method    Flask.dispatch_request src/flask/app.py  870-895
   2       0.587  gin    function  (*Engine).handleHTTPRequest gin.go      600-660
```

- `RANK` 1-based. `SIMILARITY` three decimals (display rounding only). `LINES` is `start-end`, 1-based inclusive. `KIND` includes `chunk` for fallback windows.
- Nothing at or above the floor: `no symbols similar enough (similarity >= 0.30)`, exit `0`.
- Nothing indexed (no symbol with an embedding in scope): `nothing indexed yet`, exit `0`.

Refusals:

| Cause | Exit | stderr |
|---|---|---|
| Empty or whitespace-only question (checked before connecting) | `1` | `error: question must not be empty` |
| Unknown `--repo` | `1` | `error: no repository named '<name>'` |
| Model not set up | `1` | `error: embedding model ALL_MINILM_L12_V2 is not set up; run `ccctx model load`` |
| Database unreachable | `2` | `error: database unreachable: <reason>` (no password) |
