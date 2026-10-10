# Context Assembly for Agent Memory

Companion to the final article in the multi-tenant agent memory series. Requires Oracle AI Database 26ai. The example uses database rows throughout.

## Series foundation

- [From Prompt to Persistence (Part 1)](https://blogs.oracle.com/developers/from-prompt-to-persistence-part-1-designing-multi-tenant-agent-memory-schemas-for-saas) supplies all ten original tables and their indexes in `schema.sql`.
- [From Prompt to Persistence (Part 2)](https://blogs.oracle.com/developers/from-prompt-to-persistence-part-2-putting-the-multi-tenant-agent-memory-schema-to-work) supplies the Memory Manager, scope inheritance, and the Stripe and infrastructure examples.
- [Persistent Memory and Derived Context](https://blogs.oracle.com/developers/persistent-memory-and-derived-context-a-two-layer-pattern-for-agents) supplies the original Helios-RAG fact, correction, summary, and document text.
- [Hybrid Retrieval](https://blogs.oracle.com/developers/hybrid-retrieval-for-agent-memory-vector-lexical-and-metadata-together) supplies the complete synthetic research corpus: 23 documents and 137 chunks. Its vector and Oracle Text pools, RRF fusion, query expansion, and BGE reranker run in `hybrid_query.sql` and `retrieval.py`.

`source_provenance.json` records source notebook hashes and cell numbers. Seed payloads and identifiers such as `model:helios-rag` and `beir_ndcg10` are preserved. Stable row IDs and fixed UTC seed dates make reruns reproducible; those are explicit adaptations of the earlier UUIDs and execution-time dates. The embedding is still generated from each row's actual content in Oracle.

## Database setup

Use Oracle AI Database 26ai Free in Docker, or an existing Oracle AI Database 26ai instance whose administrator can provide the required privileges and resources. The [notebook's environment and connection section](context_assembly_walkthrough.ipynb) has the local Docker commands and administrator steps. The local configuration uses the ARM64 image `container-registry.oracle.com/database/free:23.26.3.0-lite-arm64`, which reports database version `23.26.3.0.0`. Other architectures need a matching image and their own validation run.

FreeSQL cannot run this walkthrough because it does not provide `CREATE MINING MODEL` for loading the required ONNX models or `CREATE ANY CONTEXT` for tenant isolation.

Reuse the existing database user configured as `DB_USER` in the repository-root `.env`, as in the other memory notebooks. The account must already exist, must be non-SYS, and must not have `EXEMPT ACCESS POLICY`. An administrator can run [prerequisites.sql](prerequisites.sql) in the notebook's PDB and enter this username when prompted. The script grants:

- `CREATE SESSION`, `CREATE TABLE`, `CREATE PROCEDURE`, and `CREATE MINING MODEL`;
- `CTXAPP` for Oracle Text and `CREATE ANY CONTEXT` for the trusted tenant context;
- execution privileges on `DBMS_RLS`, `DBMS_FLASHBACK`, and `DBMS_VECTOR`.

The user also needs sufficient quota on its existing default tablespace. The local configuration uses a 1 GB quota and a 128 MB vector memory pool for the HNSW indexes. The lite image starts with `vector_memory_size=0`; the notebook documents the separate administrator configuration and restart. The grants script does not create users or tablespaces or restart the database.

Setup creates the database-wide `memory_ctx` application context bound to the user's package. Reuse its owner if that context already exists. Setup creates missing schema objects and stops if an existing table has different columns. No teardown runs or existing table definitions are altered.

## Connection and models

Keep the existing connection values in an ignored **repository-root** `.env`. If they are not configured yet, add the credentials for your existing user:

```dotenv
DB_USER=<your existing database username>
DB_PASSWORD=<your existing database password>
DB_DSN=localhost:1521/FREEPDB1
```

`FREEPDB1` is the local pluggable database containing the tutorial objects. For an existing instance, use the DSN supplied by its administrator. Credentials and connection values are not printed by the notebook.

`model_setup.py` reuses `ALL_MINILM_L12_V2` and `BGE_RERANKER` when loaded. Otherwise, it downloads Oracle's augmented embedding model and uploads it as a BLOB. The Python host needs outbound HTTPS to Oracle Object Storage; this download does not require a database network ACL. Embeddings have 384 dimensions.

For an absent reranker, export `BAAI/bge-reranker-base` with Oracle OML4Py and set the resulting file's absolute path in an ignored **notebook-local** `.env`:

```dotenv
RERANKER_ONNX_FILE=/absolute/path/to/bge_reranker_base.onnx
```

The [reranker export notebook](../vecdb/reranking/load-model-for-in-database-reranking.ipynb) documents the Linux x86_64 conversion environment and augmented ONNX export. Use its conversion and local validation steps; this walkthrough does not require its VecDB REST, OCI upload, or PAR steps. A Hugging Face weights file alone is not the required model artifact. The loader uses `function=regression` and `regressionOutput=output`, preserving `FIRST_INPUT` and `SECOND_INPUT`.

## Run

Open [context_assembly_walkthrough.ipynb](context_assembly_walkthrough.ipynb) in your Jupyter environment and select a kernel. The first `%pip` cell installs the pinned Python packages into that kernel. If it replaces packages already imported in the session, restart the kernel and run all cells from the top.

For command-line execution from `notebooks/context_assembly`, use an environment with the notebook runner dependencies installed:

```sh
python execute_notebook.py
```

The runner executes the notebook using the current Python interpreter and saves its outputs in the notebook file.

The default run makes no model-provider API calls. Section 8 displays archived provider results and revalidates compression replay only when the referenced compression and source rows are available in the connected database. Otherwise, it labels revalidation as skipped and displays the archived results.

For live model experiments, supply `OPENAI_API_KEY` and `OPENAI_MODEL` in the ignored notebook-local `.env` and set `CONTEXT_RUN_MODEL=1`. These experiments make paid provider calls.

## Notebook steps

1. Load and verify the two in-database models.
2. Create the full original schema where missing, plus `context_compression` and `context_source_ref`. Apply tenant VPD to the explicit table list.
3. Seed the original Stripe, infrastructure, and Helios-RAG examples, and the complete research corpus under its original `tenant_acme` identifier.
4. Add the context budget, four toolbox entries, July history, provenance links, and isolation cases. Provision an identical research corpus for `acme`. Jane uses `user:jane@acme.com`, and the assistant uses `agent:research_v1`.
5. Run hybrid retrieval with vector and Oracle Text candidates, reciprocal rank fusion, and BGE reranking.
6. Assemble comparison and fact-check windows. KB chunks inherit access and lifecycle from their parent document. Unversioned tables retain null versions in manifests.
7. Check tenant isolation, budget failures, pointer expansion, current-claim admission, deletion-aware Flashback replay, and FastMCP stdio calls.
8. Inspect archived model experiments or run live provider calls, including a stored model compression and a tool fetch for information absent from the initial window.
9. Replay the fact-check window, verify the request hash, and close the database pool.

The default assembler requires the current canonical source of an annotated historical claim at full size. If it cannot fit, assembly fails. A separate controlled ablation disables that requirement to demonstrate omission. It is recorded as an experiment and is not the normal tool-fetch path.

BGE outputs are measured logits. The adapter applies a sigmoid to place them in [0,1] for weighted priority; this is not a calibrated probability of correctness. Ranking scores, code hash, and source dependencies are recorded so replay does not rerun the reranker. The example scans a small seed corpus and does not establish production latency or retrieval quality.

## FastMCP and scope

The standalone package is pinned to `fastmcp==4.0.10`, with `mcp==2.2.0`. A custom provider reads the current scoped toolbox rows. Each executable tool rechecks the active schema and access policy before dispatching through the Memory Manager. Live tool validity uses call time. The recorded assembly timestamp is used when constructing or replaying that window. `issue_refund` remains in the original toolbox but is not advertised because this server has no implemented handler for it.

The stdio process has one scope supplied by the trusted host. Tool arguments cannot select a tenant. Pooled connections set the trusted tenant context on checkout and clear it on return, including failures. A remote HTTP deployment needs authenticated request scope and request-specific manager instances.

Clarification works in legacy handshake mode through `Context.elicit`; protocol `2026-07-28` uses an input-required result and a subsequent call with the user's response. Tests cover accept, decline, cancel, and absent elicitation support in both modes. Other host clients require their own compatibility check. See [FastMCP elicitation](https://gofastmcp.com/servers/elicitation).

## Verification and limits

The default notebook path is validated on ARM64 Oracle AI Database Free `23.26.3.0.0` with Python 3.14.2. Validation covers all 11 code cells, tenant isolation, hybrid retrieval, context assembly, all 10 MCP cases, archived compression revalidation, and matching replay hashes. Optional paid provider calls are disabled for this validation. A fresh local database run also covers loading both ONNX models and displaying archived results when compression rows are absent.

After the notebook has created and seeded the schema, standalone checks are available:

```sh
python run_checks.py
python model_checks.py  # actual provider calls; requires OpenAI settings
```

`results/verification.json` contains the database and protocol checks. `results/model_verification.json` contains actual provider answers and presence checks. The fact-check answer returned 0.78 but omitted memory citations; this failed the citation check. The missing-detail answer included memory IDs; the recorded comparison answer also omitted them. Presence checks do not prove citation support or comparative answer quality.

Replay checks present authorization and deletion for every dependency, including historical annotation sources, current correction sources, parent documents, source events, and stored compressions. It then reads retained rows at the recorded SCN and verifies the request hash. Undo availability is required; no Autonomous Database retention guarantee is made. The trusted deletion workflow can call `store.erase_derived` with source references captured before erasure to cascade through both derived tables. Model-response caches contain synthetic text and need the same retention controls as source events in a deployment.
