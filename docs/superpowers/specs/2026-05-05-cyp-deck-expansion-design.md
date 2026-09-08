# CYP deck expansion — design

> Expand `guides/cyp-2026-05/build-with-oracle-easy.html` from 17 to 28 slides for a ~90-minute workshop, covering 11 additional topics inline with the existing tier structure (beginner → intermediate → advanced). 11 new slides, 3 rewrites, 14 unchanged or renumbered.

## Context

The deck `build-with-oracle-easy.html` is the conference companion for the choose-your-path skills landed across v1/v2/v3 + the OAMP retrofit. It currently runs 17 slides in a tight conference-keynote shape. The user is delivering it as a **~90-minute workshop**, where attendees expect named components and runnable takeaways per topic, not a tightly-pruned narrative.

The user enumerated 11 additional topics that need explicit coverage:

1. Developing on GPU + quantized models — A10 GPU, Ollama or vLLM OpenAI-compat endpoints, Qwen3.5 / Qwen3.6 / Qwopus, model distillation, reasoning traces.
2. Advanced / multi-agent RAG (drawing from `apps/agentic_rag/` and `apps/agent-reasoning/`).
3. Ollama MCP functionalities.
4. In-database embeddings via ONNX models + `onnx2oracle`.
5. picooraclaw + coding agents on OpenAI-compat endpoints.
6. visual-oracledb features — converged DB, in-DB embeddings, semantic search, graphify.
7. Oracle AI SQL generation via Oracle MCP / Claude Code — converged DB cognitive-load reduction.
8. langchain-oracledb + oracleagentmemory value props.
9. Beginner-tier framed presentation around OCI GenAI + langchain-oracledb + RAG via in-DB embeddings (web + pdf).
10. Intermediate-tier framed presentation around Oracle MCP.
11. Advanced-tier framed presentation around oracleagentmemory.

## Goals

- Cover all 11 topics as named, dedicated slides — workshop-grade depth.
- Refresh the three tier ledes (5, 7, 10) so each tier opens with a concrete claim that names its protagonist library/protocol — without sliding into "simple, easy, powerful" cliché framing.
- Keep the deck's existing narrative spine intact (title → stack → tier 1 → tier 2 → tier 3 → demo → Q&A) — new topics are inserted *within* tier sections, not bolted on as a separate "deep-dive" act.
- Preserve all existing slides that already work (1–4, 6, 9, 11, 12, 13, 14, 15, 16, 17 in the current numbering).

## Non-goals

- No new demo flow — slide 26 (current 15) already runs the live demo.
- No CSS / theme / layout-system changes — new slides reuse the existing `slide`, `signal-card`, `section-title`, `section-eyebrow`, `section-lede`, and grid utilities.
- No reordering of unchanged slides — only insertions and the three tier-lede rewrites.
- No content changes to the choose-your-path skills, snippets, or references — this is a deck-only spec.

## Final slide map

★ = new or rewritten. Numbering reflects the expanded deck.

