---
name: soccer-agent-toolbelt
description: Soccer analytics agent toolbelt. Gives Claude Code direct access to the Oracle-backed match data, ML predictions, and three-tier memory. Use when answering questions about football matches, building on the soccer agent, or exploring the World Cup dataset.
---

# Soccer Agent Toolbelt

You have 13 tools available. Invoke each via the dispatcher with JSON args.

## Hybrid-first rule for coding agents

When you are building, debugging, or demoing the agent, treat `hybrid_retrieve` as the default retrieval path for explanatory grounding. It is the workshop showcase: model prediction documents plus football facts stored in Oracle through `langchain-oracledb` `OracleVS`, retrieved with native hybrid search when possible or Oracle Text + vector reciprocal-rank fusion on Oracle AI Database Free.

Use `vector_search` deliberately as the semantic-only baseline over `semantic_memory` when you want to contrast "plain vector similarity" with hybrid retrieval. Do not replace `hybrid_retrieve` with `vector_search` in the agent loop, UI demos, or final Grok chat unless the LangChain OracleVS store is unavailable.

## LangGraph OracleDB observability rule

Every live `/chat` turn should leave an ordered step trace in Oracle through `langgraph-oracledb` `OracleStore`, under namespace `("soccer-agent", "agent-steps", session_id)`. Use this for observability/debugging: it records `turn_start`, `grounding_retrieved`, each `model_response`, each `tool_call`, each `tool_result`, and `final_response` or `tool_budget_exhausted`.

Inspect it via the API after a chat turn:

    curl http://localhost:8000/observability/<session_id> | uv run python -m json.tool

Or from Python:

    uv run python - <<'PY'
    from soccer_agent.observability.langgraph_steps import list_steps
    for step in list_steps("<session_id>"):
        print(step.value["step_index"], step.value["event_type"], step.value.get("tool_name"))
    PY

If this returns no rows after a real chat turn, run `uv run python scripts/init_memory.py` and `uv run python scripts/verify.py`; the verifier must report `langgraph-oracledb OracleStore observability setup`.

## Tools

### `sql_query`
Run a read-only SELECT against the soccer schema.
Allowed tables: MATCH_RESULTS, GOALSCORERS, SHOOTOUTS, WC2026_VENUES, PREDICCIONES_FINAL, SOCCER_LANGCHAIN_DOCS, VW_COMPETITIVE_MATCHES, VW_TEAM_STATISTICS, AGENT_SESSIONS, WORKING_MEMORY, EPISODIC_MEMORY, SEMANTIC_MEMORY.
Args: `{"sql": "<SELECT statement>"}`

### `vector_search`
Semantic-only similarity over distilled facts in `semantic_memory`. The embedding is computed in-database via `VECTOR_EMBEDDING(ALL_MINILM_L6_V2 USING :t AS DATA)` — no external embedding API call is made. Use this to show the baseline that only ranks embedded fact summaries; it does not search cached ML prediction documents.
Args: `{"query": "<text>", "limit": 5, "fact_type": "team_decade"}`

### `hybrid_retrieve`
Default evidence retrieval path. Hybrid retrieval over the LangChain OracleVS table `SOCCER_LANGCHAIN_DOCS`, populated by `langchain-oracledb` after ML inference. It combines ML prediction documents and football facts with native HYBRID VECTOR INDEX when available, or Oracle Text + vector reciprocal-rank fusion on Oracle AI Database Free. Prefer this before `vector_search` for any explanation that Grok or a coding agent will use.
Args: `{"query": "Spain Brazil World Cup prediction", "limit": 5, "search_mode": "hybrid"}`

### `predict_match`
On-demand 92-feature XGBoost inference for current or hypothetical matches.
Args: `{"home_team": "Spain", "away_team": "Brazil", "neutral": true}`

### `get_elo`
FootballElo rating for one team, including tournament-tier ratings.
Args: `{"team": "Spain"}`

### `get_team_form`
Rolling and weighted recent form plus goal averages.
Args: `{"team": "Spain", "n": 10}`

### `get_h2h`
Head-to-head record from `team_a`'s perspective.
Args: `{"team_a": "Spain", "team_b": "Brazil"}`

