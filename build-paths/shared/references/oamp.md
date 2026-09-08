# OracleAgentMemory (OAMP) — reference

OAMP is the [`oracleagentmemory` PyPI package](https://pypi.org/project/oracleagentmemory/). It owns the conversational + per-user durable-memory layer that the CYP advanced tier kept hand-rolling in 200-LOC bursts. We adopt OAMP at the advanced tier wherever the use case is "auto-extracted, per-user, retrieved-by-similarity memory." We **don't** push fixed RAG corpora, DDL audits, or tool-success counters through it — those keep their own primitives.

This doc is the decision tree. The wiring is in `shared/snippets/oamp_helpers.py`.

---

## 1. When to use OAMP vs. OracleVS vs. OracleChatHistory vs. SQL table

| Storage need | Primitive | Why |
| --- | --- | --- |
| Conversational message log scoped to (user, agent), with auto-extraction of durable facts and a prompt-ready context card | **OAMP thread** | Threads, message log, extraction, summaries, and retrieval are first-class; we'd otherwise reinvent all four. |
| Per-user durable memory ("Alice leads the EU growth team") that other threads can retrieve | **OAMP `add_memory` / `search`** | OAMP scopes by `user_id` and `agent_id` automatically; the embedding + ANN retrieval is built in. |
| Fixed RAG corpora — runbooks, glossary, decision docs, invoice PDFs — that don't belong to a single user | **`OracleVS` multi-collection** | Not user-scoped, not LLM-extracted; pure document-grounded retrieval. OAMP would muddle scope. |
| Single-user simple chat log (beginner / intermediate tier) where you want full message visibility, no extraction | **`OracleChatHistory`** | A LangChain `BaseChatMessageHistory`; integrates with `RunnableWithMessageHistory` directly. OAMP is heavier than the beginner tier needs. |
| Structured DDL audit (idea 3's `DESIGN_HISTORY`), tool-success counters (idea 2's `TOOL_REGISTRY`), workflow state | **Plain SQL table** | These are relational records, not retrieval targets. OAMP is the wrong shape; OracleVS is overkill. |

### Worked examples

1. **Idea 1 — hybrid analyst.** Conversational state + per-user memory ("Alice runs EU growth, prefers SQL over docs") → **OAMP**. Runbooks / glossary / decisions corpora → **OracleVS** collections (`RUNBOOKS`, `GLOSSARY`, `DECISIONS`).
2. **Idea 2 — self-improving research agent.** Session summary + per-task running context → **OAMP**. `(tool, args, result, score)` rows for similarity retrieval → **OracleVS** (`TOOL_RUNS`). Tool success/fail counters → **plain SQL** (`TOOL_REGISTRY`).
3. **Idea 3 — schema designer.** DDL audit (every `CREATE TABLE` the agent ran) → **plain SQL** (`DESIGN_HISTORY`). The conversation that led to each DDL → **OracleChatHistory** (single user, want full transcript) — OAMP isn't a fit because the demo is "DDL audit and replay," not retrieved memory.
4. **Beginner tier.** Single-user chat over a PDF corpus → **OracleChatHistory** + **OracleVS** (`DOCUMENTS`). OAMP is overkill until you go multi-user.

---

## 2. Canonical recipe (in-DB ONNX + Grok-4 over OCI bearer-token)

The CYP wiring lives in `shared/snippets/oamp_helpers.py`. The full hand-rolled version (for reference / debugging) tracks the OCI developer guide notebook (`notebooks/agent_memory/oracle_agent_memory_developer_guide_oci.ipynb`) — that notebook is the canonical OCI variant. The bearer-token recipe below is the CYP-specific simplification (no `~/.oci/config`, no compartment OCID; just `OCI_GENAI_API_KEY` at us-phoenix-1).

```python
import oracledb
from oracleagentmemory.core import OracleAgentMemory
from oracleagentmemory.apis.thread import Message
from shared.snippets.oamp_helpers import make_oamp_client, make_oamp_thread

conn = oracledb.connect(user=..., password=..., dsn=...)
client = make_oamp_client(conn)            # in-DB ONNX + Grok-4 (if API key set)

USER_ID, AGENT_ID = "alice", "hybrid-analyst-v1"
client.add_user(USER_ID,  "Alice — EU growth lead.")
client.add_agent(AGENT_ID, "Hybrid analyst v1.")

thread = make_oamp_thread(client, USER_ID, AGENT_ID)

# IMPORTANT: call add_messages once per turn, not one big batch — see V4-OAMP-1.
# Auto-extraction counts add_messages() calls, not Message rows; batched calls
# never trigger memory_extraction_frequency.
thread.add_messages([Message(role="user", content="What was Q3 EU revenue?")])
thread.add_messages([Message(role="assistant", content="$4.2M, up 18% YoY.")])

prompt_card = thread.get_context_card()    # XML block of relevant memories
```

Defaults `make_oamp_client` applies:

| Knob | Value | Why |
| --- | --- | --- |
| `embedder` | `_InDBOAMPEmbedder` (`MY_MINILM_V1`, 384 dim) | Same model `OracleVS` uses — keeps embedding space consistent. |
| `llm` | `_GrokOAMPLlm` (Grok-4 via `chat_complete`) — only if `OCI_GENAI_API_KEY` is set | Auto-extraction needs an LLM; the rest of the project already calls Grok the same way. |
| `extract_memories` | `True` if `OCI_GENAI_API_KEY` set, else `False` | No LLM means no extraction; the rest of OAMP still works. |
| `schema_policy` | `"create_if_necessary"` | OAMP creates its tables on first connect. Idempotent on subsequent runs. |

Defaults `make_oamp_thread` applies (track the OCI dev guide notebook):

| Knob | Value | Why |
| --- | --- | --- |
| `memory_extraction_frequency` | `2` | Extract every 2 user turns. |
| `memory_extraction_window` | `4` | Over the last 4 messages. |
| `enable_context_summary` | `True` | Rolling synopsis attached to the context card. |
| `context_summary_update_frequency` | `2` | Refresh summary every 2 turns. |

---

## 3. Auto-extraction tradeoffs

`extract_memories=True` runs an LLM call every `memory_extraction_frequency` user turns over the last `memory_extraction_window` messages. With Grok-4 over OCI bearer-token at the dev-guide defaults (`freq=2`, `window=4`), a 12-turn conversation triggers 6 extra LLM calls. Each is ~600-1200 tokens of input and emits a JSON list of facts.

Cost-per-turn back-of-envelope (Grok-4, us-phoenix-1, current pricing):

```
extra_llm_calls_per_turn = 1 / memory_extraction_frequency      # ≈ 0.5
tokens_per_extraction_call ≈ 1000 in / 200 out                  # ~$0.005 each
extra_cost_per_turn ≈ 0.5 * $0.005 ≈ $0.0025                   # ~$2.50 per 1k turns
```

When to disable:

- **Cost-sensitive demo** with thousands of turns. `extract_memories=False` and call `client.add_memory(...)` manually for the facts you actually want stored.
- **Latency-sensitive UI.** The extraction call is synchronous on `add_messages` when the frequency hits — adds ~1-2s to that turn. If your adapter streams to Open WebUI, this lands on a single non-streaming turn every N user messages. Most users won't notice; some will.
- **No LLM available.** If `OCI_GENAI_API_KEY` is not set, `make_oamp_client` automatically degrades to `extract_memories=False`. You still get threads, manual memories, search, and context cards.

---

## 4. Schema coexistence

OAMP creates its own tables on first connect under `schema_policy="create_if_necessary"`. They live in the **same Oracle schema** as your project's `OracleVS` collections (`RUNBOOKS`, `GLOSSARY`, etc.) and any plain SQL tables you add (`TOOL_REGISTRY`, `DESIGN_HISTORY`). OAMP's table names are prefixed to avoid collisions with project-defined collections.

To inspect the OAMP-managed tables in your DB after first run:

```sql
SELECT TABLE_NAME FROM USER_TABLES
 WHERE TABLE_NAME LIKE 'OAM%' OR TABLE_NAME LIKE 'OAMP%'
 ORDER BY TABLE_NAME;
```

If you want to see exactly which DDL OAMP issues, enable debug logging before constructing the client:

```python
import logging
logging.getLogger("oracleagentmemory").setLevel(logging.DEBUG)
```

The DDL is also visible via the OAMP package source — `python -c "import oracleagentmemory; print(oracleagentmemory.__file__)"` will land you in the install path; the schema definitions live under `core/schema/`.

**No conflicts with `forbidden_imports.txt`.** OAMP uses `oracledb` under the hood — that's the same driver `OracleVS` uses. None of `redis`, `psycopg`, `sqlite3`, `chromadb`, `qdrant_client`, `pinecone`, `faiss` are pulled in.

---

## 5. Cold→warm thread recovery

OAMP's headline feature for the advanced tier: kill the agent process mid-conversation, reopen on a fresh process, and the context card comes back intact. This is the "DB-as-only-store proof" — no in-process state, the full conversation graph (messages + extracted memories + summary) lives in Oracle.

```python
# --- session 1 ---
client = make_oamp_client(conn)
thread = make_oamp_thread(client, USER_ID, AGENT_ID)
# One add_messages() call per turn; see V4-OAMP-1 for why batches break extraction.
thread.add_messages([Message(role="user", content="I lead the EU growth team.")])
thread.add_messages([Message(role="assistant", content="Got it — focus area noted.")])
saved_id = thread.thread_id
# (process exits)

# --- session 2 (fresh process, fresh client, same DB) ---
client = make_oamp_client(conn)
recovered = client.get_thread(saved_id)            # same conversation
print(recovered.get_context_card())                # extracted "Alice — EU growth lead"

# Per-user search across all of Alice's threads:
hits = client.search("growth team",
                     user_id=USER_ID,
                     record_types=["memory"],
                     max_results=5)
```

This is what `verify.py` checks at the advanced tier — write a memory, close the connection, reopen, retrieve. If that round-trips, the DB-as-only-store invariant holds.

---

## 6. Common errors

Findings from the OAMP cold-start friction pass (2026-05-05). New entries get a `V4-OAMP-N` ID matching the cold-start convention.

### V4-OAMP-1 — Batched `add_messages` never triggers memory extraction

**Symptom.** `thread.get_context_card()` returns a populated `<summary>` and `<topics>` but `<relevant_information>` is empty. `SELECT COUNT(*) FROM MEMORY WHERE THREAD_ID = :tid` returns 0 even after 6+ messages with `extract_memories=True` and `memory_extraction_frequency=2`.

**Root cause.** OAMP counts `add_messages()` *calls*, not Message *rows*. A single `add_messages([m1, m2, m3, m4, m5, m6])` is one event, so the freq=2 trigger never fires. The summary path (`enable_context_summary=True`) does work in batch mode because it runs at thread-flush time; the extraction path needs incremental writes.

**Fix.** Call `add_messages()` **once per turn** (one `Message` per call, or at most one user + one assistant per call). Do not buffer entire conversations and flush in one shot.

```python
# WRONG — extraction never fires
thread.add_messages([Message(...), Message(...), Message(...), Message(...)])

# RIGHT — one call per turn
for m in turns:
    thread.add_messages([m])
```

Verified by re-running with per-message calls: MEMORY rows appear at message 2, 4, 6 as expected.

### V4-OAMP-2 — `context_card.formatted_content` is a byte-for-byte alias of `.content`

**Symptom.** Code that expects `formatted_content` to be a Markdown or plaintext rendering (vs. raw XML in `.content`) gets the same XML twice.

**Workaround.** Treat `.content` and `.formatted_content` as the same string. If you need plaintext for an LLM prompt, post-process the XML yourself or just inject the XML — Grok-4 reads it fine.

### V4-OAMP-3 — Batch-written messages share one timestamp

**Symptom.** Every `<message>` in the recovered context card carries the same `timestamp` field. Temporal reasoning ("what did the user say last?") is unreliable.

**Root cause.** Same root cause as V4-OAMP-1 — OAMP stamps a single `add_messages()` call's rows with the call time, not per-message times.

**Fix.** Same as V4-OAMP-1 — one `add_messages()` call per turn. With per-turn calls, OAMP stamps each call distinctly and the recent-messages block sorts correctly.

### V4-OAMP-4 — `RECORD_CHUNKS` has +2 rows above message count (informational)

After 6 messages, `RECORD_CHUNKS` has 8 rows. The 2 extras are OAMP-internal housekeeping (thread metadata + actor profile embeddings). No correctness impact, but factor it into storage planning at scale: budget `messages * 1.3 ≈ chunks`.

---

## 7. Further reading

- **Canonical OCI variant of OAMP** — `notebooks/agent_memory/oracle_agent_memory_developer_guide_oci.ipynb`. The OCI Generative AI embedder + LLM wiring used in `oamp_helpers.py` is a CYP-specific simplification of that notebook.
- **OpenAI variant of OAMP** — `notebooks/agent_memory/oracle_agent_memory_developer_guide.ipynb`. Uses OAMP's bundled `Llm` and the `text-embedding-3-small` string embedder. Skip this one for CYP — we don't ship OpenAI-direct.
- **OAMP benchmarks** — `notebooks/agent_memory/oracle_agent_memory_benchmarks_oci.ipynb`. Useful if a future tier wants to tune `memory_extraction_frequency` against a specific workload.
- **In-DB ONNX embedder reference** — `shared/references/onnx-in-db-embeddings.md`. Same `MY_MINILM_V1` model OAMP and `OracleVS` both use.
- **Bearer-token canonical recipe** — `shared/references/oci-genai-openai.md`. The same `OCI_GENAI_API_KEY` / `us-phoenix-1` path the OAMP LLM wraps.