| # | Title (working draft) | Status | Source repo for content |
|---|---|---|---|
| 1 | Build with Oracle. Easy. | unchanged | — |
| 2 | A real, runnable AI app on *your* laptop — not a slide of pseudocode. | unchanged | — |
| 3 | Three paths. *One* skeleton. | unchanged | — |
| 4 | Six moving parts. *Five* are Oracle's. | unchanged | — |
| 5★ | OCI GenAI, `langchain-oracledb`, in-DB embeddings — three pieces, one chat-with-citations pipeline. | **rewrite** of current slide 5 | `apps/agentic_rag/`, `notebooks/agentic_rag_langchain_oracledb_demo.ipynb`, `notebooks/onnx_embeddings_oracle_ai_database.ipynb` |
| 6★ | Same pipeline. PDFs *and* web pages. | **new** | `apps/agentic_rag/src/` |
| 7 | Pick the corpus you already *have* lying around. (Beginner badges) | renumbered from 6, unchanged | choose-your-path/beginner |
| 8★ | Oracle MCP — the model calls *tools*, not *schemas*. | **rewrite** of current slide 7 | choose-your-path/intermediate, `apps/tanstack-shoe-store/` |
| 9 | Stop sending *schemas* to the model. Let it call *tools* instead. (Schemas vs tools deep-dive) | renumbered from 8, light touch | — |
| 10★ | Ollama MCP — same protocol, your model on your hardware. | **new** | Ollama docs + project memory directive on Ollama-first |
| 11★ | AI SQL generation — Oracle MCP + Claude Code = a converged-DB UX every team can adopt. | **new** | `apps/tanstack-shoe-store/` (Select AI), Claude Code SQL-gen behavior |
| 12 | Same agent loop. *Different* SQL surface area. (Intermediate badges) | renumbered from 9, light touch | choose-your-path/intermediate |
| 13★ | `oracleagentmemory` — per-user durable memory, not just a chat log. | **rewrite** of current slide 10 | `notebooks/agent_memory/`, `shared/snippets/oamp_helpers.py`, `shared/references/oamp.md` |
| 14★ | `langchain-oracledb` — what the framework gives you for free. | **new** | `apps/agentic_rag/`, `notebooks/oracle_langchain_example.ipynb` |
| 15★ | In-DB ONNX + `onnx2oracle` — same model, *no* Python embedder process. | **new** (lifts in-DB-ONNX content out of the old slide 10) | `notebooks/onnx_embeddings_oracle_ai_database.ipynb`, `shared/snippets/in_db_embeddings.py` |
| 16 | Oracle stops being *a* store. It becomes *the only* store. (Converged DB) | renumbered from 11, light touch | — |
| 17★ | `visual-oracledb` — semantic search + graphify in one converged surface. | **new** | `apps/oracle-database-vector-search/`, `notebooks/oracle_26ai_unique_features_demo.ipynb` |
| 18★ | Multi-agent RAG — retrieval, reasoning, and tools as separate agents. | **new** | `apps/agentic_rag/` |
| 19★ | Reasoning architectures over small local models. (compact, *not* an official Oracle integration) | **new — half density** | `apps/agent-reasoning/` |
| 20★ | A10 GPU + quantized weights — Qwen3.5 / Qwen3.6 / Qwopus on Ollama and vLLM. | **new** | Project memory: Qwen3.5-35B-A3B default; Ollama-first preference |
| 21★ | Distillation + reasoning traces — turning the big teacher into a small student. | **new** | `apps/agent-reasoning/generate_reasoning_outputs.py`, `split_reasoning.py` |
| 22★ | `picooraclaw` — a coding agent on OpenAI-compat endpoints, Oracle as the storage layer. | **new** | `apps/picooraclaw/` |
| 23 | Each project leans on the same three skills. *Different* app logic. (Advanced badges) | renumbered from 12, light touch | choose-your-path/advanced |
| 24 | Cold → kill → warm. The agent *remembers*. | renumbered from 13, unchanged | — |
| 25 | We walked the whole thing *twice*. Then a third time, cold. | renumbered from 14, unchanged | — |
| 26 | From `git clone` to a chat that cites a PDF — *on stage*. (Live demo) | renumbered from 15, unchanged | — |
| 27 | Things I'll happily get into. *Ask.* (Q&A) | renumbered from 16, unchanged | — |
| 28 | Outro | renumbered from 17, unchanged | — |

## Slide-by-slide spec for the 11 new + 3 rewrite slides

Every spec below targets the existing slide chrome: `.slide` container, `.slide-num`, `.slide-breadcrumb`, `.section-eyebrow`, `.section-title` (with `<em>` for the orange highlight), and either a `.signal-card` or one of the existing card grid layouts. No new CSS classes.

### Slide 5★ — OCI GenAI + langchain-oracledb + in-DB embeddings (BEGINNER LEDE)

**Replaces:** current slide 5 ("Drop a folder of PDFs in. Get a chat that *cites* them back.")

**Job:** Open the beginner tier with a concrete claim that names the three protagonist libraries (OCI GenAI, langchain-oracledb, in-DB embeddings via ONNX) and the artifact they produce together (a chat-with-citations).

**Title:** *"OCI GenAI plus `langchain-oracledb` plus in-DB ONNX. Three libraries. <em>One</em> RAG pipeline."*

**Body:** Three-card grid, one card per library. Each card states its job in one line + one supporting fact:
- **OCI GenAI** — bearer-token chat completion, OpenAI-compat. *One env var, no `~/.oci/config`.*
- **`langchain-oracledb`** — vector store + chat history + JSON Duality, all against the same Oracle connection.
- **In-DB ONNX (`MY_MINILM_V1`, 384-dim)** — embeddings inside the database; no separate embedder process to operate.

