# Data Model: Hybrid Code Search

This step reshapes one stored entity (`ccctx_symbols`: gains `search_text`, loses step 4's `embedding`), replaces one (the HNSW index `ccctx_symbols_embedding_ix` gives way to the hybrid vector index `ccctx_symbols_hybrid_ix`), and adds one migration (4). It introduces four in-memory entities (`Search mode`, `Search request`, `Hybrid candidate`, `Search result`) and three settings. `ccctx_repos`, `ccctx_files`, the embedding model `ALL_MINILM_L12_V2` and `ccctx_embedding_model` are unchanged and only read.

## Relationships

```text
Repository (ccctx_repos, unchanged)
  1 ──< File (ccctx_files, unchanged)            on delete cascade
          1 ──< Symbol (ccctx_symbols)           on delete cascade
                  └─ search_text = kind ' ' name ' in ' file.path \n source

Embedding model (ALL_MINILM_L12_V2, unchanged)
  └─ used by ──> Hybrid index (ccctx_symbols_hybrid_ix) ── over ── ccctx_symbols.search_text
                   (keyword side: Oracle Text; semantic side: HNSW, vectorized in-database)

Search request (question, mode, repos)
  ──DBMS_HYBRID_VECTOR.SEARCH, RRF + UNION, topN = CCCTX_SEARCH_CANDIDATES──> Hybrid candidate[] (by rowid)
  ──join ccctx_symbols/files/repos, filter repos, dedupe by symbol──>
  ──vector mode: floor 0.3 │ hybrid/text: definition matches first──>
  ──cap 10──> Search result[]  ──CLI table │ MCP response──>
```

One index serves both sides, so keyword and semantic ranks always refer to the same set of rows (FR-001). The semantic side uses the same model as step 4, so no second vector store exists.

## Symbol (`ccctx_symbols`, reshaped)

Existing columns (`id`, `file_id`, `name`, `kind`, `start_line`, `end_line`, `source`, `content_hash`, `commit_sha`) and their constraints are unchanged.

| Field | Type | Rule |
|---|---|---|
| `search_text` | `clob`, nullable at the column level | Added by migration 4. `kind || ' ' || name || ' in ' || <file path> || chr(10) || source` (FR-001). Full text, not capped; the index chunks long text itself. Written by ingest at insert, and backfilled by migration 4 for rows stored earlier (FR-013). Must be non-null for every row after migration 4 and every ingest. |
| `embedding` | removed | Dropped by migration 4 (ORA-00904 tolerated on re-run). Derived data the hybrid index recomputes. |

Insert rule (ingest): `_insert_symbols` binds `search_text` then `source` as the last two binds (both CLOBs, avoids ORA-24816) and no longer calls `VECTOR_EMBEDDING`. `EMBED_CHARS` is removed.

## Hybrid index (`ccctx_symbols_hybrid_ix`)

| Field | Value | Rule |
|---|---|---|
| name | `ccctx_symbols_hybrid_ix` | One constant in `semantic.py`; passed as `hybrid_index_name`. |
| column | `ccctx_symbols.search_text` | The only indexed text (FR-001). |
| parameters | `MODEL ALL_MINILM_L12_V2 VECTOR_IDXTYPE HNSW SYNC (ON COMMIT) LEXER CCCTX_CODE_LEXER` | Same model as the stored embedding model. |
| created by | `ccctx model load` | Needs the model and the vector memory pool (step 4 rule). Idempotent: an existing index is kept. `require_model` treats a missing index like a missing model and refuses search. |
| replaces | `ccctx_symbols_embedding_ix` | Dropped by migration 4 (ORA-01418 tolerated). |

### Freshness (state transitions)

```text
symbols for repo R (version n, indexed)
  ──ingest: delete + insert in one transaction──> uncommitted (index still serves version n)
  ──commit, SYNC ON COMMIT──> version n+1 indexed and searchable
  ──rollback──> version n, unchanged
```

A search sees version n or version n+1, never a mix (FR-014, edge case "searching during an ingest").

## Migration 4 (`hybrid search text`)

Ordered and re-runnable; each statement tolerates its "already done" error.

| Order | Statement | Tolerated |
|---|---|---|
| 1 | `drop index ccctx_symbols_embedding_ix` | ORA-01418 |
| 2 | `alter table ccctx_symbols drop column embedding` | ORA-00904 |
| 3 | `alter table ccctx_symbols add (search_text clob)` | ORA-01430 |
| 4 | backfill: `update ccctx_symbols s set search_text = s.kind || ' ' || s.name || ' in ' || (select path from ccctx_files f where f.id = s.file_id) || chr(10) || s.source where search_text is null` | — |

The hybrid index is not created here; the next `ccctx model load` builds it over the backfilled rows.

## Settings (`config.py`)

| Env var | Field | Default | Rule |
|---|---|---|---|
| `CCCTX_SEARCH_CANDIDATES` | `search_candidates` | 100 | Positive integer. `return.topN` of the hybrid request. Raise when a small repository is crowded out by filtering. |
| `CCCTX_TEXT_WEIGHT` | `text_weight` | 1 | Positive number. Keyword side `score_weight` (FR-008). |
| `CCCTX_VECTOR_WEIGHT` | `vector_weight` | 1 | Positive number. Semantic side `score_weight` (FR-008). |

Invalid values are refused at startup with the variable name in the message. All three are documented in the README. The result cap (10) and the vector floor (0.3) stay constants (FR-012, FR-005).

## Search mode

| Value | Request sides | Post-processing |
|---|---|---|
| `hybrid` (default) | `vector` + `text`, `search_scorer: "rrf"`, `search_fusion: "UNION"` (FR-003) | Definition boost |
| `vector` | `vector` only | Drop `vector_score < 100 × 0.3` (FR-005); no definition boost |
| `text` | `text` only | Definition boost |

Any other value is refused before the search, listing the three valid values (FR-004).

## Search request (in memory)

| Field | Type | Rule |
|---|---|---|
| `question` | str | Stripped; empty is refused (step 4 rule). Treated literally (FR-011). |
| `mode` | `Search mode` | Default `hybrid`. |
| `repos` | list[str] | CLI: repeated `--repo` and/or comma-separated; MCP: `repos` list plus legacy `repo` (FR-015). Names are trimmed, blanks dropped, duplicates removed (edge case). Empty means all repositories (FR-009). Every name must exist in `ccctx_repos`, else refused naming the unknown ones, before any search runs (FR-010). |

Derived from `question`:

- **Text query**: split on whitespace; from each word remove `{`, `}` and `\`; drop words left empty; wrap each in braces; join with ` AND `. So every word must appear, whole and case-insensitively, and `_ - & | ( ) %` are literal (FR-005, FR-011). Stopwords such as `for` match nothing on their own.
- **Identifier**: set only when the stripped question matches `^[A-Za-z_][\w.]*$`. Drives the definition boost.

## Hybrid candidate (in memory)

One JSON row of the `DBMS_HYBRID_VECTOR.SEARCH` result LOB.

| Field | Meaning |
|---|---|
| `rowid` | Row of `ccctx_symbols`; joined back to the symbol, its file and repository. |
| `score` | Fused score, 0-100. |
| `vector_score`, `vector_rank` | Semantic similarity (0-100, index scale) and rank. |
| `text_score`, `text_rank` | Keyword score and rank. `text_score = 0` means the keyword side did not find it (its rank is a placeholder). |

Several candidates may map to one symbol (the index chunks long text); the one with the best fused score is kept.

## Definition match

A symbol in the chosen repositories, with `kind <> 'chunk'`, where `lower(name) = lower(:identifier)` or `lower(name) like '%.' || lower(:identifier)` (FR-006). Found by a direct query, not only among candidates, so the rule holds even if fusion ranked the definition below `topN`. `url_for` matches both the `url_for` function and `Flask.url_for`; `Flask.url_for` matches only the method.

Ordering in hybrid and text modes: definition matches first (those that were candidates in fused order, then the rest by path), then all other candidates in fused order. With no identifier, or no definition match, the order is fused order alone.

## Search result (in memory)

At most 10 per search (FR-012).

| Field | Source | Shown as |
|---|---|---|
| `rank` | Position after ordering, 1-based | integer |
| `score` | Candidate `score`; a definition match that was not a candidate has none | number, or `-` |
| `keyword_rank` | `text_rank` when `text_score > 0` | integer, or `-` (FR-007) |
| `semantic_rank` | `vector_rank` | integer, or `-` |
| `similarity` | `vector_score / 50 - 1` | MCP only; kept for existing clients |
| `repo`, `kind`, `name`, `path`, `start_line`, `end_line` | Joined symbol, file and repository | as in step 4 |

The MCP tool returns these fields from the same `semantic.search` call the CLI uses, in the same order (FR-015, SC-008). `score`, `keyword_rank` and `semantic_rank` are additive output fields; `null` stands for the CLI's dash.
