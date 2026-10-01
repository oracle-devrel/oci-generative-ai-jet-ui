# Context Assembly for Agent Memory

Companion to the final article in the multi-tenant agent memory series. Requires Oracle AI Database 26ai. The example uses database rows throughout.

## Series foundation

- [From Prompt to Persistence (Part 1)](https://blogs.oracle.com/developers/from-prompt-to-persistence-part-1-designing-multi-tenant-agent-memory-schemas-for-saas) supplies all ten original tables and their indexes in `schema.sql`.
- [From Prompt to Persistence (Part 2)](https://blogs.oracle.com/developers/from-prompt-to-persistence-part-2-putting-the-multi-tenant-agent-memory-schema-to-work) supplies the Memory Manager, scope inheritance, and the Stripe and infrastructure examples.
- [Persistent Memory and Derived Context](https://blogs.oracle.com/developers/persistent-memory-and-derived-context-a-two-layer-pattern-for-agents) supplies the original Helios-RAG fact, correction, summary, and document text.
- [Hybrid Retrieval](https://blogs.oracle.com/developers/hybrid-retrieval-for-agent-memory-vector-lexical-and-metadata-together) supplies the complete synthetic research corpus: 23 documents and 137 chunks. Its vector and Oracle Text pools, RRF fusion, query expansion, and BGE reranker run in `hybrid_query.sql` and `retrieval.py`.

`source_provenance.json` records source notebook hashes and cell numbers. Seed payloads and identifiers such as `model:helios-rag` and `beir_ndcg10` are preserved. Stable row IDs and fixed UTC seed dates make reruns reproducible; those are explicit adaptations of the earlier UUIDs and execution-time dates. The embedding is still generated from each row's actual content in Oracle.

## Run

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python execute_notebook.py
```

When running interactively, select your notebook kernel and run the first `%pip` cell. It installs the pinned requirements into that kernel environment. If packages already imported in the session are replaced, restart the kernel and run all cells from the top.

Put `DB_USER`, `DB_PASSWORD`, and `DB_DSN` in an ignored repository-root `.env`. A notebook-local `.env` can supply `OPENAI_API_KEY` and `OPENAI_MODEL` for the optional model checks. Neither credentials nor environment values are printed. Set `CONTEXT_RUN_MODEL=1` to rerun the model experiments during notebook execution. Without it, the notebook displays the retained provider results as a recorded run.

The owner needs privileges for tables, indexes, trusted application contexts, VPD, and `DBMS_FLASHBACK`. Use an owner without `EXEMPT ACCESS POLICY`; setup checks this. `prerequisites.sql` describes the grants for an administrator. No teardown runs and no existing table definition is altered. Setup stops if a table has different columns.

### Model prerequisites

`model_setup.py` reuses `ALL_MINILM_L12_V2` and `BGE_RERANKER` if loaded. It downloads Oracle's embedding model when absent. For an absent reranker, first export `BAAI/bge-reranker-base` with Oracle OML4Py and set `RERANKER_ONNX_FILE` to the resulting ONNX file. The Developer Hub's [reranker export notebook](../vecdb/reranking/load-model-for-in-database-reranking.ipynb) documents that conversion. The loader uses `function=regression` and `regressionOutput=output`, preserving native `FIRST_INPUT` and `SECOND_INPUT` attributes. It does not rename them to DATA1/DATA2.

## Notebook steps

1. Load and verify the two in-database models.
2. Create the full original schema where missing, plus `context_compression` and `context_source_ref`. Apply tenant VPD to the explicit table list.
3. Seed the original Stripe, infrastructure, and Helios-RAG examples, and the complete research corpus under its original `tenant_acme` identifier.
4. Additional seed data: add a context budget, four toolbox entries, July history, provenance links, and isolation cases. Provision an identical copy of the research corpus for the earlier `acme` tenant. The original corpus remains present. Jane keeps `user:jane@acme.com`, and the assistant uses `agent:research_v1`.
5. Run actual retrieval and assemble comparison and fact-check windows. KB chunks inherit access and lifecycle from their parent document. Unversioned tables retain null versions in manifests.
6. Exercise budget failures, pointer expansion, current-claim admission, deletion-aware Flashback replay, and FastMCP stdio calls.
7. Inspect or rerun live model experiments, including a stored model compression and a tool fetch for information absent from the initial window.

The default assembler requires the current canonical source of an annotated historical claim at full size. If it cannot fit, assembly fails. A separate controlled ablation disables that requirement to demonstrate omission. It is recorded as an experiment and is not the normal tool-fetch path.

BGE outputs are measured logits. The adapter applies a sigmoid to place them in [0,1] for weighted priority; this is not a calibrated probability of correctness. Ranking scores, code hash, and source dependencies are recorded so replay does not rerun the reranker. The example scans a small seed corpus and does not establish production latency or retrieval quality.

## FastMCP and scope

The standalone package is pinned to `fastmcp==4.0.10`, with `mcp==2.2.0`. A custom provider reads the current scoped toolbox rows. Each executable tool rechecks the active schema and access policy before dispatching through the Memory Manager. Live tool validity uses call time. The recorded assembly timestamp is used when constructing or replaying that window. `issue_refund` remains in the original toolbox but is not advertised because this server has no implemented handler for it.

The stdio process has one scope supplied by the trusted host. Tool arguments cannot select a tenant. Pooled connections set the trusted tenant context on checkout and clear it on return, including failures. A remote HTTP deployment needs authenticated request scope and request-specific manager instances.

Clarification works in legacy handshake mode through `Context.elicit`; protocol `2026-07-28` uses an input-required result and a subsequent call with the user's response. Tests cover accept, decline, cancel, and absent elicitation support in both modes. Other host clients require their own compatibility check. See [FastMCP elicitation](https://gofastmcp.com/servers/elicitation).

## Verification and limits

```sh
python run_checks.py
python model_checks.py  # actual provider calls; requires OpenAI settings
```

`results/verification.json` contains the database and protocol checks. `results/model_verification.json` contains actual provider answers and presence checks. The fact-check answer returned 0.78 but omitted memory citations; this failed the citation check. The missing-detail answer included memory IDs; the comparison answer also omitted them in the latest run. Presence checks do not prove citation support or comparative answer quality.

Replay checks present authorization and deletion for every dependency, including historical annotation sources, current correction sources, parent documents, source events, and stored compressions. It then reads retained rows at the recorded SCN and verifies the request hash. Undo availability is required; no Autonomous Database retention guarantee is made. The trusted deletion workflow can call `store.erase_derived` with source references captured before erasure to cascade through both new tables. Model-response caches contain synthetic text and need the same retention controls as source events in a deployment.
