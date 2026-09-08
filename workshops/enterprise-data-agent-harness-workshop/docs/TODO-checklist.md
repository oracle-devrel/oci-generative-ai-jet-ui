# Workshop TODO Checklist

**9 hands-on coding TODOs across 11 parts.** Every "true setup" task (Oracle DDL, seed data, ONNX models, DDS policies, scheduler job) was run by the Codespace before you opened the notebook — you don't see it in the workshop notebook unless you open `notebook_complete_with_setup_code.ipynb` (the full-source version for advanced learners).

Each TODO has a **hard-stop assert checkpoint** right below it. If you skip a TODO or get it wrong, the next cell raises an `AssertionError` so you can't accidentally barrel forward with broken state.

---

### Part 1 — Setup ([Guide](part-1-setup.md))

*No TODO.* Just run the imports + `agent_conn` + chat client cells.

### Part 2 — Long-Term Memory with OAMP ([Guide](part-2-oamp-memory.md))

1. Implement `_scan_tables` — mine `ALL_TABLES + ALL_TAB_COMMENTS` into Facts.  **TODO 1**

### Part 3 — Retrieval ([Guide](part-3-retrieval.md))

2. Implement `retrieve_knowledge` — cosine search + rerank.  **TODO 2**
3. Implement `hybrid_rrf_search_memories` — vector + keyword fused via Reciprocal Rank Fusion in one SQL.  **TODO 3**

*(The three-way RRF probe is a demo cell — run it and observe the `r_vec` / `r_txt` ranks.)*

### Part 4 — DBFS Scratchpad ([Guide](part-4-dbfs.md))

*No TODO.* Read the DBFS Python wrapper, smoke-test with `scratch.write` / `scratch.read`.

### Part 5 — Oracle MLE Compute ([Guide](part-5-mle.md))

*No TODO.* Read the `exec_js` helper, run the percentile smoke test.

### Part 6 — Tools & Skills ([Guide](part-6-tools-and-skills.md))

4. Register `tool_run_sql` with the `@register` decorator.  **TODO 4**

### Part 7 — The Agent Loop ([Guide](part-7-agent-loop.md))

5. Implement `agent_turn` — the dispatch loop.  **TODO 5**

*(The three-turn end-to-end demo runs after the assert passes.)*

### Part 8 — Identity-Aware Authorization with DDS ([Guide](part-8-dds-identity.md))

6. Implement `set_identity` — bridge `end_user` / `clearance` into the `EDA_CTX` namespace via the trusted `AGENT.set_eda_ctx` procedure.  **TODO 6**

*(The DDS-aware `agent_turn` wrapper and the two-identity comparison run after the assert.)*

### Part 9 — JSON Relational Duality Views ([Guide](part-9-duality-views.md))

7. Register `tool_get_document` — read a full document by primary key.  **TODO 7**

### Part 10 — Continuous Scans via DBMS_SCHEDULER ([Guide](part-10-scheduler.md))

*No TODO.* The scheduler job + `AGENT_REQUEST_SCAN` procedure are pre-installed. The notebook defines `drain_queued_scans()` and shows how to consume the queue.

### Part 11 — Tool-Output Offload ([Guide](part-11-tool-output-offload.md))

8. Implement `log_tool` — persist the full tool output as an OAMP memory keyed by `tool_call_id`.  **TODO 8**
9. Register `tool_fetch_tool_output` — recover full bytes by `tool_call_id`.  **TODO 9**
