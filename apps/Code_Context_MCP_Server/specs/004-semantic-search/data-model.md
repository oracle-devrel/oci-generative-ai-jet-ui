# Data Model: Semantic Code Search

This step reshapes one stored entity from step 3 (`ccctx_symbols`, which gains an `embedding` column) and introduces three stored ones: the in-database embedding model `ALL_MINILM_L12_V2`, the model record table `ccctx_embedding_model` and the HNSW index `ccctx_symbols_embedding_ix`. It also introduces three in-memory ones (`Search request`, `Search result`, `Search response`) and one file on disk (the cached model file). `ccctx_repos` and `ccctx_files` are unchanged and only read.

## Relationships

```text
Model file (.cache/models/all_MiniLM_L12_v2.onnx, git-ignored)
  ──loaded by DBMS_VECTOR.LOAD_ONNX_MODEL──> Embedding model (user_mining_models: ALL_MINILM_L12_V2)
                                               1 ── 1 Model record (ccctx_embedding_model)

Repository (ccctx_repos, unchanged)
  1 ──< File (ccctx_files, unchanged)            on delete cascade
          1 ──< Symbol (ccctx_symbols)           on delete cascade
                  └─ embedding  <── VECTOR_EMBEDDING(Embedding model, kind/name/path/source) at insert

Vector index (ccctx_symbols_embedding_ix) ── over ── ccctx_symbols.embedding

Search request ──VECTOR_EMBEDDING(Embedding model, question)──> nearest 10 by cosine
               ──floor 0.3──> Search result[]  ──wrapped by MCP──> Search response
```

Every embedding in `ccctx_symbols` comes from the one model named in `ccctx_embedding_model`. The record, the column dimension and the model name in the SQL (`semantic.MODEL`) must agree, so vectors from two models never share the index (FR-007).

## Embedding model (`ALL_MINILM_L12_V2`, an Oracle mining model)

The ONNX model stored in the database. It turns text into a 384-number vector. Owned by Oracle's catalog, read through `user_mining_models`.

| Field | Value | Rule |
|---|---|---|
| `model_name` | `ALL_MINILM_L12_V2` | Exact name (FR-001). One constant, `semantic.MODEL`, inlined into SQL because it is an identifier, not a bind. |
| source file | `all_MiniLM_L12_v2.onnx`, 133,322,334 bytes | Oracle's prebuilt augmented file (tokenizer included). URL from `CCCTX_MODEL_URL`, default Oracle object storage (FR-002). |
| load call | `DBMS_VECTOR.LOAD_ONNX_MODEL(model_name, model_data => BLOB, metadata)` | Metadata `{"function":"embedding","embeddingOutput":"embedding","input":{"input":["DATA"]}}`. Run as the app user, which holds `CREATE MINING MODEL`. |
| output | `VECTOR(384, FLOAT32)` | `VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING 'hello world' AS data)` returns 384 elements (SC-001). |

Validation: the load is skipped when `user_mining_models` already lists the name (FR-001, US1 scenario 3). Input longer than the model's limit is truncated by the model, not rejected.

## Model file (cache on disk, not stored in the database)

| Field | Rule |
|---|---|
| path | `.cache/models/all_MiniLM_L12_v2.onnx` under the project root; `.cache/` is git-ignored. |
| reuse | The download is skipped when the file exists with the expected size (133,322,334 bytes). A file of any other size is fetched again. |
| failure | A failed download names the file and the URL and leaves the database unchanged (US1 scenario 4). |

The file holds model weights only. Fetching it sends no code or symbol text.

## Model record (`ccctx_embedding_model`, new in migration 3)

Records which model produced the stored embeddings and their dimension, so a model change is detected (FR-007).

| Field | Type | Null | Rule |
|---|---|---|---|
| `model_name` | `varchar2(128)` | no | Primary key. `ALL_MINILM_L12_V2`. |
| `dimension` | `number` | no | `384`; must equal the column's declared dimension. |
| `loaded_at` | `timestamp with time zone` | no | Default `systimestamp`. |

Written by `ccctx model load` after the model is loaded. At most one row is expected; `require_model` refuses when the row for `semantic.MODEL` is missing or its dimension is not 384.

## Symbol (`ccctx_symbols`, extended by migration 3)

