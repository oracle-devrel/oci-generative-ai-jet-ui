# Workshop TODO checklist

`notebook_student.ipynb` has eight TODOs: TODO 1 is an inline prompt, TODOs 2–8 are stubs. Each has one checkpoint cell that prints a single ✅/❌ line and fails on the stub, on trivial returns and on the obvious bug. Each stub's comment block holds its signature, steps and checkpoint. `Run All` is supposed to halt at the first unfinished TODO. Answers: `notebook_complete.ipynb`.

| TODO | Name | Section | Guide |
|---|---|---|---|
| 1 | `QUESTION`: ask the bare model | §1.3 | [part-1-setup.md](part-1-setup.md#todo-1-question) |
| 2 | `recall_memories` | §2.2 | [part-2-oamp-memory.md](part-2-oamp-memory.md#todo-2-recall_memories) |
| 3 | `_scan_tables` | §2.3 | [part-2-oamp-memory.md](part-2-oamp-memory.md#todo-3-_scan_tables) |
| 4 | `retrieve_knowledge` | §3.2 | [part-3-retrieval.md](part-3-retrieval.md#todo-4-retrieve_knowledge) |
| 5 | `retrieve_tools` | §4.1 | [part-4-tools-and-skills.md](part-4-tools-and-skills.md#todo-5-retrieve_tools) |
| 6 | `tool_run_sql` | §4.2 | [part-4-tools-and-skills.md](part-4-tools-and-skills.md#todo-6-tool_run_sql) |
| 7 | `tool_list_skills` | §4.4 | [part-4-tools-and-skills.md](part-4-tools-and-skills.md#todo-7-tool_list_skills) |
| 8 | `agent_turn` | §5.3 | [part-5-agent-loop.md](part-5-agent-loop.md#todo-8-agent_turn) |

§3.3 (`hybrid_search_knowledge`) is provided: run it, no TODO.

Part 6 ([guide](part-6-autonomous-aml-triage.md)) has no TODO: it runs the harness you built.

## Before you start

- [ ] Oracle is reachable and the `FINANCE` schema is seeded (`app/scripts/seed.py`).
- [ ] `ALL_MINILM_L12_V2` is loaded (and `RERANKER_ONNX` if the cross-encoder is provisioned).
- [ ] The identity rules are installed (`app/scripts/setup_deep_security.py`); the Codespace does this during setup.
- [ ] The kernel is the Python 3.11 workshop kernel with the packages from `requirements.txt`.
- [ ] §1.2 preflight is green. Each ❌ row prints its own fix; only a missing `FINANCE` or embedder stops the notebook.

## After the eight TODOs

- [ ] Run the two-turn demo in §5.4 (discovery, live SQL).
- [ ] Open the app at `http://localhost:3000`.
- [ ] Ask *"Which branch regions have the most FLAGGED or BLOCKED transactions?"*
- [ ] Switch the header persona to **Analyst — Europe & Middle East** and re-ask; the rows change.
- [ ] As **Compliance Officer**, ask for Suspicious Activity Reports: all rows. As **Analyst (default)**, ask again: no rows. The database answered differently; nothing in the UI changed.

## Part 6 (capstone)

- [ ] §6.1: read the ledger DDL and build the queue. The cell prints the alerts in the window and the ones it will work (`TRIAGE_LIMIT`).
- [ ] §6.2: read one evidence pack, then the policy and the validator. Unknown decisions become `REVIEW_REQUIRED`.
- [ ] §6.3: run the triage; read the tool trace and the ledger rows.
- [ ] §6.4: read the impact board (the only assumption is `MANUAL_MINUTES_PER_ALERT`), then ask the agent about its own decisions.
- [ ] Set `IGNORE_WATERMARK = False` and re-run §6.1: a scheduled job reports no new alerts instead of re-triaging the book.

## Reference material

Not in the notebook; read as needed: [DBFS](reference/dbfs.md) · [Oracle MLE](reference/mle.md) · [Deep Data Security](reference/deep-data-security.md) · [duality views](reference/duality-views.md) · [tool-output offload](reference/tool-output-offload.md) (the notebook shows offload in §5.5).

To deploy against an Oracle that is not the workshop Codespace, run the same provisioning the Codespace runs: `cd app && python scripts/bootstrap.py && python scripts/seed.py && python scripts/setup_advanced.py && python scripts/setup_deep_security.py`, in that order (`seed.py` drops and recreates `FINANCE`, so `setup_deep_security.py` must follow). `provision.sh` sequences all four and is safe to re-run. See [part-1-setup.md](part-1-setup.md).
