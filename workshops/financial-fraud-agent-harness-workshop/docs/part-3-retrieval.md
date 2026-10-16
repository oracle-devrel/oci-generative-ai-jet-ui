# Part 3: Retrieval with langchain-oracledb

Stored knowledge helps only if the agent can find it again. This Part builds the read path in three steps: a vector store over AML notes and OAMP memories (§3.1), vector search plus cross-encoder rerank (§3.2), and hybrid search with Reciprocal Rank Fusion (§3.3).

## The two retrieval surfaces

| Layer | Strong on | Example |
|---|---|---|
| **Vector + rerank** | meaning | "Where do we store transaction amounts?" |
| **Hybrid (vector + Oracle Text, fused with RRF)** | meaning and exact tokens | "which column holds RATE_BP" |

Both run in the database. No separate vector DB, no Python embedder.

## The knowledge store (§3.1)

The agent searches one table, `AML_KNOWLEDGE_VS`, managed by `OracleVS`. `OracleEmbeddings` calls the same in-database ONNX model as OAMP (`ALL_MINILM_L12_V2`, 384 dimensions), so both share one vector space. The table holds the AML policy notes in `workshop/aml_knowledge.py` plus the valid OAMP memories written as facts (with a `kind` and a `subject`); chat extractions and `tool_output` records are left out. OAMP stays the source of truth: each row reuses its OAMP record id, `sync_knowledge` upserts new or changed rows and deletes stale ones, and `mirror_writes` makes later `write_facts` calls update the table too.

§3.1 also calls `prepare_search` (in `workshop/retrieval.py`), which creates an HNSW index and an Oracle Text index (`AML_KNOWLEDGE_TEXT_IDX`) on the table, makes every fact write also update the table, and returns `rerank(query, candidates, top_k, content_key)`, the in-database cross-encoder (`PREDICTION(RERANKER_ONNX ...)`).

## The FINANCE Demo Schema

`app/scripts/seed.py` creates the `FINANCE` schema with these tables (approximate seed sizes):

| Table | Rows (approx) | What it represents |
|---|---|---|
| `branches` | 60 | Bank branches with `SDO_GEOMETRY` location |
| `merchants` | 140 | Merchants where card transactions occur, with `SDO_GEOMETRY` location |
| `customers` | 2,000 | Bank customers with a 1-100 `risk_rating` |
| `accounts` | 2,650 | Checking / savings / money-market / credit-line accounts |
| `cards` | ~3,000 | Debit / credit / prepaid cards |
| `transactions` | ~23,600 | Card/account transactions incl. seeded AML patterns |
| `loans` + `sar_reports` | 900 + 117 | Loans; Suspicious Activity Reports (compliance-only) |
| `sanctions_screenings` | 431 | Watchlist (OFAC / EU / UN / PEP / adverse-media) name matches with a disposition |
| `beneficial_owners` | 1,206 | Who ultimately owns each SME/CORP customer, per ownership layer |
| `wire_messages` | 1,320 | SWIFT-style detail behind wire transactions (BICs, purpose code) |
| `login_events` | ~7,000 | Digital-banking logins with `SDO_GEOMETRY` location (impossible-travel evidence) |
| `kyc_documents` | ~3,000 | Due-diligence paperwork with expiry dates (the remediation backlog) |
| `case_notes` | ~250 | Investigator narrative behind the SARs |
| `fx_rates` | 630 | Daily USD rates per currency |

Two columns are intentionally surprising — these are exactly the kind of facts a senior engineer remembers and an LLM hallucinates:

- **`transactions.amount_cents`** is in USD cents, not dollars.
- **`customers.risk_rating`** is a 1-100 score, higher means riskier.

The scanner picks both up via `COMMENT ON COLUMN`. Part 2 scans them into memory.

The seed is pre-built; read the `COMMENT ON TABLE` / `COMMENT ON COLUMN` block in `seed.py` to see the domain model in SQL.

## TODO 4: `retrieve_knowledge`

§3.2. Oversample by 4x so the reranker has candidates to reorder, then rerank down to `k`.

The function already splits a `"a,b"` string into a list, builds the `kinds` filter `flt` (`{"kind": {"$in": kinds}}`, or `None` for every kind), turns each result into a hit and reranks. You write one line, the search itself:

`hits = knowledge_vs.similarity_search_with_score(query, k=k * 4, filter=flt)`. It returns `(Document, distance)` pairs; `k * 4` fetches extra candidates for the reranker.

**Solution:**

```python
def retrieve_knowledge(query: str, k: int = 5,
                       kinds: list[str] | None = None) -> list[dict]:
    if isinstance(kinds, str):
        kinds = [s.strip() for s in kinds.split(",") if s.strip()]
    flt = {"kind": {"$in": kinds}} if kinds else None
    hits = knowledge_vs.similarity_search_with_score(query, k=k * 4, filter=flt)
    candidates = [to_hit(doc, distance=float(dist)) for doc, dist in hits]
    return rerank(query, candidates, top_k=k, content_key="body")
```

