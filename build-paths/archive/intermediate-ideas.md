# Intermediate — project ideas

Eight RAG-shaped projects. Each lands a working chatbot with a UI, persistent chat history, and hybrid retrieval — all on Oracle. The user has built RAG before (probably with FAISS or Chroma); this is them rebuilding it on Oracle and OCI GenAI.

The skill asks the user to pick one. Free-text pitches get mapped to the closest. If nothing maps well, the skill picks idea 1 (PDF-RAG) as the safest default.

---

## 1. PDF-RAG chatbot

**Pitch.** Drop PDFs in a folder, get a chat UI that answers questions about them with citations.

**What the user does.**
- `python ingest.py` — chunks + embeds the PDFs into one collection per file.
- `gradio_app.py` — chat UI on `localhost:7860`. Conversation history persists across restarts.

**LangChain primitives forced.**
- Multi-collection `OracleVS` (one collection per PDF, one shared `CONVERSATIONS` for chat history).
- `EnsembleRetriever` for hybrid search.
- `OracleChatMessageHistory` + `RunnableWithMessageHistory` for stateful chat.
- Metadata = `{"filename": ..., "page": ...}` so citations point at exact pages.

**Shape.** `src/<project>/{ingest,store,chains,app}.py`. ~600 lines total.

**Demo.** GIF: drop a PDF, ask 3 questions, see citations + persistent history after a kill/restart.

---

## 2. Codebase Q&A

**Pitch.** Index a Git repo's source. "Where is auth implemented? How does the rate limiter work?"

**What the user does.**
- `python ingest.py /path/to/repo` — walks the tree, embeds source files (chunked by symbol, not by line count).
- `gradio_app.py` — chat UI. Filter by language or directory at retrieval time.

**LangChain primitives forced.**
- One `OracleVS` collection, with metadata = `{"path": ..., "lang": ..., "symbol": ...}`.
- `vs.as_retriever(search_kwargs={"k": 5, "filter": {"lang": "python"}})` — metadata filtering at retrieval.
- The metadata-as-string monkeypatch (filtered retrieval *requires* it).

**Shape.** Same skeleton as PDF-RAG. ~700 lines.

**Demo.** Index this very repo. Ask "where does the agentic_rag verify step run?"; get `apps/agentic_rag/tests/test_smoke_reasoning.py` cited correctly.

---

## 3. Web-page librarian

**Pitch.** Personal Pocket replacement with semantic search and answers-with-citations.

**What the user does.**
- `python add.py "https://..."` — fetches, extracts text (use `trafilatura`), chunks, embeds.
- `gradio_app.py` — search + chat. Citations link back to the source URL.

**LangChain primitives forced.**
- `OracleVS.add_documents()` per page (vs `from_texts` once).
- `similarity_search_with_score()` to surface confidence.
- Persistent chat history scoped per user session.

**Shape.** ~600 lines.

**Demo.** Save 10 pages, ask cross-page questions, see source URLs in answers.

---

## 4. Slack-thread digest

**Pitch.** Paste an exported Slack export; get a chat UI that knows your team's history.

**What the user does.**
- `python ingest.py slack_export.zip` — one collection per channel.
- `gradio_app.py` — pick channel(s), chat. Summarize chains over retrieved threads.

**LangChain primitives forced.**
- Multi-collection (one per channel) with cross-collection search.
- Summarization chain reading from the retriever, writing to a second collection (pattern that prefigures the advanced "second brain" idea).

**Shape.** ~700 lines.

**Demo.** "What did we decide about the migration?" → summary + thread links.

---

## 5. Personal Wikipedia (markdown notes)

**Pitch.** RAG over your second brain. Two collections — `RAW_NOTES` and `SYNTHESIZED_SUMMARIES` — and the agent writes back into the second one.

**What the user does.**
- Point the skill at a folder of `.md` files (Obsidian, Logseq, plain notes — whatever).
- `gradio_app.py` — chat. Each conversation produces a summary that gets embedded into `SYNTHESIZED_SUMMARIES` so future questions can recall *prior conversations*, not just notes.

**LangChain primitives forced.**
- Two-collection pattern with cross-collection retrieval.
- Agent that *writes* to a vector store, not just reads.
- Persistent chat history.

**Shape.** ~800 lines. The most ambitious of the original five.

**Demo.** Show how asking a question once and asking it again three days later surfaces the prior conversation as context.

---

## 6. Meeting transcript assistant

**Pitch.** Drop Zoom / Otter / Teams transcripts. Chat "what did Sarah say about the migration?"; get a quote plus the timestamp to jump to.

**LangChain primitives forced.**
- Speaker-attribution metadata (`{"speaker": ..., "timestamp": ..., "meeting_id": ...}`).
- Retriever with `filter={"speaker": "sarah@..."}` — the user picks a speaker in the UI to scope retrieval.
- `EnsembleRetriever`: vector for "what was discussed" + BM25 for "who said the literal phrase 'must ship by Friday'".

**Shape.** Same skeleton as PDF-RAG. ~700 lines.

**Demo.** Ingest a 1h transcript. Filter to one speaker. Ask "what's their position on X?" → quoted answer with timestamp.

---

## 7. GitHub issue triage chat

**Pitch.** Export a repo's issues (via `gh issue list --json`) and chat across them. "What bugs did we close last sprint? What's still open in the auth area?"

**LangChain primitives forced.**
- Heavy categorical metadata filtering (`{"status": ..., "labels": [...], "milestone": ..., "created": ...}`).
- The metadata-as-string monkeypatch — categorical filters fail silently without it.
- Date-range filter pattern: `filter={"closed_after": "2026-03-01"}` then post-filter; demonstrates a real limitation of vector filters and how to work around it.

**Shape.** ~700 lines.

**Demo.** Ingest issues from a public repo (e.g. `langchain-oracledb`). Chat: "summarize all closed bugs labelled 'docs' in the last 30 days." Get a real list with links.

---

## 8. Newsletter / RSS digest chatbot

**Pitch.** Paste exports from Substack, Pocket, or any RSS reader. Chat about what you've been reading. "What did Stratechery say about AI hardware in Q1?"

**LangChain primitives forced.**
- Author + date faceting at retrieval (`{"author": ..., "published": ..., "feed": ...}`).
- Per-topic chat threading: `RunnableWithMessageHistory` keyed by topic ID rather than user — showing that the history table can index whatever scope you want.
- A second collection (`SUMMARIES`) where each finished chat thread writes back a short summary. Future questions retrieve from both raw articles *and* prior summaries — the precursor pattern to advanced-tier "second brain" agents.

**Shape.** ~750 lines.

**Demo.** Ingest one author's last year of posts. Ask three follow-up questions. Restart, ask a related question, watch the prior thread's summary surface as context.

---

## What the skill won't scaffold

- **Multi-user with auth.** Out of scope. Single-user only.
- **Production deployment.** No Docker for the *app*, no nginx, no TLS. The user can dockerize after the project works.
- **Anything where Oracle isn't the vector store.** No FAISS / Chroma / Qdrant fallback.
- **Voice input, image RAG, agent tool-calling.** All advanced-tier features.