**Why this isn't cliché:** the lede names libraries and dimensions, not adjectives. It tells the audience exactly what code they're about to write.

### Slide 6★ — Multi-source RAG (PDFs + web)

**New slide. Inserts after slide 5.**

**Job:** Show the beginner tier covers more than PDFs — the same `langchain-oracledb` ingestion path handles web pages too.

**Title:** *"Same chunking. Same embedder. *Different* loaders."*

**Body:** Two-column code panel. Left = `PyPDFLoader`, right = `WebBaseLoader`. Both feed the same `OracleVS.from_documents(...)` call. Caption underneath: "the corpus shape changes; the storage and retrieval don't."

**Source:** `apps/agentic_rag/` ingestion patterns; one of the corpus pickers in beginner badges.

### Slide 8★ — Oracle MCP lede (INTERMEDIATE LEDE)

**Replaces:** current slide 7 ("One `sk-…` key. *Zero* ceremony.").

**Note:** the bearer-token-auth content from old slide 7 is *not* dropped — it's already covered implicitly by the `OCI_GENAI_API_KEY` env-var convention in slide 5. This rewrite redirects the lede to the intermediate-tier protagonist (Oracle MCP) instead.

**Title:** *"Oracle MCP — the model calls <em>tools</em>, not <em>schemas</em>."*

**Body:** Two-column comparison.
- **Left, "without MCP":** dump the schema in the system prompt (~600 tokens), pray the model doesn't hallucinate a column.
- **Right, "with Oracle MCP":** four named tools — `list_tables`, `describe_table`, `run_sql`, `vector_search`. The model picks the tool; Oracle answers.

Caption: "the agent doesn't memorize your schema. It asks."

### Slide 10★ — Ollama MCP

**New slide. Inserts after slide 9.**

**Job:** Show that MCP isn't OCI-specific — Ollama's MCP client works the same way against the same Oracle MCP server.

**Title:** *"Same protocol. <em>Your</em> model on <em>your</em> hardware."*

**Body:** Diagram: Ollama (local Qwen3.5) → MCP → Oracle MCP server → same four tools as slide 9. One-line code panel showing the Ollama tool-use config that points at the MCP server.

**Caveat block:** "Tool-call quality tracks model quality — Qwen3.5-35B-A3B is the floor we recommend; smaller models hallucinate tool args."

### Slide 11★ — AI SQL generation via Oracle MCP + Claude Code

**New slide. Inserts after slide 10.**

**Job:** Make the converged-DB cognitive-load argument explicit — multiple teams hitting the same DB through their preferred consumption layer (SQL, vector, graph, JSON) means *every* team can use natural language to query, and the LLM doesn't have to learn 5 schemas.

**Title:** *"One database. Five consumption layers. <em>One</em> natural-language interface."*

**Body:** Stat row + caption.
- Stat 1: "5 consumption layers — relational, JSON Duality, vector, graph, Select AI."
- Stat 2: "1 schema — the source of truth lives once, not per-team."
- Stat 3: "0 ETL — no team needs a copy of someone else's data."

Caption: "Claude Code already generates Oracle SQL well. Oracle MCP gives it the schema and the run loop. The cognitive load drops to: 'ask in English, get rows.'"

### Slide 13★ — oracleagentmemory lede (ADVANCED LEDE)

**Replaces:** current slide 10 ("Same model. *No* Python embedder process.")

**Note:** the in-DB-ONNX content from old slide 10 is *not* dropped — it moves to slide 15 as a dedicated topic in the advanced data plane. This rewrite redirects the advanced lede to the advanced-tier protagonist (OAMP) instead.

**Title:** *"`oracleagentmemory` — per-user durable memory. Not just a chat log."*

**Body:** Three-card grid, one card per OAMP primitive that you'd otherwise hand-roll:
- **Threads** — `(user_id, agent_id)` conversations with auto-stamped timestamps. Cold→warm recovery via UUID.
- **Durable memory** — `add_memory` + `search`, scoped to user + agent. Auto-extracted from messages when an LLM is wired in.
- **Context cards** — `thread.get_context_card()` returns a prompt-ready XML synopsis. No prompt-stuffing.

Footer: "the v3 advanced retrofit replaced ~250 LOC of hand-rolled chat-history + session-summary plumbing with ~30 LOC of OAMP wiring. See slide 23."

### Slide 14★ — langchain-oracledb value props

