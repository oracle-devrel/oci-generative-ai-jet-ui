# Contract: schema migration 4, hybrid vector index

Extends `specs/004-semantic-search/contracts/schema.md`. Migration 4 replaces the step 4 embedding column and HNSW index.

## Migration 4

Applied by `ccctx db migrate` and the migrate pre-step of every command. Ordered and re-runnable.

```sql
drop index ccctx_symbols_embedding_ix;                       -- ORA-01418 tolerated
alter table ccctx_symbols drop column embedding;             -- ORA-00904 tolerated
alter table ccctx_symbols add (search_text clob);            -- ORA-01430 tolerated
update ccctx_symbols s
   set search_text = s.kind || ' ' || s.name || ' in '
       || (select path from ccctx_files f where f.id = s.file_id)
       || chr(10) || s.source
 where search_text is null;
```

The backfill makes symbols stored before this step searchable without re-ingesting (FR-013). `ccctx_embedding_model` is unchanged.

## Created by `ccctx model load` (not a migration)

| Object | Definition |
|---|---|
| Mining model, model record | Unchanged from step 4 (`ALL_MINILM_L12_V2`, dimension `384`). |
| Hybrid vector index | `create hybrid vector index ccctx_symbols_hybrid_ix on ccctx_symbols (search_text) parameters ('MODEL ALL_MINILM_L12_V2 VECTOR_IDXTYPE HNSW SYNC (ON COMMIT) LEXER CCCTX_CODE_LEXER')` (`ORA-00955` tolerated). Serves both keyword and semantic matching. |

`SYNC (ON COMMIT)`: a committed ingest is searchable at once; a search sees the previous complete index or the new one, never a mix (FR-014).

## Stored per symbol at ingest

| Column | Value |
|---|---|
| `ccctx_symbols.search_text` | `CLOB`: `kind || ' ' || name || ' in ' || path || chr(10) || source`, full length. Both CLOB binds (`search_text`, then `source`) come last. |
| `ccctx_symbols.embedding` | Removed. No `VECTOR_EMBEDDING` call at insert; the index vectorizes in the database. |

## Query

One statement per search:

```sql
select dbms_hybrid_vector.search(json(:request)) from dual
```

`:request`:

```json
{
  "hybrid_index_name": "ccctx_symbols_hybrid_ix",
  "search_scorer": "rrf",
  "search_fusion": "UNION",
  "vector": {"search_text": "<query>", "score_weight": 1},
  "text":   {"contains": "{url_for}", "score_weight": 1},
  "return": {"topN": 100}
}
```

`search_scorer` `RRF` and `search_fusion` `UNION` in `hybrid` mode. `vector` mode sends only `vector`; `text` mode sends only `text`. Weights and `topN` come from `CCCTX_VECTOR_WEIGHT`, `CCCTX_TEXT_WEIGHT`, `CCCTX_SEARCH_CANDIDATES`. The result LOB is a JSON array; each row's `rowid`, `score`, `vector_score`, `text_score`, `vector_rank` and `text_rank` are read. Repository filtering is applied after the search by joining rowids to `ccctx_files` and `ccctx_repos` (`filter_by` is not supported).

## Python surface (`golestan_code_mcp.semantic`)

| Name | Shape |
|---|---|
| `MODEL`, `DIMENSION`, `LIMIT`, `FLOOR` | Unchanged: `"ALL_MINILM_L12_V2"`, `384`, `10`, `0.3`. |
| `INDEX` | `"CCCTX_SYMBOLS_HYBRID_IX"` |
| `MODES` | `("vector", "text", "hybrid")` |
| `ModelError` | Unchanged, subclass of `ValueError`. |
| `load_model(conn, env) -> bool` | As step 4; creates the hybrid index. |
| `require_model(conn) -> None` | Raises `ModelError` when model, record or hybrid index is missing or dimension is not 384. |
| `search(conn, question, repos=None, mode="hybrid", env=None) -> list[Result]` | `repos`: list of names or `None` for all. Raises `ValueError` for an empty question, an unknown mode or an unregistered repository, before searching. |
| `Result` | `Result(rank, score, keyword_rank, semantic_rank, similarity, repo, kind, name, path, start_line, end_line)`. `keyword_rank`, `semantic_rank`, `similarity` are `None` when that side did not find the symbol. |

## Config surface (`golestan_code_mcp.config`)

| Field | Variable | Default |
|---|---|---|
| `search_candidates` | `CCCTX_SEARCH_CANDIDATES` | `100` |
| `text_weight` | `CCCTX_TEXT_WEIGHT` | `1.0` |
| `vector_weight` | `CCCTX_VECTOR_WEIGHT` | `1.0` |
