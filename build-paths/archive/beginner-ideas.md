# Beginner — project ideas

Eight scoped ideas. Each is short (~80-200 lines), uses only `langchain-oracledb` + Ollama + Oracle 26ai Free in Docker, and has an obvious "did it work" demo.

The skill asks the user to pick one. If they pitch their own, the skill maps it to the closest idea and confirms. If nothing maps, the skill falls back to idea 5 (smoke-only) rather than guessing a shape.

---

## 1. Personal bookmarks search

**Pitch.** Paste URLs into a CLI, get them back via natural-language search.

**What the user does.**
- `python add.py "https://..." "title" "description"` — appends a bookmark.
- `python search.py "what was that thing about langchain?"` — top-3 hits.

**LangChain primitives taught.**
- `OracleVS.from_texts()` to bootstrap on first run.
- `vs.add_texts(..., metadatas=[{"url": ..., "added_at": ...}])` for new bookmarks.
- `vs.similarity_search()` for retrieval.
- `vs.similarity_search_with_score()` so the user sees the distance.

**Shape.** Two scripts (`add.py`, `search.py`) sharing a `store.py` module. ~80 lines total.

**Demo.** A 30s GIF of typing one bookmark and finding it via a fuzzy query.

---

## 2. Recipe finder

**Pitch.** Drop a folder of `.txt` recipes; ask "what can I make with chicken and rice?"

**What the user does.**
- Place recipes in `recipes/`.
- `python ingest.py` — embeds all of them once.
- `python ask.py "what can I make with chicken and rice?"` — top-3 matches, with the source filename.

**LangChain primitives taught.**
- `OracleVS.from_texts(texts=..., metadatas=[{"filename": ...}])` — metadata as filename.
- `vs.similarity_search_with_score()` — show how confident the match is.
- The metadata-as-string monkeypatch (already non-trivial; the skill writes it for the user with a comment explaining why).

**Shape.** `ingest.py`, `ask.py`, `store.py`. ~100 lines total.

**Demo.** Type a query about ingredients, see three recipe filenames + scores.

---

## 3. Dev journal

**Pitch.** Append-only notes table with semantic recall. "What did I figure out about WebSockets last month?"

**What the user does.**
- `python note.py "fixed the websocket reconnect bug — turns out keepalive=30s"` — appends.
- `python recall.py "websockets reconnect"` — top-N.

**LangChain primitives taught.**
- Bootstrap once with `OracleVS.from_texts(["initial seed"], ...)`, then `add_texts` thereafter.
- Timestamp metadata; demonstrating `filter={"month": "2026-04"}` once on the recall side.

**Shape.** `note.py`, `recall.py`, `store.py`. ~120 lines.

**Demo.** Add three notes, recall one with a paraphrased query.

---

## 4. Movie taste graph

**Pitch.** Insert movies you liked (with plot summaries); get "more like this" recommendations.

**What the user does.**
- `python like.py "Arrival" "<plot summary>"`
- `python more_like.py "Arrival"` — top-5 nearest neighbors among your liked list.

**LangChain primitives taught.**
- `vs.as_retriever(search_kwargs={"k": 5})` — first taste of the retriever interface (sets up intermediate path).
- Search-by-title uses metadata filter to find the seed embedding, then a follow-up search by content.

**Shape.** `like.py`, `more_like.py`, `store.py`. ~100 lines.

**Demo.** Like 5 movies, get a "more like Arrival" output that's clearly thematic.

---

## 5. First-vector-query smoke

**Pitch.** No project. Just verify the whole stack — Docker container, Oracle 26ai, Ollama, `OracleVS` — works on the user's machine.

**What the user does.**
- `python smoke.py` — does `OracleVS.from_texts(["build-paths lives"], ...)`, searches for "build-paths", asserts it comes back. Prints `smoke: OK`.

**LangChain primitives taught.**
- The 5-line sermon, exactly. Nothing more.

**Shape.** One file. ~30 lines.

**Demo.** A terminal screenshot that says `smoke: OK`. Boring but honest.

---

## 6. Shell history search

**Pitch.** Embed your `~/.zsh_history` (or `.bash_history`); ask "what was that `ffmpeg` command I used to strip audio?"

**What the user does.**
- `python ingest.py` — reads `~/.zsh_history` (or a path passed as arg), filters lines >5 chars, embeds them with `{"shell": "zsh", "ts": ...}` metadata.
- `python find.py "strip audio from a video"` — top-3 commands.

**LangChain primitives taught.**
- `OracleVS.from_texts()` once on the full history. Shows that not all data needs to be appended a row at a time — sometimes ingestion is a single bulk pass over a file you already own.
- `similarity_search_with_score()` so the user sees match confidence on real, noisy data.

**Shape.** `ingest.py`, `find.py`, `store.py`. ~90 lines.

**Demo.** Search a paraphrase of a real command from your history; see it surface.

---

## 7. Flashcard recall

**Pitch.** A study aid. Type a question; get the nearest flashcard plus a confidence score that tells you whether *you* should remember it without peeking.

**What the user does.**
- `python add.py "What does ARP do?" "Maps IPs to MAC addresses on a LAN."`
- `python ask.py "how do hosts find each other on a LAN?"` — top-1 card with score; the answer is only revealed if the score crosses a threshold (close enough match).

**LangChain primitives taught.**
- Two-field metadata (`{"front": ..., "back": ...}`).
- `similarity_search_with_score()` used as a *gate*, not just a sort key. Below threshold → "you should know this, try again." Above threshold → reveal.
- Custom score interpretation (cosine distance closer to 0 = better).

**Shape.** `add.py`, `ask.py`, `store.py`. ~100 lines.

**Demo.** Add 10 cards; ask paraphrases of three of them. Watch confidence rise and fall sensibly.

---

## 8. Podcast / video note search

**Pitch.** Drop timestamped notes from your podcast or video log (e.g. `[00:13:00] CRDTs explained as monotonic merge`). Ask "where did I hear about CRDTs?"; get back filename + jump-to timestamp.

**What the user does.**
- Place notes in `episodes/` — one file per episode, lines beginning `[hh:mm:ss]` are individual chunks.
- `python ingest.py` — splits each line into its own embedding with `{"episode": ..., "ts": "00:13:00"}` metadata.
- `python find.py "CRDTs"` — top-3 with episode + timestamp.

**LangChain primitives taught.**
- Within-file chunking (vs the recipes idea, which embeds whole files).
- Structured metadata that's actually *useful at retrieval time* — the timestamp lets the user open the right place in the source.

**Shape.** `ingest.py`, `find.py`, `store.py`. ~110 lines.

**Demo.** Search a topic, click the printed timestamp, jump to the moment in your audio/video player.

---

## What the skill won't scaffold

If the user pitches:

- **A web UI.** Out of scope for beginner — that's intermediate. Skill says "great idea, save it for the next path."
- **Multiple LLMs.** Beginner uses one Ollama model.
- **Anything chat-like.** No conversation history at this tier — that's an intermediate primitive.
- **Anything with auth, multiple users, or "production-grade".** This is a learning project; keep it small.
