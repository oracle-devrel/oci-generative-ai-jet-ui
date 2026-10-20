# Research: Hybrid Code Search

All findings below were probed on the running 23.26.3 database with throwaway tables, which were then dropped.

## One hybrid vector index replaces the step 4 vector index

- **Decision**:
  - Migration 4 drops `ccctx_symbols_embedding_ix` (ORA-01418 tolerated) and the `embedding` column (ORA-00904 tolerated).
  - It adds `search_text clob` and backfills it with `update ccctx_symbols s set search_text = s.kind || ' ' || s.name || ' in ' || (select path from ccctx_files f where f.id = s.file_id) || chr(10) || s.source`.
  - `ccctx model load` creates `ccctx_symbols_hybrid_ix` with `create hybrid vector index … on ccctx_symbols (search_text) parameters ('MODEL ALL_MINILM_L12_V2 VECTOR_IDXTYPE HNSW SYNC (ON COMMIT)')`.
- **Rationale**: the request asks for lexical and semantic matching from one index. The hybrid index vectorizes text itself with the in-database model, so keeping the step 4 `VECTOR_EMBEDDING` insert would embed every symbol twice. The backfill keeps symbols stored before this step searchable without re-ingesting (FR-013). Building the index stays in `model load`, because it needs the model and the vector memory pool (the step 4 rule).
- **Alternatives considered**: keeping the step 4 column for vector mode means two vector stores built by different paths. A user datastore joining in the path has more moving parts than one column.

## Index freshness

- **Decision**: `SYNC (ON COMMIT)`.
- **Rationale**: the probe showed the default index does not see a committed row until a sync. With sync on commit, a fresh row was found immediately. Ingest already replaces a repository's symbols in one transaction, so searches see the old index or the new one (FR-014). The cost is that the commit embeds the new rows, which is the same work step 4 did inside the insert.
- **Alternatives considered**: calling `ctx_ddl.sync_index` after commit works (1.3 s on the probe) but leaves a window between commit and sync.

## The query

- **Decision**: one `select dbms_hybrid_vector.search(json(:request)) from dual`. The request has `hybrid_index_name`, `search_scorer: "rrf"`, `search_fusion: "UNION"` and `return.topN = CCCTX_SEARCH_CANDIDATES` (default 100), and by mode:
  - **hybrid**: both sides.
  - **vector**: only `vector: {search_text, score_weight}`.
  - **text**: only `text: {contains, score_weight}`.

  The text side is the question's words, split on whitespace, each with `{`, `}` and `\` removed and wrapped in braces, then joined with ` AND `. The result LOB is parsed as JSON.
- **Rationale**: braces make Oracle Text treat each word literally. Without them `_` in `url_for` is a wildcard and matched nothing. AND gives "contains every word" (FR-005), and stopwords such as `for` simply match nothing. Text-only results have no `chunk_text`, so only `rowid`, the scores and the ranks are read.
- **Alternatives considered**: `ctx_query` escaping helpers add a round trip. Sending the raw question breaks on `_`, `-`, `&` and parentheses.

## Repository filter and the 10-result cap

- **Decision**: map the candidate rowids to symbols with one query that joins `ccctx_files` and `ccctx_repos`, keep only the chosen repositories, de-duplicate by symbol (keeping its best fused score), then cap at 10.
- **Rationale**: the probe rejected a `filter_by` key, so filtering happens after the search. Asking for 100 candidates leaves enough after filtering for the two-repository case. The ceiling is a very small repository among very large ones, where fewer than 10 of the 100 candidates may belong to it. `CCCTX_SEARCH_CANDIDATES` raises that ceiling.

## Definitions above call sites

- **Decision**: when the question is a single identifier (`^[A-Za-z_][\w.]*$`), query directly for symbols in the chosen repositories whose `lower(name) = lower(:q)` or `lower(name) like '%.' || lower(:q)`, excluding chunks. In hybrid and text modes those come first, in fused order when they were candidates and by path otherwise. Everything else follows in fused order.
- **Rationale**: there is one definition and many call sites. A direct name lookup makes the rule deterministic (FR-006), even if fusion ranked the definition outside the candidates. `Flask.url_for` and the `url_for` function both qualify.

## Scores shown and the vector floor

- **Decision**: show `score` (fused, 0-100), the keyword rank (`text_rank` when `text_score > 0`, else `-`) and the semantic rank (`vector_rank`). In vector mode, drop results whose `vector_score` is below `100 × 0.3`. The MCP output keeps a `similarity` field, which is `vector_score / 100`, and adds `score`, `keyword_rank` and `semantic_rank`.
- **Rationale**: `vector_score` is the index's own similarity on a 0-100 scale. In the probe it was 72.7 where a direct cosine on the raw text gave 0.62, because the index embeds its own normalized chunk text. So the floor is applied on the index's scale, and implement must re-check that it behaves on the sourdough question. A missing keyword match shows `text_score` 0 with a placeholder rank, so 0 means "not found".

## Weights

- **Decision**: `CCCTX_TEXT_WEIGHT` and `CCCTX_VECTOR_WEIGHT`, positive numbers with default 1, are passed as each side's `score_weight`. `CCCTX_SEARCH_CANDIDATES` has default 100. All are documented in the README.
- **Rationale**: the probe showed `score_weight` changes the fused order. This meets constitution IV ("configurable with documented defaults").

## Insert path

- **Decision**: `_insert_symbols` stores `search_text` (full, not capped) and no longer calls `VECTOR_EMBEDDING`. Both CLOB binds, `search_text` and then `source`, come last. `EMBED_CHARS` is removed.
- **Rationale**: the index vectorizes and chunks long text itself. Ordering the LOB binds last avoids ORA-24816, as in step 4.

## Corrections measured during implement

The decisions above were revised once the real flask and gin index answered queries.

- **`_` must be a word character.** The default lexer split `url_for` into `url` plus the stopword `for`, so `{url_for}` matched every `url = …` line in `uv.lock`. `ccctx model load` now creates the `CCCTX_CODE_LEXER` preference (`BASIC_LEXER` with `PRINTJOINS '_'`) and builds the index with `LEXER CCCTX_CODE_LEXER`. A probe confirmed that `{url_for}` then matches only real occurrences, in any case.
- **The semantic score is `(1 + cosine) / 2 × 100`.** This was measured against direct cosine on the same rows (for example 57.0 against 0.140). So `similarity = vector_score / 50 - 1`, and the step 4 floor of 0.3 means a score of 65.
- **The floor applies to semantic-only hits in hybrid mode too.** Without it, "recipe for sourdough bread" returned 10 weak matches. Keyword hits are never dropped.
- **Hybrid's keyword side uses ACCUM, not AND.** A natural question contains stopwords (`how`, `are`, `to`), and AND with a stopword matches nothing, which left the routing question with no keyword side. Text mode stays strict AND. Plain alphabetic words are stemmed with `$word`, so `routed` finds `route`. Identifiers and Oracle Text operator words stay literal in braces.
- **One fallback window per file.** Without this rule, dozens of near-identical `uv.lock` windows filled the results.
- **The candidate pool widens under a repository filter**, up to 4000, multiplying by 4 each time, until 10 candidates are in scope. With 100 candidates, flask's 85 mentions of `url_for` crowded a small repository out entirely.
- **Ranks are renumbered** within the repositories searched, so `KEYWORD 1` means first among what you asked for.
- **Building the hybrid index** over about 3,000 symbols took about 8 minutes on the development container.