**New slide. Inserts after slide 13.**

**Job:** State what `langchain-oracledb` brings that you'd otherwise hand-write — value-prop framing, not a feature catalog.

**Title:** *"`langchain-oracledb` — the LangChain integration that already <em>knows</em> Oracle."*

**Body:** Four named primitives, one line each:
- **`OracleVS`** — vector store with multi-collection support (RUNBOOKS / GLOSSARY / DECISIONS).
- **`OracleChatMessageHistory`** — chat-history store on the same connection (single-user simple log).
- **`OracleDocLoader` + `OracleTextSplitter`** — load PDFs, web, files; chunk semantically; one connection.
- **JSON Duality view bridge** — read your relational data as documents without a copy.

Caption: "the framework brings the storage; you bring the agent."

### Slide 15★ — In-DB ONNX + onnx2oracle

**New slide. Inserts after slide 14.** Lifts in-DB-ONNX content from the old slide 10.

**Title:** *"Same model. <em>No</em> Python embedder process."*

**Body:** Two-column code panel.
- **Left, "in Python":** `embed_query(text) → list[float]` (the way most projects ship). Has a separate process. Has a separate model file. Has a separate failure mode.
- **Right, "in Oracle":** `SELECT VECTOR_EMBEDDING(MY_MINILM_V1 USING :t AS data) FROM dual`. One connection. One model load (registered via `onnx2oracle`). Same 384-dim output.

Caption: "OAMP and OracleVS share one embedder, one schema, one operational story."

### Slide 17★ — visual-oracledb

**New slide. Inserts after slide 16.**

**Job:** Show the converged-DB story is more than vector — graph, JSON, and SQL share the same store, and they can be queried as one.

**Title:** *"`visual-oracledb` — semantic search + graphify, one connection."*

**Body:** Three-panel grid.
- **Vector** — `VECTOR_DISTANCE(...)` over a 1M-row corpus, IVF or HNSW index.
- **Graph** — `MATCH (n)-[r]->(m)` over property graphs, same schema.
- **SQL Duality** — `SELECT * FROM customer_dv` reading documents as relational rows.

Caption: "RAG, graph traversal, and analytics — same DBA, same backup, same auth."

### Slide 18★ — Multi-agent RAG

**New slide. Inserts after slide 17.**

**Job:** Cover the advanced RAG architecture from `apps/agentic_rag/` — separate agents for retrieval, reasoning, and tool use.

**Title:** *"Retrieval. Reasoning. Tool use. <em>Three</em> agents, one query."*

**Body:** Pipeline diagram with three nodes:
1. **Retrieval agent** — picks the right collection (RUNBOOKS / GLOSSARY / DECISIONS), runs vector search, ranks.
2. **Reasoning agent** — plans the answer using CoT or ReAct over the retrieved context.
3. **Tool agent** — calls Oracle MCP if SQL or fresh-data lookups are needed.

Caption: "the orchestrator (LangGraph in `apps/agentic_rag`) wires them; OAMP carries the conversation state across them."

### Slide 19★ — agent-reasoning (compact, half density)

**New slide. Inserts after slide 18.**

**Job:** Tease, don't deep-dive. Acknowledge `apps/agent-reasoning/` exists, name the architectures, point to the repo. Explicitly tag *not an official Oracle integration*.

**Title:** *"Small models. <em>Big</em> reasoning patterns."*

**Body:** Single card.
- One-liner: "11 cognitive architectures over Ollama — CoT, ToT, ReAct, Reflexion, Self-Refine, and others."
- One-liner: "Reference repo, not an Oracle-shipped library. Useful when your model is small enough that the architecture has to do the heavy lifting."
- Footer link: `apps/agent-reasoning/`.

Half density — no diagram, no code, no stat row. This is intentional: the user explicitly asked for less coverage on this topic.

### Slide 20★ — A10 GPU + Qwen on Ollama / vLLM

**New slide. Inserts after slide 19.**

**Job:** Cover the local-inference plane — A10 (24GB) sizing, Qwen3.5/3.6/Qwopus, INT4 quantization, Ollama vs vLLM.

**Title:** *"24 GB of VRAM. A 35B-param mixture-of-experts. <em>INT4</em> quantization."*