### `get_momentum`
Streaks, unbeaten run, clean-sheet rate, comeback rate, draw tendency, and blowouts.
Args: `{"team": "Spain", "n": 15}`

### `get_poisson_xg`
Poisson expected-goals lambdas and outcome probabilities.
Args: `{"home_team": "Spain", "away_team": "Brazil", "n": 20}`

### `get_tournament_context`
World Cup, continental, qualifying, friendly, and big-game context for one team.
Args: `{"team": "Spain"}`

### `lookup_prediction`
Precomputed prediction from PREDICCIONES_FINAL.
Args: `{"home_team": "Spain", "away_team": "Brazil"}`

### `remember`
Write a fact to semantic memory.
Args: `{"fact_type": "...", "subject_key": "...", "summary": "...", "source": {}}`

### `recall`
Recent N turns of episodic memory for the current session.
Args: `{"limit": 8}`

## How to invoke

From the repo root with the uv env active:

    uv run python .claude/skills/soccer-agent-toolbelt/tools/run_tool.py <tool> '<json args>' [--session SID]

Examples:

    uv run python .claude/skills/soccer-agent-toolbelt/tools/run_tool.py sql_query \
        '{"sql":"SELECT home_team, away_team FROM match_results WHERE tournament = '\''FIFA World Cup'\'' AND ROWNUM <= 5"}'

    uv run python .claude/skills/soccer-agent-toolbelt/tools/run_tool.py lookup_prediction \
        '{"home_team":"Spain","away_team":"Brazil"}'

    uv run python .claude/skills/soccer-agent-toolbelt/tools/run_tool.py hybrid_retrieve \
        '{"query":"Spain Brazil World Cup prediction evidence","limit":3}'

Contrast it with the semantic-only baseline when teaching the difference:

    uv run python .claude/skills/soccer-agent-toolbelt/tools/run_tool.py vector_search \
        '{"query":"Spain Brazil World Cup prediction evidence","limit":3}'

Expected contrast: `hybrid_retrieve` can return `doc_type=prediction` rows from `PREDICCIONES_FINAL` with a `retrieval_mode` such as `native_hybrid` or `fallback_rrf`; `vector_search` returns only distilled facts from `semantic_memory`. That difference is the Oracle AI Database vector-store showcase.

The dispatcher prints the result as a single JSON line to stdout. Tool surface mirrors `soccer_agent/agent/tools.py` exactly — same schemas as the deployed FastAPI agent uses.

## Adding your own tool

If you want to add a 14th tool (e.g. one that reads team stats, schedules a future match, or writes to a custom table):

1. Append a new schema to `TOOL_SCHEMAS` in `soccer_agent/agent/tools.py`.
2. Add a `if name == "your_tool":` branch in `dispatch(...)`. Return a JSON-serializable dict; the loop will surface it back to the model.
3. The `soccer-agent-toolbelt` dispatcher (this skill) and the FastAPI agent both pick it up automatically — they share the same `TOOL_SCHEMAS` list.

## Pitfalls when building on Oracle AI Database

These are the sharp edges we hit shipping the workshop. They aren't theoretical — every one bit a real session.

### python-oracledb (3.x)

- **`IS JSON` CLOBs auto-decode to Python dict/list.** `json.loads(value)` on a column declared `CLOB CHECK (... IS JSON)` raises `TypeError: the JSON object must be str, bytes or bytearray, not dict` because the driver already parsed it. Guard with `isinstance(val, (str, bytes, bytearray))` before decoding.
- **LOB locators die after connection close.** If you fetch CLOB rows inside `with get_connection() as conn: ...` and then build dataclasses or call `.read()` AFTER the `with` block exits, you get `DPY-1001: not connected to database`. Materialize CLOBs INSIDE the `with` block:
  ```python
  with get_connection() as conn:
      cur = conn.cursor()
      cur.execute(...)
      rows = [
          {c: (v.read() if hasattr(v, "read") else v)
           for c, v in zip(cols, row)}
          for row in cur.fetchall()
      ]
  return rows
  ```
