# Beginner — project ideas

Three takes on the same skeleton: ingest a corpus → embed via OCI Cohere → store in `OracleVS` → chat about it in Open WebUI, powered by Grok 4 on OCI Generative AI. The user's job is to pick **what** they want to chat with. The skeleton is identical across all three.

> The skill maps free-text pitches to the closest of the three. If nothing maps, default to **idea 1 (PDFs)** — it's the most universal demo.

## Stack (same for all three)

| Layer | Choice | Why |
| --- | --- | --- |
| DB | Oracle 26ai Free in Docker | Single command up; vector + relational + JSON in one place. |
| Vector store | `langchain-oracledb` `OracleVS`, single collection | The library you came to learn. |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (384 dim) via `HuggingFaceEmbeddings` (Python-side) | Same model intermediate/advanced register inside Oracle. Local, free, ~90MB weights downloaded once. Lets a user migrate their corpus to tier 2/3 without re-tuning chunks. |
| LLM | OCI GenAI — `xai.grok-4` at `us-phoenix-1` (OpenAI-compat endpoint, bearer-token API key) | Hosted, fast, no GPU on the laptop. Auth is one `OCI_GENAI_API_KEY=sk-...` value — no full OCI tenancy needed. Skill warns about cost during the interview. |
| Chat history | `OracleChatHistory` (custom subclass, since `langchain-oracledb` doesn't ship one) backed by `chat_history` table | Survives kill/restart. |
| UI | **Open WebUI**, pointed at the project's OpenAI-compatible adapter | Polished out of the box, multi-conversation, drop-in for ChatGPT-style interaction. |
| Adapter | A tiny FastAPI app exposing `/v1/chat/completions` over the LangChain chain | Open WebUI talks OpenAI; this is the thinnest glue. |
| Lines | ~350-450 LOC per project | Heavier than the old "two scripts" beginner because the chat loop + history + adapter all need to be there. Still fits in an afternoon. |

The heavy lifting (DB up, store layer, history table) is delegated to `build-paths/skills/oracle-aidb-docker-setup` and `build-paths/skills/langchain-oracledb-helper`. Each project's `SKILL.md` invokes those before writing app code.

---

## 1. PDFs-to-chat

**Pitch.** Drop PDFs in `data/pdfs/`, get a chat UI in Open WebUI that answers questions about them with citations.

**What the user does.**

1. Drop 1-N PDF files into `data/pdfs/`.
2. `python -m pdf_chat.ingest` — chunks (per page + 800-token windows), embeds, stores in `OracleVS`. Idempotent: re-runs only embed new files.
3. `docker compose up open-webui` — Open WebUI on `http://localhost:3000`, pre-configured to talk to the local FastAPI adapter on `:8000`.
4. Chat. Citations include filename + page; click-through opens the PDF at that page (where the OS supports it).

**Layout.**

```
src/pdf_chat/
  __init__.py
  store.py          # from langchain-oracledb-helper
  history.py        # from langchain-oracledb-helper
  _monkeypatch.py   # from langchain-oracledb-helper
  ingest.py         # PDF → chunks → embed → OracleVS
  chain.py          # retriever → grok-4 → cited answer
  adapter.py        # FastAPI: /v1/chat/completions ↔ chain
data/pdfs/
docker-compose.yml  # oracle + open-webui (the latter pinned to ghcr.io/open-webui/open-webui)
.env.example
verify.py
```

**Demo.** Drop the Oracle 26ai PDF release notes, ask "what's new in vector indexes?", get an answer with `[release_notes_26ai.pdf:p.14]` citation.

**Distinct primitive taught.** Multi-page document chunking + page-level metadata for citations. The PDF parser of choice is `pypdf` (lightweight) or `unstructured` (heavier but cleaner) — skill picks `pypdf` by default.

---

## 2. Markdown-notes-to-chat

**Pitch.** Point at your Obsidian / Logseq / dotfile-notes folder. Chat with your second brain.

**What the user does.**

1. Set `NOTES_DIR=/path/to/your/notes` in `.env`.
2. `python -m notes_chat.ingest` — walks the tree, chunks per H2 section, preserves markdown frontmatter as metadata.
3. Open WebUI → chat.
4. Answers cite `notes/area/topic.md#heading-anchor`. Markdown links are resolvable in Obsidian.

**Layout.** Identical to PDF-to-chat, swap `ingest.py` for a markdown walker. ~400 LOC.

**Demo.** "What did I write about distributed locks?" → returns the relevant snippets with file paths + headings.

**Distinct primitive taught.** **Hierarchy-aware chunking.** PDFs are flat by page; markdown has H1/H2/H3 structure. The ingest walker chunks at H2 boundaries (not arbitrary token windows) so retrieved chunks are semantically clean. Frontmatter (`tags: [...]`, `date: ...`) becomes filterable metadata — sets up the user for the intermediate-tier "filter at retrieval" pattern without forcing it yet.

---

## 3. Web-pages-to-chat

**Pitch.** Personal Pocket replacement with chat. Save URLs, ask about them later.

**What the user does.**

1. `python -m web_chat.add "https://example.com/article"` — fetches via `trafilatura` (extracts main content, drops nav/ads), chunks, embeds.
2. Repeat for each URL you want to remember (or pipe a list of bookmarks in).
3. Open WebUI → chat. Answers cite source URLs and page titles.

**Layout.** Same skeleton; `add.py` replaces `ingest.py`, takes a URL on argv instead of walking a folder.

**Demo.** Save 10 articles about a topic over a month. Ask "what's the consensus view on X across what I've read?" → multi-source synthesis with link list.

**Distinct primitive taught.** **Per-document add with rich metadata.** Each `add` is one HTTP fetch + one `add_documents` call (vs the bulk-folder pattern of ideas 1-2). Metadata includes `{"url": ..., "fetched_at": ..., "title": ..., "byline": ...}` — perfect setup for ranking by recency or filtering by author later.

---

## Why these three (and why in this order)

The point of beginner is to teach the skeleton, not surprise the user with three different architectures. All three have:

- The same `store.py` (output of `langchain-oracledb-helper`).
- The same `chain.py` (retriever → Grok 4 → cited prompt).
- The same `adapter.py` (FastAPI wraps the chain into `/v1/chat/completions`).
- The same Open WebUI pointing at the adapter.

What differs is one file: `ingest.py` (or `add.py`). The user picks based on **what corpus they have lying around**, not based on what they want to learn — they'll learn the same thing either way. By idea 3, they should be able to write a fourth ingest module from scratch (RSS feed, code repo, email export) without the skill.

Order is deliberate:
1. **PDFs** is the canonical "RAG demo" people recognize from blog posts. Lowest activation energy.
2. **Markdown** is the most personal — your own notes — so it's the most rewarding to chat with. Slightly more involved (hierarchy-aware chunking).
3. **Web pages** introduces the per-add pattern instead of bulk ingest. The most flexible long-term but the least "shiny on first run."

---

## What the skill won't scaffold

- **No multi-user.** Open WebUI's auth is trivially defeatable when you're running it on `localhost`. Single-user only at this tier.
- **No agent / tool-calling.** The chain is retrieve-then-generate, no MCP, no `bind_tools`. Tier 2's job.
- **No hybrid (vector + BM25) retrieval.** Pure vector. Hybrid is intermediate.
- **No notebook by default.** Beginner output is the project itself; if the user wants to walk through it cell-by-cell, they ask, and the skill copies `shared/templates/notebook.template.ipynb`.
- **No self-hosted LLM.** OCI GenAI Grok 4 only. If the user has no OCI tenancy, the skill stops and points them at the OCI free trial signup. Earlier versions allowed Ollama as a fallback at this tier — that's gone, on purpose, so the user gets the production-feeling stack on day one.

---

## What you get (sanity check)

By the time `verify.py` reports OK, the user has:

- A healthy Oracle 26ai Free container.
- A populated `OracleVS` collection (or empty, if they haven't run `ingest` yet — verify.py uses a temp collection, not the real one).
- A working FastAPI adapter on `:8000`.
- Open WebUI on `:3000` already pointed at the adapter.
- A README with the screenshot slot, the "Why Oracle" paragraph, and the run-locally instructions.

That's the deliverable. Not a tutorial — a thing that works, ready for a 30-second demo recording.
