# Architecture

```
+--------------------------+        +--------------------------+
|  React UI (frontend/)    | <----> |  FastAPI service         |
|  Vite + Tailwind + FM    |  HTTP  |  /chat /predict /health  |
|                          |        |  /memory/* /observ/*     |
+--------------------------+        +-----------+--------------+
                                                |
                          +---------------------+---------------------+
                          |                                           |
                          v                                           v
              +-----------------------+               +-----------------------+
              |  Agent runtime        |               |  Inference service    |
              |  - Grok 4 (OCI GenAI) |               |  - 92-feature XGBoost |
              |  - 13 tools           |               |  - FeatureRuntime     |
              +-----------+-----------+               +-----------+-----------+
                          |                                       |
                          +-------------------+-------------------+
                                              |
                                              v
              +---------------------------------------------------+
              |  Oracle AI Database (container)                    |
              |  - 49k matches + 47k goals                        |
              |  - PREDICCIONES_FINAL (bulk predictions)          |
              |  - SOCCER_LANGCHAIN_DOCS (LangChain OracleVS)      |
              |  - LangGraph OracleStore step trace               |
              |  - working / episodic / semantic memory           |
              |  - VECTOR(384, FLOAT32) + in-DB ONNX embeddings   |
              |    (ALL_MINILM_L6_V2, 384-dim)                    |
              +---------------------------------------------------+
```

## Components

- `soccer_agent/db.py` — Oracle connection helpers (`get_connection`, `get_admin_connection`).
- `soccer_agent/memory/` — Oracle-backed memory and retrieval:
  - `working.py` — per-session key/value (short-term)
  - `episodic.py` — past conversation turns, vector-searchable
  - `semantic.py` — distilled facts (team/decade), vector-searchable
  - `langchain_hybrid.py` — `langchain-oracledb` `OracleVS` table populated from ML prediction rows and football facts; native hybrid search when available, Oracle Text + vector RRF fallback on Oracle AI Database
  - `oracle_agent_memory.py` — optional `oracleagentmemory` SDK showcase using the same Oracle connection
  - `schema.sql` — DDL for `agent_sessions`, `working_memory`, `episodic_memory`, `semantic_memory`
- `soccer_agent/observability/` — `langgraph-oracledb` step observability:
  - `langgraph_steps.py` — uses `OracleStore` to persist ordered per-turn events (`turn_start`, `grounding_retrieved`, `model_response`, `tool_call`, `tool_result`, `final_response`) under namespace `("soccer-agent", "agent-steps", session_id)`
- `soccer_agent/agent/` — Agent runtime:
  - `embeddings.py` — Python wrapper around Oracle's `VECTOR_EMBEDDING` SQL
  - `grok_client.py` — HTTPS client for OCI GenAI Inference (bearer token, no OCI SDK)
  - `tools.py` — 13 tools: seven infrastructure tools (`sql_query`, `hybrid_retrieve`, `vector_search`, `predict_match`, `lookup_prediction`, `remember`, `recall`) plus six Reto Enseña ML feature tools (`get_elo`, `get_team_form`, `get_h2h`, `get_momentum`, `get_poisson_xg`, `get_tournament_context`) with SQL safety guard
  - `loop.py` — `run_turn`: recall, ground, call Grok, dispatch tools, persist memory and LangGraph OracleDB observability steps
- `soccer_agent/inference/` — Predictions:
  - `bulk.py` — Lookup from `PREDICCIONES_FINAL` for cached rows
  - `live.py` — On-demand 92-feature inference from `models/best_model.pkl`
- `soccer_agent/api/` — FastAPI + static UI, including `GET /observability/{session_id}` for step traces.
- `soccer_agent/cli/chat.py` — Terminal REPL alternative to the web UI.
- `.claude/skills/soccer-workshop-setup/` — One-shot scaffolder skill.
- `.claude/skills/soccer-agent-toolbelt/` — Runtime tools usable from Claude Code (same surface as the FastAPI agent).
- `scripts/` — `setup_db.py`, `init_memory.py`, `load_onnx_model.py`, `load_predictions.py`, `load_langchain_vectors.py`, `embed_match_facts.py`, `showcase_oracle_agent_memory.py`, `verify.py`, `smoke_test.py`.

## Why these choices

- **In-DB ONNX embeddings (via `onnx2oracle`)** — no external embedding service at runtime; Oracle stores and computes embeddings for the soccer schema. Tokenizer is baked into the ONNX graph so `VECTOR_EMBEDDING(MODEL USING :t AS DATA)` works on a plain text CLOB.
- **LangChain OracleDB vector store after ML inference** — once `PREDICCIONES_FINAL` exists, `scripts/load_langchain_vectors.py` turns prediction rows and football aggregates into LangChain `Document` rows in `SOCCER_LANGCHAIN_DOCS`. This shows the model output becoming retrievable knowledge, not just a one-off prediction table.
- **Hybrid retrieval over similarity-only RAG** — `hybrid_retrieve` first tries `OracleHybridSearchRetriever`/HYBRID VECTOR INDEX for Oracle versions that support it, then falls back to Oracle Text + vector similarity fused with reciprocal rank on Oracle AI Database Free. The runtime is hybrid-first: `run_turn` injects LangChain OracleVS grounding before chat history and only falls back to semantic-only memory when the hybrid store is unavailable or empty.
- **LangGraph OracleDB observability without rewriting the agent** — OCI Grok bearer auth still requires the prompt-protocol tool loop, so the runtime is not converted into a LangGraph graph. Instead, `langgraph-oracledb` `OracleStore` records each individual agent step in Oracle for durable observability and replay/debugging.
- **Bearer-token Grok client** — OCI GenAI Inference accepts `Authorization: Bearer sk-...` directly; the full OCI Python SDK is not needed (and doesn't fit bearer auth without OCID/fingerprint/key-pair).
- **Thirteen tools, narrow surface** — same JSON schemas used by the deployed FastAPI agent AND the `soccer-agent-toolbelt` Claude Code skill. Attendees can prototype questions in Claude Code, then know exactly what Grok will see at runtime, including the `hybrid_retrieve` tool that showcases Oracle AI Database vector-store hybrid search versus the semantic-only `vector_search` baseline.
- **Static HTML UI** — no React/Next build step; loads in any browser; tool-trace is collapsible under each reply for the teaching moment.