- **Pass float32 vectors as `array.array('f', list)`, not numpy ndarrays.** `oracledb` does not bind numpy directly to `VECTOR` columns.
- **`load_dotenv()` with no args needs a stack frame.** If you pipe Python to stdin (`uv run python - <<EOF`), `find_dotenv()` raises `AssertionError`. Pass an explicit path: `load_dotenv(Path.cwd() / ".env")`.

### Vector, hybrid search, and observability

- **Hybrid-first default.** For agent grounding, UI demos, and final Grok answers, use `hybrid_retrieve` first so the answer can cite cached ML prediction documents and football facts from the LangChain OracleVS vector store. Use `vector_search` as a semantic-only comparison or fallback, not as the primary path.
- **Observe the loop, not just the final answer.** `soccer_agent.observability.langgraph_steps` stores every turn/tool step with `langgraph-oracledb` `OracleStore`. `GET /observability/{session_id}` is the fastest proof that the agent persisted its execution path.
- **Lower distance is better.** `ORDER BY VECTOR_DISTANCE(embedding, :q, COSINE) ASC` (ascending is the default; just don't put `DESC`).
- **Use `FETCH FIRST :n ROWS ONLY`**, not `LIMIT`. `LIMIT` is not valid Oracle SQL.
- **Bind the query vector once.** Don't compute `embed_one(query)` twice — call it once and reuse the `array.array`.
- **Refresh `SOCCER_LANGCHAIN_DOCS` after model changes.** Run `uv run python scripts/load_langchain_vectors.py --reset` after `scripts/load_predictions.py` so hybrid retrieval reflects the latest `PREDICCIONES_FINAL` probabilities.
- **HYBRID VECTOR INDEX is optional on Oracle AI Database Free.** `hybrid_retrieve` falls back to Oracle Text + vector reciprocal-rank fusion if native `OracleHybridSearchRetriever` support is unavailable.

### Schema and grants

- **`CREATE MINING MODEL`** is required for `DBMS_VECTOR.LOAD_ONNX_MODEL`. Workshop setup grants it; if you re-create the user manually, add the grant.
- **`DBMS_VECTOR` is already `EXECUTE` to `PUBLIC`** on Oracle AI Database Free; do NOT try to grant it explicitly — SYSTEM lacks `GRANT ANY OBJECT PRIVILEGE` and you'll hit `ORA-01031`.

### In-DB ONNX embedding model

- **Model name in SQL is uppercase with underscores** (e.g. `ALL_MINILM_L6_V2`), NOT the HuggingFace path. Set the model name via the `ORACLE_EMBED_MODEL` env var.
- **Vanilla HuggingFace ONNX exports don't work.** Oracle requires the tokenizer baked into the graph; otherwise `VECTOR_EMBEDDING(...)` returns `ORA-54426: Tensor "input_ids" contains multiple dimensions (2) of variable size`. Use the `onnx2oracle` PyPI package (not `oml4py`, which is a 4-file stub on PyPI).
- **Embedding dim must match the `VECTOR(384, FLOAT32)` column type.** If you switch to `all-mpnet-base-v2` (768 dims), update the schema too.

### OCI GenAI Inference (Grok 4)

- **Bearer-token auth (sk-...) works against `/actions/chat` and `/actions/embedText` only.** The control plane (`https://generativeai...`) rejects the bearer key — you can't list models with it. Look in the OCI Console for the model catalog.
- **Compartment OCID is required in the request body**, not just for auth. Always include `servingMode.compartmentId` (the workshop's `grok_client.py` does this).
- **Native tool calling (the `tools` array) returns HTTP 400** on every model tested with this auth path. Use the prompt-protocol pattern: append tool schemas to the system message, instruct the model to emit `{"tool": "...", "args": {...}}` as a single JSON object when calling a tool, parse it out of the response text. See `soccer_agent/agent/grok_client.py:_inject_tool_protocol` and `_parse_tool_calls`.
- **`role: "tool"` messages get rejected without `toolCallId`.** Since the bearer-auth endpoint never emits a `toolCallId`, route tool results back as `role: "system"` messages. Skip any persisted `role: "tool"` turns when rebuilding the message list for the next iteration — they will break the next API call.