Each hit has `kind`, `subject`, `body`, `metadata` and `distance`. The checkpoint fails on the stub, on an empty result, on missing keys, when the `kinds` filter is ignored, and when more than `k` hits come back.

## Hybrid search: `hybrid_search_knowledge`

§3.3. Vector search misses exact identifiers such as `AMOUNT_CENTS`; keyword search misses paraphrases. Run both legs over the same table and fuse the ranks:

$$\text{score}(d) = \sum_{\text{leg}} \frac{1}{k + r_{\text{leg}}(d)}$$

$r$ is the 1-based rank in a leg, $k=60$ (`rrf_k`), and a row missing from a leg adds nothing. RRF uses ranks, not scores, so cosine distance and Oracle Text `SCORE` need no calibration.

This function is provided in the notebook (no TODO); run it and compare which search found each result. The code:

```python
def hybrid_search_knowledge(query: str, k: int = 5, rrf_k: int = 60) -> list[dict]:
    vec = [doc for doc, _ in knowledge_vs.similarity_search_with_score(query, k=30)]
    txt = OracleTextSearchRetriever(vector_store=knowledge_vs, k=30).invoke(keyword_terms(query))
    fused = {}
    for leg, docs in (("vec_rank", vec), ("txt_rank", txt)):
        for rank, doc in enumerate(docs, start=1):
            hit = fused.setdefault(doc.id, to_hit(doc, rrf_score=0.0, vec_rank=None, txt_rank=None))
            hit[leg] = rank
            hit["rrf_score"] += 1 / (rrf_k + rank)
    return sorted(fused.values(), key=lambda h: h["rrf_score"], reverse=True)[:k]
```

`keyword_terms` (in `workshop/retrieval.py`) turns the question into search words: it lowercases, drops stop words and splits identifiers at `_`, because the Oracle Text index tokenises there (`which column is RATE_BP?` becomes `column rate bp`). A plain multi-word sentence passed to `CONTAINS` is parsed as a phrase and matches almost nothing.

The demo cell after it asks for `RATE_BP` by name: the keyword search finds `FINANCE.LOANS.RATE_BP` directly, so it ranks first.

## LangChain interop

Part 3 already uses `langchain-oracledb`. Other components of the package:

| Need | `langchain-oracledb` |
|---|---|
| In-database embeddings | `OracleEmbeddings(conn=..., params={"provider": "database", "model": "ALL_MINILM_L12_V2"})` |
| Vector store | `OracleVS(client, embedding_function, table_name, DistanceStrategy.COSINE)` with `similarity_search`, `similarity_search_with_score`, `max_marginal_relevance_search`, `.as_retriever()` |
| Keyword leg | `create_text_index(...)` + `OracleTextSearchRetriever(vector_store=..., k=...)` |
| Hybrid inside the database | `OracleHybridSearchRetriever(vector_store=..., idx_name=..., search_mode="hybrid")` over a `DBMS_HYBRID_VECTOR` index (`create_hybrid_index`) |
| Chat history | `OracleChatMessageHistory` |
| Utilities | `OracleSummary`, `OracleTextSplitter`, `OracleDocLoader`, `OracleSemanticCache` |

- **`OracleVS` owns its table.** It creates a `VECTOR` table (`id`, `text`, `metadata`, `embedding`); that is separate from the OAMP-managed tables from Part 2, which is why `sync_knowledge` mirrors them.
- **The hybrid index is exclusive.** `create_hybrid_index` fails with `ORA-29879` on a table that already carries a separate vector index and an Oracle Text index, as `AML_KNOWLEDGE_VS` does. The hybrid index is both, so it needs its own table.

## Key takeaways: Part 3

- **Vector search alone misses exact tokens.** A user typing `AMOUNT_CENTS` or `ORA-00904` wants the row that contains the string. Fusing a keyword leg with RRF closes the gap.
- **Reranking is one SQL primitive.** `PREDICTION(RERANKER_ONNX USING :q AS DATA1, doc AS DATA2)` runs the cross-encoder in the database (register the model with `app/backend/db/reranker_setup.py`).
- **Oversample before rerank.** A reranker needs candidates to reorder: `k * 4` from the vector search, then rerank to `k`.
- **RRF is rank-based.** Cosine distance and `SCORE(1)` come from different scales; fusing on rank avoids calibrating them.

## Troubleshooting

**`retrieve_knowledge` returns nothing**: `AML_KNOWLEDGE_VS` is empty. Run §2.3 (the scan) and §3.1 first.

**`ORA-29855: error occurred in the execution of ODCIINDEXCREATE`**: the Oracle Text index needs the `CTXAPP` role. The setup grants it; outside the Codespace run `GRANT CTXAPP TO AGENT` as `SYSDBA`.

**The keyword leg is empty**: the query reached `CONTAINS` as a phrase, or the index is stale. Pass the question through `keyword_terms`; `refresh_text_index` syncs the index after writes. `DRG-10599: column is not indexed` means the §3.1 index cell has not run against this database.
