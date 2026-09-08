# Workshop TODO Checklist

**9 hands-on coding TODOs across 12 parts.** Every "true setup" task (Oracle
DDL, ONNX model load, seed data) was run by the Codespace before you
opened the notebook (`app/scripts/bootstrap.py`, `onnx_setup.py`,
`seed_supplychain.py`). The workshop notebook never re-runs them — you can
focus on the agent-wiring code instead.

Each TODO has a **hard-stop assert checkpoint** right below it. If you
skip a TODO or get it wrong, the next cell raises an `AssertionError` so
you can't barrel forward with broken state.

Two notebooks ship:

| Notebook                                                                  | When to open                                                               |
| ------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| [`workshop/notebook_student.ipynb`](../workshop/notebook_student.ipynb)   | Your working notebook — 9 blank stubs + the assert checkpoints             |
| [`workshop/notebook_complete.ipynb`](../workshop/notebook_complete.ipynb) | The same notebook with all 9 TODOs filled in — open this when you're stuck |

---

### Part 1 — Setup & connectivity ([guide](part-1-setup.md))

_No TODO._ Pick the LLM provider, validate credentials, open three Oracle
connections. Just run the cells top-to-bottom.

### Part 2 — In-DB embeddings ([guide](part-2-embeddings.md))

1. **TODO 1** — wire up `OracleEmbeddings` against the pre-loaded
   `ALL_MINILM_L12_V2` ONNX model.

### Part 3 — `OracleVS` — vector knowledge base ([guide](part-3-vector-store.md))

2. **TODO 2** — instantiate `OracleVS` against the pre-seeded
   `supplychain_demand` table.

### Part 4 — `AsyncOracleStore` — long-term cross-thread memory ([guide](part-4-store.md))

3. **TODO 3** — instantiate the store with an HNSW vector index on the
   `"note"` field and call `.setup()`.

### Part 5 — `AsyncOracleSaver` — per-thread checkpoints ([guide](part-5-saver.md))

4. **TODO 4** — instantiate the saver and call `.setup()`.

### Part 6 — `OracleSemanticCache` ([guide](part-6-cache.md))

5. **TODO 5** — build a `ChatOpenAI(cache=semantic_cache, …)`, invoke
   twice with the same prompt, time both calls.

### Part 7 — Naive vs semantic search ([guide](part-7-search-comparison.md))

6. **TODO 6** — implement the literal-substring vs vector-search
   comparison. The literal search should find **0** matches; the
   semantic search should find the relevant football SKUs.

### Part 8 — `demand_analyst` ([guide](part-8-demand-analyst.md))

7. **TODO 7** — implement `search_demand_reports(query)` and compile
   the agent with `create_agent(..., name="demand_analyst")`.

### Part 9 — `policy_agent` ([guide](part-9-policy-agent.md))

8. **TODO 8** — implement `get_planner_policy()` and async
   `get_user_memory(user_id)`, then compile the agent.

### Part 10 — Supervisor + end-to-end run ([guide](part-10-supervisor.md))

9. **TODO 9** — build the `create_supervisor` graph, compile it with
   **both** `checkpointer=saver` and `store=agent_store`, and invoke
   with a planner request that includes `user_id=priya`. The final
   answer must reference both the policy threshold _and_ Priya's
   saved preference.

### Part 11 — `OracleChatMessageHistory` ([guide](part-11-chat-history.md))

_No TODO._ A standalone primitive, separate from the LangGraph loop.

### Part 12 — Teardown

_No TODO._ Close the three connections.