**Body:** Stat row + a thin two-column compare.
- Stat 1: "Qwen3.5-35B-A3B — 35B total, 3B active, 256 experts, 9 active per token."
- Stat 2: "INT4 quantization → ~17.5GB on disk, fits in A10 24GB with headroom."
- Stat 3: "OpenAI-compat endpoints: `ollama serve` *or* `vllm.serve`."

Compare panel:
- **Ollama** — drop-in, serves multiple models, GGUF; best for laptop and small-fleet workshops.
- **vLLM** — paged attention, higher throughput; best for served APIs at scale.

Caption: "the same OpenAI client code (`base_url` + `api_key`) talks to either."

### Slide 21★ — Distillation + reasoning traces

**New slide. Inserts after slide 20.**

**Job:** Cover the "make a small model behave like a big one" pattern using reasoning-trace distillation, drawing from `apps/agent-reasoning/generate_reasoning_outputs.py` + `split_reasoning.py`.

**Title:** *"Big teacher, small student — and the <em>traces</em> in between."*

**Body:** Pipeline diagram.
1. **Teacher** (Qwen3.5-35B or Grok-4) generates a reasoning trace for each question.
2. **`split_reasoning.py`** segments the trace into `(prompt, reasoning, answer)` triples.
3. **Student** (smaller Qwen, e.g. 7B) is fine-tuned on the triples.
4. **Result** — small model produces teacher-shaped reasoning at student-shaped cost.

Caption: "Oracle isn't shipping this — but it's how every workshop attendee should be thinking about deploying small models locally."

### Slide 22★ — picooraclaw

**New slide. Inserts after slide 21.**

**Job:** Show the user's coding-agent fork — picooraclaw — using Oracle as the storage layer behind an OpenAI-compat coding agent.

**Title:** *"`picooraclaw` — a Go coding agent. Oracle is its <em>memory</em>."*

**Body:** Three-card grid.
- **OpenAI-compat I/O** — talks to any endpoint: OCI GenAI, Ollama, vLLM, OpenAI. Bring your own model.
- **Oracle storage layer** — sessions, conversations, tool runs, snapshots. Replaces SQLite/Postgres.
- **CYP-shaped invariant** — DB-as-only-store. Same posture as the advanced choose-your-path tier.

Footer: "snapshot fork of Picoclaw. Sync method: cherry-pick upstream onto a fresh branch + reapply the Oracle layer."

## Touchups to existing slides (light edits, no restructuring)

- **Slide 9** (current 8, schemas-vs-tools): add one-line forward-reference to slide 10 (Ollama MCP) so the audience knows the local-model variant is coming.
- **Slide 12** (current 9, intermediate badges): no copy change; just renumber.
- **Slide 16** (current 11, converged DB): add one-line forward-reference to slide 17 (visual-oracledb).
- **Slide 23** (current 12, advanced badges): no copy change beyond renumber; the OAMP retrofit is already reflected per today's commit.

## Implementation strategy

The deck is a single self-contained HTML file; all CSS and JS live in `<head>` / `<style>` blocks. New slides are HTML inserts only — they reuse existing classes:

- `.slide` + `.slide-num` + `.slide-breadcrumb` (chrome).
- `.section-eyebrow` + `.section-title` + `<em>` (heading block).
- `.signal-card` for ledes; `.grid` + per-card flex containers for content.
- `.code-panel` (existing) for code snippets.
- `.stat-row` (existing) for numbered stat blocks.

Renumbering happens in three places per touched slide: the `<div class="slide-num">NN / 28</div>` block, the `id="slide-NN"` attribute, and the breadcrumb tier-active class. A single pass updates the totals from `/ 17` to `/ 28` everywhere.

The implementation plan (next step, via writing-plans) will sequence these as: (1) global renumber, (2) tier-lede rewrites, (3) new slide insertions in order, (4) light touchups to slides with forward-references, (5) browser smoke (open file, scroll all 28 slides, no overflow), (6) commit.

## Success criteria

- All 11 new topics appear as named slides in the order specified.
- Three tier ledes (5, 8, 13) name their protagonist libraries explicitly without sliding into "simple/easy/powerful" cliché framing.
- The deck still opens to a clean fullscreen scroll-snap presentation in any modern browser; no slide overflows on the project's reference resolution.
- All slide numbers and breadcrumbs are consistent (1/28 through 28/28).
- agent-reasoning (slide 19) is visibly half-density and carries an explicit *not Oracle official* tag.
- The deck commits cleanly with no AI-attribution lines (per global preferences).
