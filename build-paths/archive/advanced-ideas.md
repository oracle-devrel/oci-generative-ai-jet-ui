# Advanced — project ideas

Eight projects where Oracle AI DB is the **only** state store. The advanced skill *refuses* to scaffold Redis, Postgres, SQLite, ChromaDB, FAISS, Qdrant, Pinecone, or filesystem state — that constraint is the whole point.

The user has built agents before. They know what episodic memory is. The skill picks one of these (or accepts a custom pitch that fits the constraint) and builds it real.

---

## 1. Personal research agent

**Pitch.** Ingest papers, build a citation graph, answer questions episodically (it remembers what you've already read).

**Features used.** Vector search · Hybrid search · Property graph · Agent memory tables.

**Shape.**
- Ingestion pipeline: PDFs → chunks → vectors + metadata.
- Graph: papers ↔ citations (entity + edge tables, Python BFS for n-hop).
- Memory layer: 6 memory tables from `apps/finance-ai-agent-demo/backend/memory/manager.py`.
- Agent loop: retrieve (vector + 1-hop graph expansion) → reason → write summary back to `summary_memory`.
- Notebook + Gradio UI showing: chat with the agent, browse the citation graph, inspect what's in memory.

**~2000 lines. Notebook mandatory.**

---

## 2. Code-review agent with auditable history (the JSON Duality showcase)

**Pitch.** Watches a repo, reviews PRs, remembers prior reviews. Agent persists nested JSON; humans run SQL analytics on the same data.

**Features used.** Vector search · **JSON Duality views (the headline)** · Agent memory.

**Shape.**
- Schema: `review` + `review_file` + `review_finding` (per `json-duality.md`).
- View: `review_dv` exposes them as nested JSON.
- Agent: produces a JSON review per PR; writes through `review_dv`; reads taste-history through the same view.
- Dashboard tab in Gradio: runs `SELECT severity, COUNT(*) FROM review_finding GROUP BY severity` and a "most-flagged files" query against the same data.
- Notebook proves duality: write JSON in cell 4, see it as relational rows in cell 5, in the same transaction.

**~1500 lines. Notebook mandatory.**

---

## 3. Email triage agent

**Pitch.** Read an inbox export, classify by intent, remember sender context (preferences, prior asks, relationships).

**Features used.** Vector search · Entity memory · Hybrid search · Optional ONNX in-DB embeddings (sensitivity).

**Shape.**
- Ingestion: `.mbox` or Gmail Takeout export → embed bodies, extract entities (sender, mentioned-people, asks).
- Entity memory: per-person row with vector embedding of their "voice" (concatenated past messages).
- Triage agent: for new email, retrieve sender context + similar past emails + relationship-graph neighbors, classify intent, draft reply.
- Optional: register an in-DB ONNX embedding model so email content never leaves the DB.

**~1800 lines. Notebook mandatory.**

---

## 4. "Translate-this-toy-agent-to-Oracle" path

**Pitch.** User points at an existing toy agent (smolagent, langgraph demo, autogen quickstart). The skill reads it, identifies its storage layer, replaces it with Oracle.

**Features used.** Whatever the original used — translated. Vector store → `OracleVS`. Conversation history → `OracleChatMessageHistory`. Tool log → DB table. Entity memory → entity-memory pattern.

**Shape.**
- The skill reads the user-supplied source, builds a translation plan, asks for approval, then patches.
- Result: same agent, Oracle backing it. Notebook shows the *before* and *after* working identically from the user's perspective.

**Variable size — depends on source. Notebook mandatory.**

This idea is also a *recruiting tool*: it's how someone with a popular agent demo on GitHub gets to brag "now it runs on Oracle AI DB" with one PR.

---

## 5. DevDay-style demo (pick-3-features)

**Pitch.** Pick any 3 features from `shared/references/visual-oracledb-features.md` and build a demo that genuinely uses all 3. Optimized to look great in a 5-minute live demo.

**Features used.** User picks. Skill enforces "all 3 features must actually be exercised in the demo path" (verify checks each).

**Shape.** Variable. The skill scaffolds an outline based on the user's 3 picks, citing the reference docs for each, and the Gradio app has a tab per feature.

**~2000-2500 lines. Notebook mandatory.**

---

## 6. Personal CRM agent

**Pitch.** Log every interaction with people you know (calls, emails, meetings, DMs). Before any new interaction, ask the agent "what's the state of my relationship with X?" — get a brief that pulls from entity memory, recent threads, open asks, and shared context with mutual contacts.

**Features used.** **Entity memory (the headline)** · Property graph (Person ↔ shared-meeting ↔ Person) · Vector search.

**Shape.**
- Entity table: one row per person with embedding of concatenated past interactions, plus structured fields (`open_asks`, `last_seen`, `relationship_type`).
- Graph: people connected by meetings/emails they were both in (Python BFS to find warm intros).
- Agent loop on "prep for meeting with X": retrieve entity memory + recent threads with X + 1-hop graph neighbors who've talked about similar topics → produce a one-page brief.
- Notebook + Gradio: log five fictional interactions, then run the meeting prep on each. Watch the brief get richer over time.

**~1900 lines. Notebook mandatory.**

This is the entity-memory showcase the way idea 2 is the JSON-duality showcase.

---

## 7. Long-running project copilot (workflow memory)

**Pitch.** Drives a multi-week project — writing a book, building a side project, planning a wedding. The agent persists project state (chapters, milestones, blockers, decisions) across sessions, so every "good morning" picks up exactly where you left off.

**Features used.** **Workflow memory (the headline)** · Summary memory · Vector search.

**Shape.**
- Workflow table: one row per active project with a JSON CLOB holding the full state machine (current phase, completed milestones, open blockers, last decision, next action).
- Summary memory: at the end of each session, agent writes a 3-sentence "where we're at" summary; each new session retrieves the latest one before doing anything else.
- Agent loop: every turn — read workflow row, plan next move, execute (write a paragraph, refine an outline, add a TODO), update workflow row in the same transaction.
- Notebook + Gradio: simulate a 5-day project arc. Show the workflow row mutating; show how kill/restart preserves everything.

**~1700 lines. Notebook mandatory.**

This is the workflow-memory showcase. It also doubles as a real-world template for any agent that runs *over time* rather than per-session.

---

## 8. API integration scout (toolbox + execution-log showcase)

**Pitch.** Agent reads an OpenAPI spec or MCP server descriptor, registers each endpoint as a tool in its `toolbox_memory`, then chains tool calls to fulfil user goals ("get me London's weather, translate it to Japanese, save the result"). Every call is logged with inputs/outputs/latency in `tool_execution_log`.

**Features used.** **Toolbox memory + tool execution log (the headline)** · Vector search · Episodic memory.

**Shape.**
- Toolbox table: one row per tool, with name + JSON schema + provenance (which spec it came from).
- Execution log table: one row per tool call (run_id, tool, args JSON, result JSON, latency, status).
- Agent loop: parse user goal → vector-search the toolbox for matching tools → plan a chain → execute each → log → return.
- Vector-search the execution log: "have I called something like this before?" — past calls become few-shot examples for the planner.
- Notebook + Gradio: register two real tools (e.g. `wttr.in` for weather + a free translate API). Show the agent chain three calls in one turn; show the execution log fill up; demonstrate the planner reusing a past chain.

**~2100 lines. Notebook mandatory.**

This is the toolbox-memory showcase. It's also the most "agentic" of the eight — closest to AutoGPT/SmolAgents in shape, but with full Oracle backing.

---

## What the skill won't scaffold

- Anything storing state outside Oracle. Hard refusal — the verify step greps for forbidden imports.
- Multi-user auth / ACLs / role-based access. Out of scope.
- Production hardening (rate limits, autoscaling, observability stack). The user can layer that on after.
- Agentic systems with browser automation / OS-level tool use. Tool *registry* is in scope; tool *execution* of arbitrary OS calls is not.
