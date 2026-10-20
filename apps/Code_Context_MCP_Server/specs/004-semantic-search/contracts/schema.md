# Contract: schema migration 3, model and vector index

Extends `specs/003-code-ingestion/contracts/schema.md`.

## Migration 3

Applied by `ccctx db migrate` and the migrate pre-step of every command.

```sql
alter table ccctx_symbols add (embedding vector(384, float32));
create table ccctx_embedding_model (
  model_name varchar2(128) primary key,
  dimension  number not null,
  loaded_at  timestamp with time zone default systimestamp not null);
```

`embedding` is nullable: symbols indexed before this step keep `null` until re-ingested, and search skips them. Re-runnable: `ORA-01430` (column exists) and `ORA-00955` (name used) are tolerated.

## Created by `ccctx model load` (not a migration)

| Object | Definition |
|---|---|
| Mining model | `ALL_MINILM_L12_V2`, loaded with `DBMS_VECTOR.LOAD_ONNX_MODEL` from `all_MiniLM_L12_v2`. Listed by `SELECT model_name FROM user_mining_models;`. |
| Model record | Row `('ALL_MINILM_L12_V2', 384)` in `ccctx_embedding_model`. |
| Vector index | `create vector index ccctx_symbols_embedding_ix on ccctx_symbols (embedding) ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95` (`ORA-00955` tolerated). |

## Stored per symbol at ingest

| Column | Value |
|---|---|
| `ccctx_symbols.embedding` | `VECTOR(384, FLOAT32)` computed in the insert: `VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :kind \|\| ' ' \|\| :name \|\| ' in ' \|\| :path \|\| chr(10) \|\| :source AS data)`. Never computed in the application. Text past the model's input limit is truncated by the model. |

## Database setting

`db/startup/02_vector_memory.sh` sets `vector_memory_size=256M` with `scope=spfile` when it is 0, saves FREEPDB1 state, and restarts the instance once. Later starts change nothing.

## Python surface (`golestan_code_mcp.semantic`)

| Name | Shape |
|---|---|
| `MODEL` | `"ALL_MINILM_L12_V2"` |
| `DIMENSION`, `LIMIT`, `FLOOR` | `384`, `10`, `0.3` |
| `ModelError` | subclass of `ValueError` |
| `load_model(conn, env) -> bool` | `True` when it loaded, `False` when already present. |
| `require_model(conn) -> None` | raises `ModelError` when model, record or index is missing or dimension is not 384. |
| `search(conn, question, repo=None) -> list[Result]` | `Result(rank, similarity, repo, kind, name, path, start_line, end_line)`. |
