# Research: Semantic Code Search

Facts probed on the running database (23.26.3 Free) before deciding:

- The app user holds `CREATE MINING MODEL`.
- `vector_memory_size` is 0, and `sga_target` is 1.5 GB.
- `alter system set vector_memory_size=512M scope=memory` fails with ORA-51950 ("cannot be increased").
- No mining models are loaded yet.

## Getting the model file

- **Decision**: download `https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/iPX9W0MZeRkwJKWdFmdJCemmN-iKAl_bFvNGYLW7YqIrw4kKsukL24J2q93Beb9S/n/adwc4pm/b/OML-ai-models/o/all_MiniLM_L12_v2.onnx` (133,322,334 bytes, HTTP 200 on 2026-10-11) with `urllib.request` into `.cache/models/all_MiniLM_L12_v2.onnx` under the project root. The download is skipped when the cached file exists with the expected size. `CCCTX_MODEL_URL` overrides the URL.
- **Rationale**: this is Oracle's current prebuilt, augmented (tokenizer-included) file. The older `OML-Resources/all_MiniLM_L12_v2_augmented.zip` link now returns 404. A direct `.onnx` needs no unzip step. The file is code-free model weights, so downloading it sends nothing of ours.
- **Alternatives considered**: shipping the 133 MB file in git bloats the repository. Downloading inside the container needs curl and network access in the image.

## Loading it into the database

- **Decision**: read the cached file and bind it as a BLOB to `DBMS_VECTOR.LOAD_ONNX_MODEL(model_name => 'ALL_MINILM_L12_V2', model_data => :blob, metadata => JSON('{"function":"embedding","embeddingOutput":"embedding","input":{"input":["DATA"]}}'))`, as the app user. Skip the load when `user_mining_models` already lists the model.
- **Rationale**: the BLOB overload needs no Oracle DIRECTORY object. That means no SYS-created directory, no new mount and no file copy into the container. The metadata matches Oracle's documented input and output names for this augmented model.
- **Alternatives considered**: the directory overload needs a DBA to create and grant a directory and a bind mount for the file. `LOAD_ONNX_MODEL_CLOUD` needs network access from the database.

## Enabling the vector memory pool

- **Decision**: new startup script `db/startup/02_vector_memory.sh`, run as sysdba in the CDB root on every start:
  - If the spfile value of `vector_memory_size` is 0, set it to `256M` with `scope=spfile`, then `shutdown immediate` and `startup`. Before that, run `alter pluggable database freepdb1 save state` so FREEPDB1 reopens after the restart.
  - On every later start the value is already set and the script does nothing.
- **Rationale**: ORA-51950 shows the pool cannot be raised on a running instance. 256 MB is generous for a few thousand 384-dimension vectors, which take about 1.5 KB each plus the graph, and leaves the 1.5 GB SGA room. Doing the restart inside the script keeps "one command starts the database".
- **Alternatives considered**: asking the developer to run `docker compose restart` once is easy to miss, and every index build would fail with an obscure error until they did. A bigger pool takes memory from the buffer cache for no gain at this size.

## Where the HNSW index is created

- **Decision**: `ccctx model load` creates `ccctx_symbols_embedding_ix` with `create vector index … on ccctx_symbols (embedding) ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95`, tolerating ORA-00955. Migration 3 adds only the column and the model record table.
- **Rationale**: `migrate()` runs before every command. If the index were in a migration, a database without the vector pool would break `repo list` and every other command. Putting the index with the model keeps "set up semantic search" as one step that can fail clearly on its own.
- **Alternatives considered**: a migration step tolerating the pool error leaves the index silently missing.

## Migration 3

- **Decision**: two statements. First, `alter table ccctx_symbols add (embedding vector(384, float32))`, nullable. Second, `create table ccctx_embedding_model (model_name varchar2(128) primary key, dimension number not null, loaded_at timestamp with time zone default systimestamp not null)`.
- **Rationale**: existing symbols survive until they are re-ingested (US2 scenario 2). Their embedding is null meanwhile, and search skips rows with a null embedding. The model table records name and dimension, so a model change is detectable (FR-007, constitution).

## Embedding on insert

- **Decision**: `_insert_symbols` switches to named binds and stores `embedding = VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :kind || ' ' || :name || ' in ' || :path || chr(10) || :source AS data)`. `source` is bound once as a CLOB and reused. The model name is the one `semantic.MODEL` constant, inlined into the SQL because it is an identifier.
- **Rationale**: the database computes every vector (FR-004). Kind, name and path come first so the model's input truncation never cuts them off. The text is built in SQL from values already being inserted, so nothing extra is sent.
- **Alternatives considered**: a second `update … set embedding = …` pass doubles the work and leaves a window with null embeddings.

## Ingest refuses without the model

- **Decision**: `semantic.require_model(conn)` runs before discovery. It checks that the model is listed in `user_mining_models`, that `ccctx_embedding_model` records it with dimension 384, and that the index exists. Otherwise it raises `semantic.ModelError` with "embedding model ALL_MINILM_L12_V2 is not set up; run `ccctx model load`". `ModelError` subclasses `ValueError`, so the CLI exits 1.
- **Rationale**: FR-008 requires that nothing changes, and checking first avoids chunking a repository only to refuse.

## The search query

- **Decision**:
  ```sql
  with q as (select vector_embedding(ALL_MINILM_L12_V2 using :question as data) v from dual),
  top as (
    select r.name repo, s.kind, s.name, f.path, s.start_line, s.end_line,
           1 - vector_distance(s.embedding, q.v, cosine) similarity
      from ccctx_symbols s join ccctx_files f on f.id = s.file_id join ccctx_repos r on r.id = f.repo_id, q
     where s.embedding is not null and (:r is null or r.id = :r)
     order by vector_distance(s.embedding, q.v, cosine)
     fetch approx first 10 rows only with target accuracy 95)
  select * from top where similarity >= 0.3 order by similarity desc
  ```
  It returns `Result(rank, similarity, repo, kind, name, path, start_line, end_line)`. Similarity is rounded to 3 places for display only.
- **Rationale**: one round trip. The question is embedded by the same in-database model. The floor is applied after the top 10, so it never pulls in an 11th weaker match. An unknown `--repo` goes through `registry.get_repo`'s message.

## Output and the MCP tool

- **Decision**:
  - CLI columns: `RANK SIMILARITY REPO KIND NAME PATH LINES`, through `format_table`. With nothing above the floor it prints `no symbols similar enough (similarity >= 0.30)`. An empty question is refused before connecting.
  - MCP tool `search(question: str, repo: str | None = None)` returns `{status: "ok" | "unavailable", reason, results: [...]}`. Every failure becomes `unavailable` with a reason: database down, model missing, unknown repo, empty question. `isError` is always false.
- **Rationale**: same shape and error behaviour as the existing tools. `status` replaces `database` because "unavailable" also covers a missing model, which is not a database outage.