All step 3 fields are unchanged (`id`, `file_id`, `name`, `kind`, `start_line`, `end_line`, `source`, `content_hash`, `commit_sha`). One field is added:

| Field | Type | Null | Rule |
|---|---|---|---|
| `embedding` | `vector(384, float32)` | yes | Computed by the database in the same `insert` as the row (FR-003, FR-004): `VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :kind \|\| ' ' \|\| :name \|\| ' in ' \|\| :path \|\| chr(10) \|\| :source AS data)`. Kind, name and path come first so truncation never cuts them (FR-005). Never computed in the application. |

Validation:

- Nullable only so that rows stored before migration 3 survive. Search skips rows where it is null.
- After any ingest run under this step, every symbol of that repository has a non-null embedding (SC-002). Fallback chunks (`kind = 'chunk'`) are embedded too.
- Ingest calls `semantic.require_model(conn)` before discovery and changes nothing when it fails (FR-008).

## Vector index (`ccctx_symbols_embedding_ix`)

| Field | Value |
|---|---|
| table / column | `ccctx_symbols (embedding)` |
| organization | `ORGANIZATION INMEMORY NEIGHBOR GRAPH` (HNSW) |
| distance | `DISTANCE COSINE` |
| accuracy | `WITH TARGET ACCURACY 95` |

Created by `ccctx model load`, not by a migration, so commands that run `migrate()` keep working on a database without the vector pool. Creation tolerates ORA-00955. It needs `vector_memory_size` > 0, set to `256M` by `db/startup/02_vector_memory.sh`. `require_model` refuses when the index is missing.

## Search request (in memory)

| Field | Type | Rule |
|---|---|---|
| `question` | `str` | Required. Empty or whitespace-only is refused before connecting (FR-014, US3 scenario 5). |
| `repo` | `str \| None` | Optional. Resolved through `registry.get_repo`; an unknown name is refused and named (FR-013). |
| limit | `10` | Fixed. `fetch approx first 10 rows only with target accuracy 95`. |
| floor | `0.3` | Fixed. Applied after the top 10, never relaxed to fill the list (FR-010). |

## Search result (in memory, `semantic.Result`)

One symbol returned for a question (FR-011, FR-015).

| Field | Type | Rule |
|---|---|---|
| `rank` | `int` | 1-based, by descending similarity. |
| `similarity` | `float` | `1 - vector_distance(embedding, question_vector, cosine)`; always ≥ 0.3 (SC-005). Rounded to 3 places for display only. |
| `repo` | `str` | `ccctx_repos.name`. |
| `kind` | `str` | Symbol kind, `chunk` for fallback windows. |
| `name` | `str` | Symbol name. |
| `path` | `str` | `ccctx_files.path`. |
| `start_line`, `end_line` | `int` | Symbol line range. |

A list holds 0 to 10 results in strictly non-increasing similarity. The CLI prints them as `RANK SIMILARITY REPO KIND NAME PATH LINES`; an empty list prints `no symbols similar enough (similarity >= 0.30)` and exits 0 (FR-012).

## Search response (MCP tool `search`)

| Field | Type | Rule |
|---|---|---|
| `status` | `"ok" \| "unavailable"` | `unavailable` for database down, model missing, unknown repo or empty question. `isError` is always false. |
| `reason` | `str \| null` | Set when `status` is `unavailable`; never contains a password. |
| `results` | list of Search result | Same symbols, order and scores as `ccctx search` (SC-008); empty when unavailable. |

## State transitions

### Semantic setup (per database)

```text
no pool ──02_vector_memory.sh (spfile 256M, one restart)──> pool enabled
pool enabled ──model load: download/cache──> file cached
file cached ──LOAD_ONNX_MODEL──> model loaded ──insert record──> recorded ──create index──> READY
```

- `ccctx model load` is re-runnable: each stage is skipped when already done, so a run on a READY database changes nothing (US1 scenario 3).
- A failure at any stage leaves later stages undone; `require_model` reports not-ready and names `ccctx model load`.
- Only READY allows ingest and search.

### Symbol embedding

```text
(row from step 3) embedding = null ──re-ingest under READY──> row replaced, embedding set
(new row under READY)            ──insert──> embedding set
```

No backfill command: rows are replaced by re-ingest (delete files, cascade, insert with `VECTOR_EMBEDDING`).
