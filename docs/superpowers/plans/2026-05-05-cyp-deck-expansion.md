# CYP deck expansion — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `guides/cyp-2026-05/build-with-oracle-easy.html` from 17 to 28 slides per the spec at `docs/superpowers/specs/2026-05-05-cyp-deck-expansion-design.md` — 11 new slides, 3 lede rewrites, light touchups, global renumber.

**Architecture:** The deck is a single self-contained HTML file with `<style>` and `<script>` blocks in-line. New slides reuse existing CSS classes (`slide`, `signal-card`, `section-eyebrow`, `section-title`, `two-col`, `col-stack`, `pre.code`, `badge-grid`, `arch`, `stat-row`, `bullets`). No CSS changes. Implementation order: (1) global renumber to `/ 28`, (2) tier-lede rewrites (slides 5/8/13), (3) new slide insertions, (4) light touchups with forward-references, (5) browser-render smoke + commit.

**Tech Stack:** HTML5 + scoped CSS (Archivo Black / Space Grotesk / JetBrains Mono via Google Fonts). Vanilla JS controller. No build step. No tests beyond manual viewport scroll + grep-based numbering audit.

---

## File structure

Single file modified throughout the entire plan:

- **Modify:** `guides/cyp-2026-05/build-with-oracle-easy.html` (currently ~1387 lines, will grow to ~2300 lines)

No new files. No CSS changes. No JS changes (the slide controller auto-discovers `.slide` sections via `document.querySelectorAll('.slide')`, so it adapts to the new count for free).

## Pre-flight: verification baseline

Before any edits, capture the current state so renumbering can be verified deterministically.

- [ ] **Step 0a: Verify current slide count is 17**

Run: `grep -c '<section class="slide' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: `17`

- [ ] **Step 0b: Verify current `slide-num` denominators are all `/ 17`**

Run: `grep -c '/ 17</div>' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: `17`

- [ ] **Step 0c: Capture current title-text fingerprints for the three slides we're about to rewrite (5, 7, 10)**

Run: `grep -n -A1 'id="slide-5"\|id="slide-7"\|id="slide-10"' guides/cyp-2026-05/build-with-oracle-easy.html | head -30`
Expected output should include all three currently-existing IDs.

---

## Task 1: Global renumber from `/ 17` to `/ 28`

**Why first:** Every subsequent slide insert/rewrite needs to know its target number. Renumbering before edits eliminates a class of bugs where a slide gets inserted with the wrong number.

**Note on slide-num text values:** Each existing `<div class="slide-num">NN / 17</div>` will get its denominator bumped to `/ 28`. The numerator stays as-is for now (the existing slide stays at its existing position); later tasks will bump numerators in the slides that physically shift.

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html` (replace_all on `/ 17</div>` → `/ 28</div>`)

- [ ] **Step 1.1: Replace all `/ 17</div>` with `/ 28</div>`**

Use Edit with `replace_all: true`:
- old_string: `/ 17</div>`
- new_string: `/ 28</div>`

- [ ] **Step 1.2: Verify the global replace landed on all 17 sites**

Run: `grep -c '/ 28</div>' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: `17`

Run: `grep -c '/ 17</div>' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: `0`

- [ ] **Step 1.3: Update the file-top comment (line 7-8) which still claims "17 slides"**

Edit:
- old_string:
  ```
    <!-- 17 slides. Use-case slides for each tier sit immediately after each tier
         intro: beginner @ slide 6, intermediate @ slide 9, advanced @ slide 12. -->
  ```
- new_string:
  ```
    <!-- 28 slides. Tier ledes: beginner @ slide 5, intermediate @ slide 8, advanced @ slide 13.
         Tier badge slides: beginner @ slide 7, intermediate @ slide 12, advanced @ slide 23.
         Demo @ slide 26. Per docs/superpowers/plans/2026-05-05-cyp-deck-expansion.md. -->
  ```

- [ ] **Step 1.4: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): renumber denominators 17 to 28 ahead of slide-set expansion"
```

---

## Task 2: Renumber existing slide-num numerators that will shift

**Background:** After insertions, the existing slides will sit at new positions. Rather than do this in two passes (insert, then renumber), we can pre-shift the numerators on the slides that are *not* getting rewritten so the file is internally consistent at every commit boundary. The three slides being **rewritten in place** (5, 8, 13 — currently slide 5, 7, 10) keep their slot; their numerators only change for slides 8 and 13.

**Position mapping** (current → new):

| Current `id="slide-N"` | Stays / Moves | New numerator | New `id` |
|---|---|---|---|
| 1 | stays | 01 | slide-1 |
| 2 | stays | 02 | slide-2 |
| 3 | stays | 03 | slide-3 |
| 4 | stays | 04 | slide-4 |
| 5 | rewritten in place | 05 | slide-5 |
| 6 | shifts +1 | 07 | slide-7 |
| 7 | rewritten + shifts +1 | 08 | slide-8 |
| 8 | shifts +1 | 09 | slide-9 |
| 9 | shifts +3 | 12 | slide-12 |
| 10 | rewritten + shifts +3 | 13 | slide-13 |
| 11 | shifts +5 | 16 | slide-16 |
| 12 | shifts +11 | 23 | slide-23 |
| 13 | shifts +11 | 24 | slide-24 |
| 14 | shifts +11 | 25 | slide-25 |
| 15 | shifts +11 | 26 | slide-26 |
| 16 | shifts +11 | 27 | slide-27 |
| 17 | shifts +11 | 28 | slide-28 |

**Why we shift in this task before inserting:** the file-search pattern `id="slide-NN"` is unique per slide, so we can do exact edits without ambiguity. After insertion, several `id`s would collide.

**Approach:** rename the highest-numbered shifters first so we never overwrite an in-use ID. Order: 17 → 16 → 15 → 14 → 13 → 12 → 11 → 10 → 9 → 8 → 7 → 6.

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html` (16 numerator edits across 11 shifters; slides 6, 9, 11 each shift but slot 5/8/13 will be rewritten so their numerator changes happen as part of those rewrites in later tasks)

- [ ] **Step 2.1: Shift slide 17 → 28**

Edit:
- old_string: `<section class="slide" id="slide-17">`
- new_string: `<section class="slide" id="slide-28">`

Edit:
- old_string: `  <div class="slide-num">17 / 28</div>`
- new_string: `  <div class="slide-num">28 / 28</div>`

- [ ] **Step 2.2: Shift slide 16 → 27**

Edit:
- old_string: `<section class="slide" id="slide-16">`
- new_string: `<section class="slide" id="slide-27">`

Edit:
- old_string: `  <div class="slide-num">16 / 28</div>`
- new_string: `  <div class="slide-num">27 / 28</div>`

- [ ] **Step 2.3: Shift slide 15 → 26**

Edit:
- old_string: `<section class="slide" id="slide-15">`
- new_string: `<section class="slide" id="slide-26">`

Edit:
- old_string: `  <div class="slide-num">15 / 28</div>`
- new_string: `  <div class="slide-num">26 / 28</div>`

- [ ] **Step 2.4: Shift slide 14 → 25**

Edit:
- old_string: `<section class="slide" id="slide-14">`
- new_string: `<section class="slide" id="slide-25">`

Edit:
- old_string: `  <div class="slide-num">14 / 28</div>`
- new_string: `  <div class="slide-num">25 / 28</div>`

- [ ] **Step 2.5: Shift slide 13 → 24**

Edit:
- old_string: `<section class="slide" id="slide-13">`
- new_string: `<section class="slide" id="slide-24">`

Edit:
- old_string: `  <div class="slide-num">13 / 28</div>`
- new_string: `  <div class="slide-num">24 / 28</div>`

- [ ] **Step 2.6: Shift slide 12 → 23**

Edit:
- old_string: `<section class="slide" id="slide-12">`
- new_string: `<section class="slide" id="slide-23">`

Edit:
- old_string: `  <div class="slide-num">12 / 28</div>`
- new_string: `  <div class="slide-num">23 / 28</div>`

- [ ] **Step 2.7: Shift slide 11 → 16**

Edit:
- old_string: `<section class="slide" id="slide-11">`
- new_string: `<section class="slide" id="slide-16">`

Edit:
- old_string: `  <div class="slide-num">11 / 28</div>`
- new_string: `  <div class="slide-num">16 / 28</div>`

- [ ] **Step 2.8: Shift slide 9 → 12**

Edit:
- old_string: `<section class="slide" id="slide-9">`
- new_string: `<section class="slide" id="slide-12">`

Edit:
- old_string: `  <div class="slide-num">09 / 28</div>`
- new_string: `  <div class="slide-num">12 / 28</div>`

- [ ] **Step 2.9: Shift slide 8 → 9**

Edit:
- old_string: `<section class="slide" id="slide-8">`
- new_string: `<section class="slide" id="slide-9">`

Edit:
- old_string: `  <div class="slide-num">08 / 28</div>`
- new_string: `  <div class="slide-num">09 / 28</div>`

- [ ] **Step 2.10: Shift slide 6 → 7**

Edit:
- old_string: `<section class="slide" id="slide-6">`
- new_string: `<section class="slide" id="slide-7">`

Edit:
- old_string: `  <div class="slide-num">06 / 28</div>`
- new_string: `  <div class="slide-num">07 / 28</div>`

- [ ] **Step 2.11: Verify shifts**

Run: `grep -E '<section class="slide.*id="slide-' guides/cyp-2026-05/build-with-oracle-easy.html | sed -E 's/.*id="(slide-[0-9]+)".*/\1/' | sort -t- -k2n`
Expected: `slide-1, slide-2, slide-3, slide-4, slide-5, slide-7, slide-9, slide-10, slide-12, slide-16, slide-23, slide-24, slide-25, slide-26, slide-27, slide-28` (16 lines, with the gaps where new slides will land — 6, 8, 11, 13–15, 17–22).

(Slide 10 and 5 are still in their old spots and will be rewritten in tasks 3 and 4.)

- [ ] **Step 2.12: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): pre-shift existing slide IDs for 28-slide layout"
```

---

## Task 3: Slide 5 — Beginner lede rewrite (OCI GenAI + langchain-oracledb + in-DB ONNX)

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html` (replace existing slide 5 body and section comment)

Per spec: name the three protagonist libraries explicitly, supply one supporting fact each, no cliché framing.

- [ ] **Step 3.1: Replace slide 5 (and the comment block above it) with the new lede**

Edit:
- old_string:
  ```
  <!-- =========================================================
       SLIDE 5 — TIER 1 / BEGINNER
       The shape of the afternoon project
       ========================================================= -->
  <section class="slide" id="slide-5">
    <div class="slide-num">05 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="active">Beginner</span>
      <span class="inactive">Intermediate</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Tier 1 · Beginner</div>
      <h2 class="section-title reveal" contenteditable="false">Drop a folder of PDFs in. Get a chat that <em>cites</em> them back.</h2>
      <div class="two-col reveal">
        <div class="col-stack">
          <p class="section-lede" contenteditable="false">The classic RAG shape, but the storage and retrieval live <strong>inside Oracle 26ai</strong> — not Chroma, not FAISS, not a SaaS pinned to someone else's billing dashboard.</p>
          <ul class="bullets" contenteditable="false">
            <li><code>OracleVS.from_documents()</code> — chunk, embed, write</li>
            <li><code>OracleVS.as_retriever()</code> — k-NN cosine search</li>
            <li><code>OracleSummaryStore</code> — chat history that survives restart</li>
            <li>Same chunking the tier-2/3 paths reuse</li>
          </ul>
        </div>
        <pre class="code" contenteditable="false"><span class="kw">from</span> langchain_oracledb <span class="kw">import</span> OracleVS
  <span class="kw">from</span> langchain_huggingface <span class="kw">import</span> HuggingFaceEmbeddings

  emb = <span class="fn">HuggingFaceEmbeddings</span>(
      <span class="em">model_name</span>=<span class="str">"sentence-transformers/all-MiniLM-L6-v2"</span>,
  )

  vs = OracleVS.<span class="fn">from_documents</span>(
      docs, emb,
      client=conn,
      table_name=<span class="str">"DOCUMENTS"</span>,
      distance_strategy=<span class="str">"COSINE"</span>,
  )

  retriever = vs.<span class="fn">as_retriever</span>(search_kwargs={<span class="str">"k"</span>: 4})</pre>
      </div>
    </div>
  </section>
  ```

  *(Note: in the actual file, the `pre.code` block content is left-flush, not indented inside the markdown — keep the file's existing indentation.)*

- new_string:
  ```
  <!-- =========================================================
       SLIDE 5 — TIER 1 / BEGINNER LEDE
       OCI GenAI + langchain-oracledb + in-DB ONNX = one RAG pipeline
       ========================================================= -->
  <section class="slide" id="slide-5">
    <div class="slide-num">05 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="active">Beginner</span>
      <span class="inactive">Intermediate</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Tier 1 · Beginner</div>
      <h2 class="section-title reveal" contenteditable="false">OCI GenAI plus <code>langchain-oracledb</code> plus in-DB ONNX. Three libraries. <em>One</em> RAG pipeline.</h2>
      <div class="arch reveal">
        <div class="arch-box primary">
          <div class="arch-label" contenteditable="false">Inference</div>
          <div class="arch-title" contenteditable="false">OCI GenAI</div>
          <div class="arch-detail" contenteditable="false">Bearer-token chat completion, OpenAI-compatible. One <code>OCI_GENAI_API_KEY</code> env var, no <code>~/.oci/config</code>.</div>
        </div>
        <div class="arch-box">
          <div class="arch-label" contenteditable="false">Storage</div>
          <div class="arch-title" contenteditable="false">langchain-oracledb</div>
          <div class="arch-detail" contenteditable="false">Vector store, chat history, JSON Duality — all on the same Oracle connection.</div>
        </div>
        <div class="arch-box">
          <div class="arch-label" contenteditable="false">Embeddings</div>
          <div class="arch-title" contenteditable="false">In-DB ONNX (MY_MINILM_V1)</div>
          <div class="arch-detail" contenteditable="false">384-dim model registered inside Oracle. No separate Python embedder process.</div>
        </div>
      </div>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">Drop PDFs or web pages into <code>corpus/</code>. <code>OracleVS.from_documents()</code> chunks, embeds, and writes — then chat answers cite the rows back. Same skeleton the tier-2 and tier-3 paths reuse.</p>
    </div>
  </section>
  ```

- [ ] **Step 3.2: Verify slide 5 was rewritten**

Run: `grep -A1 'id="slide-5"' guides/cyp-2026-05/build-with-oracle-easy.html | head -5`
Expected: contains `05 / 28` and the new section-title text starts with "OCI GenAI plus".

- [ ] **Step 3.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): rewrite slide 5 lede around OCI GenAI + langchain-oracledb + in-DB ONNX"
```

---

## Task 4: Slide 6 — Multi-source RAG (PDFs + web), NEW

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html` (insert after slide 5 closing `</section>`, before the `SLIDE 6 — BEGINNER USE CASES` comment which now belongs to slide 7)

- [ ] **Step 4.1: Insert new slide 6 between current slide 5 and the existing beginner-badges slide (now at id slide-7)**

Edit:
- old_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 6 — BEGINNER USE CASES
       Three concrete projects all sharing the same skeleton
       ========================================================= -->
  <section class="slide" id="slide-7">
    <div class="slide-num">07 / 28</div>
  ```

  *(Note: The `</div></section>` pair right before the SLIDE 6 comment is the close of slide 5. We pin on this exact context to avoid hitting other section closes.)*

- new_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 6 — MULTI-SOURCE RAG (PDFs + web), beginner tier
       Same chunking, same embedder, different loaders
       ========================================================= -->
  <section class="slide" id="slide-6">
    <div class="slide-num">06 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="active">Beginner</span>
      <span class="inactive">Intermediate</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Tier 1 · same pipeline, two corpora</div>
      <h2 class="section-title reveal" contenteditable="false">Same chunking. Same embedder. <em>Different</em> loaders.</h2>
      <div class="two-col reveal">
        <div class="col-stack">
          <p class="section-lede" contenteditable="false"><code>langchain-oracledb</code> doesn't care whether your text came from PDFs on disk or HTML over the wire. The loader on the left changes; the storage and retrieval on the right don't.</p>
          <ul class="bullets" contenteditable="false">
            <li><code>PyPDFLoader</code> — page-aware chunks with <code>source.pdf:p.N</code> citations</li>
            <li><code>WebBaseLoader</code> — HTML scrubbed via <code>trafilatura</code>, URL kept as metadata</li>
            <li>Same <code>OracleVS.from_documents()</code> sink either way</li>
            <li>Mix-and-match: PDFs <em>and</em> web pages in the same collection</li>
          </ul>
        </div>
  <pre class="code" contenteditable="false"><span class="kw">from</span> langchain_community.document_loaders <span class="kw">import</span> (
      PyPDFLoader, WebBaseLoader,
  )
  <span class="kw">from</span> langchain_oracledb <span class="kw">import</span> OracleVS

  pdf_docs = <span class="fn">PyPDFLoader</span>(<span class="str">"corpus/release-notes.pdf"</span>).<span class="fn">load</span>()
  web_docs = <span class="fn">WebBaseLoader</span>([
      <span class="str">"https://docs.oracle.com/en/database/.../vector.html"</span>,
  ]).<span class="fn">load</span>()

  vs = OracleVS.<span class="fn">from_documents</span>(
      pdf_docs + web_docs,         <span class="com"># mixed corpus, same sink</span>
      embedding=embedder,
      client=conn,
      table_name=<span class="str">"CORPUS"</span>,
      distance_strategy=<span class="str">"COSINE"</span>,
  )</pre>
      </div>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">The corpus shape changes; the retrieval path doesn't. Beginner badges 1.1 (PDFs) and 1.3 (web articles) ship the same <code>vs</code> object — just a different <code>load()</code> at the top.</p>
    </div>
  </section>
  ```

- [ ] **Step 4.2: Verify slide 6 inserted**

Run: `grep -c 'id="slide-6"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: `1`

Run: `grep -E 'id="slide-(5|6|7)"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: three lines, in order slide-5, slide-6, slide-7.

- [ ] **Step 4.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): add slide 6 — multi-source RAG (PDFs + web pages, same pipeline)"
```

---

## Task 5: Slide 8 — Oracle MCP lede rewrite (replaces old "sk-… key" intermediate lede)

**Background:** The slide currently sitting at `id="slide-7"` (post task 2 shift) is the old slide 7 ("One `sk-…` key. Zero ceremony"). We need to:
1. Move it from id slide-7 to id slide-8 (because slide 7 is now the beginner-badges slide).
2. Rewrite its body to be the Oracle MCP lede.

**Wait — re-checking task 2 mapping.** Old slide 7 (bearer-token) gets *rewritten*; per spec it becomes the new intermediate lede at slot 8. Old slide 6 (beginner badges) shifts to slot 7. So in task 2 we shifted old-6 → 7 but we did **not** shift old-7 to anywhere — we left it at id slide-7. Let me re-check.

Re-reading task 2: yes, step 2.10 shifts old slide 6 → 7. But old slide 7 stays where it is — at the renamed-by-collision spot. After task 2, the file has `id="slide-7"` appearing **twice** if we shifted old-6 to that spot before moving old-7 out.

**Fix to task 2:** Insert one more shift step between 2.10 and 2.11. Shift old slide 7 → slide 8 *first*, then shift old slide 6 → slide 7.

**Correction (read this carefully and apply during execution):** In task 2, swap the order of steps 2.9 (old slide 8 → 9) and 2.10 (old slide 6 → 7). The correct order to avoid ID collision is:

1. Step 2.9-corrected: shift old slide 8 → slide 9 (correct as written).
2. Step 2.9b-new: shift old slide 7 → slide 8 (NEW — must be inserted before 2.10).
3. Step 2.10-corrected: shift old slide 6 → slide 7 (correct as written, but only valid once old slide 7 is out of slot 7).

**Apply this correction in task 2 execution:** insert the following step 2.9b after step 2.9 and before step 2.10.

- [ ] **Step 2.9b (correction): Shift old slide 7 → slide 8 (before old slide 6 takes slot 7)**

Edit:
- old_string: `<section class="slide" id="slide-7">`
- new_string: `<section class="slide" id="slide-8">`

Edit:
- old_string: `  <div class="slide-num">07 / 28</div>`
- new_string: `  <div class="slide-num">08 / 28</div>`

(Insert this step into Task 2 during execution, then proceed with task 2.10 and onward.)

---

Now task 5 itself: rewrite the slide body that now sits at `id="slide-8"`.

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html` (replace the body of the slide at id slide-8, plus its preamble comment)

- [ ] **Step 5.1: Rewrite slide 8 (the old bearer-token slide) into the Oracle MCP lede**

Edit:
- old_string:
  ```
  <!-- =========================================================
       SLIDE 7 — BEARER-TOKEN AUTH
       The "no tenancy needed" punchline
       ========================================================= -->
  <section class="slide" id="slide-8">
    <div class="slide-num">08 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="active">Beginner</span>
      <span class="inactive">Intermediate</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Auth — the part that used to take a day</div>
      <h2 class="section-title reveal" contenteditable="false">One <code>sk-…</code> key. <em>Zero</em> ceremony.</h2>
      <div class="two-col reveal">
        <div class="col-stack">
          <p class="section-lede" contenteditable="false">The OCI Generative AI service exposes an OpenAI-compatible bearer-token endpoint at <code>us-phoenix-1</code>. You don't need <code>~/.oci/config</code>, a compartment OCID, or the SigV1 signer dance. You don't even need a full OCI tenancy.</p>
          <ul class="bullets" contenteditable="false">
            <li>Generate the key in the OCI GenAI service console</li>
            <li>Drop it in <code>.env</code> as <code>OCI_GENAI_API_KEY</code></li>
            <li>Use the upstream <code>openai</code> Python SDK — no shim</li>
            <li>Same wire format your other OpenAI code already speaks</li>
          </ul>
        </div>
        <pre class="code" contenteditable="false"><span class="kw">from</span> openai <span class="kw">import</span> OpenAI
  <span class="kw">import</span> os

  client = <span class="fn">OpenAI</span>(
      <span class="em">base_url</span>=<span class="str">"https://inference.generativeai."</span>
               <span class="str">"us-phoenix-1.oci.oraclecloud.com/v1"</span>,
      <span class="em">api_key</span>=os.environ[<span class="str">"OCI_GENAI_API_KEY"</span>],
  )

  resp = client.chat.completions.<span class="fn">create</span>(
      model=<span class="str">"xai.grok-4"</span>,   <span class="com"># full id required</span>
      messages=[{<span class="str">"role"</span>: <span class="str">"user"</span>,
                 <span class="str">"content"</span>: <span class="str">"Reply OK."</span>}],
      max_tokens=8,
  )
  <span class="fn">print</span>(resp.choices[0].message.content)  <span class="com"># OK</span></pre>
      </div>
    </div>
  </section>
  ```

- new_string:
  ```
  <!-- =========================================================
       SLIDE 8 — TIER 2 / INTERMEDIATE LEDE — ORACLE MCP
       Tools, not schemas
       ========================================================= -->
  <section class="slide" id="slide-8">
    <div class="slide-num">08 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Beginner</span>
      <span class="active">Intermediate</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Tier 2 · Intermediate</div>
      <h2 class="section-title reveal" contenteditable="false">Oracle MCP — the model calls <em>tools</em>, not <em>schemas</em>.</h2>
      <div class="two-col reveal">
        <div class="col-stack">
          <p class="section-lede" contenteditable="false"><strong>Without MCP</strong>, you stuff the schema into the system prompt — ~600 tokens of <code>CREATE TABLE</code>s and indexes, and you pray the model doesn't hallucinate a column. Cost climbs with every table; reliability drops with every join.</p>
          <p class="section-lede" contenteditable="false"><strong>With Oracle MCP</strong>, the model has four tools and zero schema in the prompt. It picks <code>list_tables</code> when it needs the surface, <code>describe_table</code> when it needs columns, <code>run_sql</code> when it has the query, <code>vector_search</code> when it has only a question.</p>
        </div>
  <pre class="code" contenteditable="false"><span class="com"># Oracle MCP server exposes four tools.</span>
  <span class="com"># The agent picks; Oracle answers.</span>

  tools = [
      <span class="fn">ListTables</span>(),                          <span class="com"># schema discovery</span>
      <span class="fn">DescribeTable</span>(),                       <span class="com"># columns + indexes</span>
      <span class="fn">RunSQL</span>(mode=<span class="str">"read_only"</span>),              <span class="com"># SELECTs by default</span>
      <span class="fn">VectorSearch</span>(model=<span class="str">"MY_MINILM_V1"</span>),    <span class="com"># in-DB ONNX</span>
  ]

  agent = <span class="fn">create_react_agent</span>(
      llm=<span class="fn">ChatOpenAI</span>(model=<span class="str">"xai.grok-4"</span>),
      tools=tools,
  )

  <span class="com"># The agent doesn't memorize your schema. It asks.</span></pre>
      </div>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">Bearer-token auth still applies — the same <code>OCI_GENAI_API_KEY</code> env var from slide 5 picks up here. The difference is what the model sees: in slide 5 it sees text, in slide 8 it sees <em>tools</em>.</p>
    </div>
  </section>
  ```

- [ ] **Step 5.2: Verify slide 8 was rewritten**

Run: `grep -A1 'id="slide-8"' guides/cyp-2026-05/build-with-oracle-easy.html | head -5`
Expected: contains `08 / 28` and section-title with "Oracle MCP — the model calls".

- [ ] **Step 5.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): rewrite slide 8 lede around Oracle MCP (tools not schemas)"
```

---

## Task 6: Slide 10 — Ollama MCP, NEW

**Position:** between current slide 9 (schemas-vs-tools, the old slide 8) and current slide 12 (intermediate badges, the old slide 9). Insert as a fresh `<section>` with id slide-10.

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 6.1: Insert slide 10 (Ollama MCP) after slide 9 closes**

The slide at `id="slide-9"` is the old slide 8 (schemas-vs-tools deep-dive). Find its closing `</section>` followed by the comment block for the next slide (which will be `<!-- SLIDE 9 ... -->` from the original numbering, now containing the slide we already shifted to id slide-12).

The exact context to match:

Edit:
- old_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 9 — INTERMEDIATE USE CASES
       Three projects: NL2SQL · schema-doc generator · hybrid retrieval
       ========================================================= -->
  <section class="slide" id="slide-12">
  ```

- new_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 10 — OLLAMA MCP
       Same MCP protocol against a local model
       ========================================================= -->
  <section class="slide" id="slide-10">
    <div class="slide-num">10 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Beginner</span>
      <span class="active">Intermediate</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Same protocol · your model · your hardware</div>
      <h2 class="section-title reveal" contenteditable="false">Same protocol. <em>Your</em> model on <em>your</em> hardware.</h2>
      <div class="two-col reveal">
        <div class="col-stack">
          <p class="section-lede" contenteditable="false">MCP isn't OCI-specific. The <strong>same Oracle MCP server</strong> from slide 9 speaks to Ollama running a local model — the four tools (<code>list_tables</code>, <code>describe_table</code>, <code>run_sql</code>, <code>vector_search</code>) don't change.</p>
          <ul class="bullets" contenteditable="false">
            <li><code>ollama serve</code> on <code>:11434</code> — OpenAI-compat endpoint</li>
            <li><code>Qwen3.5-35B-A3B</code> at INT4 — fits a 24 GB A10</li>
            <li>MCP client config points at the same Oracle MCP server</li>
            <li>Falls back to Grok-4 over OCI when local hardware is unavailable</li>
          </ul>
          <p class="section-lede" contenteditable="false"><strong>Caveat.</strong> Tool-call quality tracks model quality. Qwen3.5-35B-A3B is the floor we recommend; smaller models will hallucinate tool arguments under load.</p>
        </div>
  <pre class="code" contenteditable="false"><span class="kw">from</span> langchain_openai <span class="kw">import</span> ChatOpenAI

  <span class="com"># Local Ollama, OpenAI-compatible endpoint</span>
  llm = <span class="fn">ChatOpenAI</span>(
      model=<span class="str">"qwen3.5:35b-a3b"</span>,
      base_url=<span class="str">"http://localhost:11434/v1"</span>,
      api_key=<span class="str">"ollama"</span>,         <span class="com"># any non-empty string</span>
  ).<span class="fn">bind_tools</span>(oracle_mcp_tools)

  <span class="com"># Same agent loop. Same Oracle MCP server.</span>
  <span class="com"># Different inference plane.</span>
  agent = <span class="fn">create_react_agent</span>(llm, tools=oracle_mcp_tools)</pre>
      </div>
    </div>
  </section>
  ```

- [ ] **Step 6.2: Verify slide 10 inserted**

Run: `grep -E 'id="slide-(9|10|12)"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: three lines, in order slide-9, slide-10, slide-12.

- [ ] **Step 6.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): add slide 10 — Ollama MCP (same protocol, local Qwen)"
```

---

## Task 7: Slide 11 — AI SQL generation via Oracle MCP + Claude Code, NEW

**Position:** between slide 10 (Ollama MCP) and slide 12 (intermediate badges, the shifted old slide 9).

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 7.1: Insert slide 11 between slide 10 and slide 12**

Edit:
- old_string: (the close of slide 10 followed by the comment for slide 9-now-12)
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 9 — INTERMEDIATE USE CASES
       Three projects: NL2SQL · schema-doc generator · hybrid retrieval
       ========================================================= -->
  <section class="slide" id="slide-12">
  ```

- new_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 11 — AI SQL GENERATION VIA ORACLE MCP + CLAUDE CODE
       Converged DB UX — every team's preferred consumption layer
       ========================================================= -->
  <section class="slide" id="slide-11">
    <div class="slide-num">11 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Beginner</span>
      <span class="active">Intermediate</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Converged DB · one schema · many languages</div>
      <h2 class="section-title reveal" contenteditable="false">One database. <em>Five</em> consumption layers. <em>One</em> natural-language interface.</h2>
      <div class="stat-row reveal">
        <div class="stat">
          <div class="stat-val">5</div>
          <div class="stat-label" contenteditable="false">consumption layers — relational, JSON Duality, vector, graph, Select AI</div>
        </div>
        <div class="stat">
          <div class="stat-val">1</div>
          <div class="stat-label" contenteditable="false">schema — the source of truth lives once, not per-team</div>
        </div>
        <div class="stat">
          <div class="stat-val">0</div>
          <div class="stat-label" contenteditable="false">ETL — no team needs a copy of someone else's data</div>
        </div>
        <div class="stat">
          <div class="stat-val">∞</div>
          <div class="stat-label" contenteditable="false">teams that can ask questions in English instead of learning each other's pipelines</div>
        </div>
      </div>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">Claude Code already writes Oracle SQL well. Oracle MCP gives it the schema and the run loop. The cognitive load drops to: <em>"ask in English, get rows."</em> Two SREs and a data scientist hit the same DB through their preferred consumption layer — and the LLM doesn't need to learn five copies of their data.</p>
    </div>
  </section>
  ```

- [ ] **Step 7.2: Verify slide 11 inserted**

Run: `grep -E 'id="slide-(10|11|12)"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: three lines, in order slide-10, slide-11, slide-12.

- [ ] **Step 7.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): add slide 11 — AI SQL generation via Oracle MCP + Claude Code"
```

---

## Task 8: Slide 13 — OAMP lede rewrite (replaces old "in-DB ONNX" advanced lede)

**Position:** the slide currently at `id="slide-13"` is the shifted-from-slide-10 in-DB-ONNX slide. We overwrite its body with the OAMP lede. The in-DB-ONNX content moves to slide 15 (task 10).

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 8.1: Rewrite slide 13 as OAMP lede**

Edit:
- old_string:
  ```
  <!-- =========================================================
       SLIDE 10 — IN-DB ONNX EMBEDDINGS
       The "embeddings move into the database" punchline
       ========================================================= -->
  <section class="slide" id="slide-13">
    <div class="slide-num">13 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Beginner</span>
      <span class="active">Intermediate</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Embeddings move <em>into</em> the database</div>
      <h2 class="section-title reveal" contenteditable="false">Same model. <em>No</em> Python embedder process.</h2>
      <div class="two-col reveal">
        <div class="col-stack">
          <p class="section-lede" contenteditable="false">Tier 1 ran <code>HuggingFaceEmbeddings</code> in Python. Tier 2 registers the <em>same</em> MiniLM-L6-v2 ONNX model <strong>inside</strong> Oracle and calls <code>VECTOR_EMBEDDING(MODEL ... USING text)</code> as a SQL primitive.</p>
          <ul class="bullets" contenteditable="false">
            <li>Register once via the <code>onnx2oracle</code> CLI</li>
            <li>One round-trip: query in, vector out, all in-database</li>
            <li>Embeddings + vector search + relational filters in <em>one</em> SQL plan</li>
            <li>No Python dependency on the retrieval path</li>
          </ul>
        </div>
        <pre class="code" contenteditable="false"><span class="com"># 1. Register the ONNX model (one-time)</span>
  $ onnx2oracle export --preset all-MiniLM-L6-v2 \
                       --output minilm.onnx
  $ onnx2oracle import \
      --dsn user/pwd@host:port/service \
      --onnx minilm.onnx \
      --model-name MY_MINILM_V1

  <span class="com"># 2. Embed and search in one SQL pass</span>
  <span class="kw">SELECT</span> id, text,
         <span class="fn">VECTOR_DISTANCE</span>(
           embedding,
           <span class="fn">VECTOR_EMBEDDING</span>(
             <span class="em">MY_MINILM_V1</span> <span class="kw">USING</span> :q
           ),
           <span class="kw">COSINE</span>
         ) <span class="kw">AS</span> dist
  <span class="kw">FROM</span>   chunks
  <span class="kw">ORDER BY</span> dist
  <span class="kw">FETCH FIRST</span> 4 <span class="kw">ROWS ONLY</span>;</pre>
      </div>
    </div>
  </section>
  ```

- new_string:
  ```
  <!-- =========================================================
       SLIDE 13 — TIER 3 / ADVANCED LEDE — ORACLEAGENTMEMORY
       Per-user durable memory · threads · auto-extraction · context cards
       ========================================================= -->
  <section class="slide" id="slide-13">
    <div class="slide-num">13 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Intermediate</span>
      <span class="active">Advanced</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Tier 3 · Advanced</div>
      <h2 class="section-title reveal" contenteditable="false"><code>oracleagentmemory</code> — per-user durable memory. <em>Not</em> just a chat log.</h2>
      <div class="arch reveal">
        <div class="arch-box primary">
          <div class="arch-label" contenteditable="false">Threads</div>
          <div class="arch-title" contenteditable="false">(user_id, agent_id) conversations</div>
          <div class="arch-detail" contenteditable="false">Per-turn timestamps. Cold→warm recovery via UUID. <code>client.get_thread(saved_id)</code> on a fresh process returns the same conversation.</div>
        </div>
        <div class="arch-box">
          <div class="arch-label" contenteditable="false">Durable memory</div>
          <div class="arch-title" contenteditable="false">add_memory · search</div>
          <div class="arch-detail" contenteditable="false">Scoped to user + agent. Auto-extracted from messages when an LLM is wired in (frequency=2, window=4).</div>
        </div>
        <div class="arch-box">
          <div class="arch-label" contenteditable="false">Context cards</div>
          <div class="arch-title" contenteditable="false">thread.get_context_card()</div>
          <div class="arch-detail" contenteditable="false">Prompt-ready XML synopsis — topics, summary, relevant memories. No prompt-stuffing, no hand-rolled summaries.</div>
        </div>
      </div>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">The v3 advanced retrofit replaced ~250 LOC of hand-rolled chat-history + session-summary plumbing with ~30 LOC of OAMP wiring. Three primitives, one PyPI package (<code>oracleagentmemory==26.4</code>), same Oracle connection. See slide 23 for the three projects it powers.</p>
    </div>
  </section>
  ```

- [ ] **Step 8.2: Verify slide 13 was rewritten and now sits in the Advanced tier breadcrumb**

Run: `grep -A6 'id="slide-13"' guides/cyp-2026-05/build-with-oracle-easy.html | head -15`
Expected: contains `13 / 28`, the breadcrumb has `Advanced` as `active` and `Intermediate` as `inactive`, and the section-title contains `oracleagentmemory`.

- [ ] **Step 8.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): rewrite slide 13 lede around oracleagentmemory (advanced tier)"
```

---

## Task 9: Slide 14 — langchain-oracledb value props, NEW

**Position:** between slide 13 (OAMP lede) and slide 16 (converged-DB story, the shifted old slide 11).

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 9.1: Insert slide 14 after slide 13**

Edit:
- old_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 11 — TIER 3 / ADVANCED INTRO
       Six memory types · self-memory · JSON Duality
       ========================================================= -->
  <section class="slide" id="slide-16">
  ```

- new_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 14 — LANGCHAIN-ORACLEDB VALUE PROPS
       Vector store · chat history · loaders · JSON Duality bridge
       ========================================================= -->
  <section class="slide" id="slide-14">
    <div class="slide-num">14 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Intermediate</span>
      <span class="active">Advanced</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">The framework that already <em>knows</em> Oracle</div>
      <h2 class="section-title reveal" contenteditable="false"><code>langchain-oracledb</code> — what the framework gives you for free.</h2>
      <div class="arch reveal" style="grid-template-columns: repeat(4, 1fr);">
        <div class="arch-box">
          <div class="arch-label" contenteditable="false">Vector</div>
          <div class="arch-title" contenteditable="false">OracleVS</div>
          <div class="arch-detail" contenteditable="false">Multi-collection vector store — RUNBOOKS, GLOSSARY, DECISIONS — IVF or HNSW indexes, COSINE/DOT/L2.</div>
        </div>
        <div class="arch-box">
          <div class="arch-label" contenteditable="false">Chat</div>
          <div class="arch-title" contenteditable="false">OracleChatMessageHistory</div>
          <div class="arch-detail" contenteditable="false">Single-user simple chat log on the same connection. The "no extraction needed" tier.</div>
        </div>
        <div class="arch-box">
          <div class="arch-label" contenteditable="false">Loaders</div>
          <div class="arch-title" contenteditable="false">OracleDocLoader + Splitter</div>
          <div class="arch-detail" contenteditable="false">Load PDFs, web, files. Chunk semantically. Same Oracle connection as the sink.</div>
        </div>
        <div class="arch-box primary">
          <div class="arch-label" contenteditable="false">Bridge</div>
          <div class="arch-title" contenteditable="false">JSON Duality view bridge</div>
          <div class="arch-detail" contenteditable="false">Read your relational data as documents — without copying it. Tier 3's "one row, two shapes" trick.</div>
        </div>
      </div>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">The framework brings the storage. You bring the agent. <code>OracleVS</code> for fixed RAG corpora, <code>OracleChatMessageHistory</code> when a chat log is enough — and <code>oracleagentmemory</code> (slide 13) when the conversation deserves a real memory layer.</p>
    </div>
  </section>
  ```

- [ ] **Step 9.2: Verify slide 14 inserted**

Run: `grep -E 'id="slide-(13|14|16)"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: three lines, in order slide-13, slide-14, slide-16.

- [ ] **Step 9.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): add slide 14 — langchain-oracledb value props"
```

---

## Task 10: Slide 15 — In-DB ONNX + onnx2oracle, NEW (rescues content from old slide 10)

**Position:** between slide 14 (langchain-oracledb) and slide 16 (converged-DB story).

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 10.1: Insert slide 15 after slide 14**

Edit:
- old_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 11 — TIER 3 / ADVANCED INTRO
       Six memory types · self-memory · JSON Duality
       ========================================================= -->
  <section class="slide" id="slide-16">
  ```

- new_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 15 — IN-DB ONNX + onnx2oracle
       Same model, no Python embedder process (lifted from old slide 10)
       ========================================================= -->
  <section class="slide" id="slide-15">
    <div class="slide-num">15 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Intermediate</span>
      <span class="active">Advanced</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Embeddings live <em>inside</em> Oracle</div>
      <h2 class="section-title reveal" contenteditable="false">Same model. <em>No</em> Python embedder process.</h2>
      <div class="two-col reveal">
        <div class="col-stack">
          <p class="section-lede" contenteditable="false">Most projects ship a separate Python embedder process: a model file on disk, a HuggingFace import, its own failure mode. <code>onnx2oracle</code> registers the same MiniLM-L6-v2 ONNX model <strong>inside</strong> Oracle so embedding becomes a SQL primitive — same connection as the rest of your retrieval path.</p>
          <ul class="bullets" contenteditable="false">
            <li>Register once via the <code>onnx2oracle</code> CLI</li>
            <li>One round-trip: query in, vector out, all in-database</li>
            <li>Embeddings + vector search + relational filters in <em>one</em> SQL plan</li>
            <li><code>OracleVS</code> and <code>oracleagentmemory</code> share one embedder, one schema, one operational story</li>
          </ul>
        </div>
  <pre class="code" contenteditable="false"><span class="com"># 1. Register the ONNX model (one-time)</span>
  $ onnx2oracle export --preset all-MiniLM-L6-v2 \
                       --output minilm.onnx
  $ onnx2oracle import \
      --dsn user/pwd@host:port/service \
      --onnx minilm.onnx \
      --model-name MY_MINILM_V1

  <span class="com"># 2. Embed and search in one SQL pass</span>
  <span class="kw">SELECT</span> id, text,
         <span class="fn">VECTOR_DISTANCE</span>(
           embedding,
           <span class="fn">VECTOR_EMBEDDING</span>(
             <span class="em">MY_MINILM_V1</span> <span class="kw">USING</span> :q <span class="kw">AS</span> data
           ),
           <span class="kw">COSINE</span>
         ) <span class="kw">AS</span> dist
  <span class="kw">FROM</span>   chunks
  <span class="kw">ORDER BY</span> dist
  <span class="kw">FETCH FIRST</span> 4 <span class="kw">ROWS ONLY</span>;</pre>
      </div>
    </div>
  </section>
  ```

- [ ] **Step 10.2: Verify slide 15 inserted**

Run: `grep -E 'id="slide-(14|15|16)"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: three lines, in order slide-14, slide-15, slide-16.

- [ ] **Step 10.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): add slide 15 — in-DB ONNX + onnx2oracle (rescued from old slide 10)"
```

---

## Task 11: Slide 17 — visual-oracledb (semantic search + graphify), NEW

**Position:** after slide 16 (converged-DB story), before slide 23 (advanced badges).

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 11.1: Insert slide 17 after slide 16**

Edit:
- old_string: (the close of slide 16 followed by the comment for the original slide 12 which now lives at id slide-23)
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 12 — ADVANCED USE CASES
       Three projects composed from skills/ building blocks
       ========================================================= -->
  <section class="slide" id="slide-23">
  ```

- new_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 17 — VISUAL-ORACLEDB
       Converged DB — vector + graph + JSON Duality, one connection
       ========================================================= -->
  <section class="slide" id="slide-17">
    <div class="slide-num">17 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Intermediate</span>
      <span class="active">Advanced</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Converged DB · semantic search + graphify</div>
      <h2 class="section-title reveal" contenteditable="false"><code>visual-oracledb</code> — semantic search and <em>graphify</em>, one connection.</h2>
      <div class="arch reveal">
        <div class="arch-box primary">
          <div class="arch-label" contenteditable="false">Vector</div>
          <div class="arch-title" contenteditable="false">VECTOR_DISTANCE</div>
          <div class="arch-detail" contenteditable="false">k-NN over a 1M-row corpus. IVF (~0.88-0.90 recall@10) or HNSW (~0.95-0.97). Same SQL surface.</div>
        </div>
        <div class="arch-box">
          <div class="arch-label" contenteditable="false">Graph</div>
          <div class="arch-title" contenteditable="false">MATCH (n)-[r]-&gt;(m)</div>
          <div class="arch-detail" contenteditable="false">Property graphs over the same schema. Walk relationships you'd otherwise denormalize into JSON.</div>
        </div>
        <div class="arch-box">
          <div class="arch-label" contenteditable="false">Duality</div>
          <div class="arch-title" contenteditable="false">SELECT * FROM customer_dv</div>
          <div class="arch-detail" contenteditable="false">JSON Duality View — read your relational rows as documents. One row, two shapes, server-managed.</div>
        </div>
      </div>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">RAG, graph traversal, and analytics — same DBA, same backup, same auth. The advanced tier (slides 23 onward) leans on this: hybrid analyst (3.1) routes between vector and SQL, schema designer (3.3) ships JSON Duality views from a conversation.</p>
    </div>
  </section>
  ```

- [ ] **Step 11.2: Verify slide 17 inserted**

Run: `grep -E 'id="slide-(16|17|23)"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: three lines, in order slide-16, slide-17, slide-23.

- [ ] **Step 11.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): add slide 17 — visual-oracledb (vector + graph + JSON Duality)"
```

---

## Task 12: Slide 18 — Multi-agent RAG, NEW

**Position:** after slide 17, before slide 23.

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 12.1: Insert slide 18**

Edit:
- old_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 12 — ADVANCED USE CASES
       Three projects composed from skills/ building blocks
       ========================================================= -->
  <section class="slide" id="slide-23">
  ```

- new_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 18 — MULTI-AGENT RAG (apps/agentic_rag)
       Retrieval, reasoning, tool use as separate agents
       ========================================================= -->
  <section class="slide" id="slide-18">
    <div class="slide-num">18 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Intermediate</span>
      <span class="active">Advanced</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Beyond single-pipeline RAG</div>
      <h2 class="section-title reveal" contenteditable="false">Retrieval. Reasoning. Tool use. <em>Three</em> agents, one query.</h2>
      <div class="two-col reveal">
        <div class="col-stack">
          <p class="section-lede" contenteditable="false"><code>apps/agentic_rag/</code> splits the work that beginner-tier RAG does in one chain across three specialised agents. Each agent owns one decision; the orchestrator (LangGraph) wires them; <code>oracleagentmemory</code> carries the conversation state across them.</p>
          <ul class="bullets" contenteditable="false">
            <li><strong>Retrieval agent.</strong> Picks the collection (RUNBOOKS / GLOSSARY / DECISIONS), runs vector search, ranks results.</li>
            <li><strong>Reasoning agent.</strong> Plans the answer over the retrieved context using CoT or ReAct.</li>
            <li><strong>Tool agent.</strong> Calls Oracle MCP if SQL or fresh-data lookup is needed mid-answer.</li>
          </ul>
        </div>
  <pre class="code" contenteditable="false"><span class="kw">from</span> langgraph.graph <span class="kw">import</span> StateGraph

  graph = <span class="fn">StateGraph</span>(AgentState)
  graph.<span class="fn">add_node</span>(<span class="str">"retrieve"</span>, retrieval_agent)
  graph.<span class="fn">add_node</span>(<span class="str">"reason"</span>,   reasoning_agent)
  graph.<span class="fn">add_node</span>(<span class="str">"tools"</span>,    tool_agent)

  graph.<span class="fn">add_edge</span>(<span class="str">"retrieve"</span>, <span class="str">"reason"</span>)
  graph.<span class="fn">add_conditional_edges</span>(<span class="str">"reason"</span>,
      route=<span class="kw">lambda</span> s: <span class="str">"tools"</span> <span class="kw">if</span> s.needs_sql <span class="kw">else</span> END,
  )

  <span class="com"># Conversation state via OAMP, not in-process memory</span>
  thread = client.<span class="fn">create_thread</span>(user_id, agent_id)</pre>
      </div>
    </div>
  </section>
  ```

- [ ] **Step 12.2: Verify slide 18 inserted**

Run: `grep -E 'id="slide-(17|18|23)"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: three lines, in order slide-17, slide-18, slide-23.

- [ ] **Step 12.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): add slide 18 — multi-agent RAG (apps/agentic_rag)"
```

---

## Task 13: Slide 19 — agent-reasoning compact, NEW

**Position:** after slide 18, before slide 23.

**Spec note:** explicitly half-density. Single card. Tag *not Oracle official*. No diagram, no code, no stat row.

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 13.1: Insert slide 19**

Edit:
- old_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 12 — ADVANCED USE CASES
       Three projects composed from skills/ building blocks
       ========================================================= -->
  <section class="slide" id="slide-23">
  ```

- new_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 19 — AGENT-REASONING (compact, half-density)
       Reference repo, not an official Oracle integration
       ========================================================= -->
  <section class="slide" id="slide-19">
    <div class="slide-num">19 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Intermediate</span>
      <span class="active">Advanced</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Reference repo · <em>not</em> an official Oracle integration</div>
      <h2 class="section-title reveal" contenteditable="false">Small models. <em>Big</em> reasoning patterns.</h2>
      <ul class="bullets reveal" contenteditable="false" style="max-width: 60em;">
        <li><code>apps/agent-reasoning/</code> ships <strong>11 cognitive architectures</strong> over Ollama — CoT, ToT, ReAct, Reflexion, Self-Refine, and others.</li>
        <li>Useful when your model is small enough that the architecture has to do the heavy lifting. Pair with Qwen3.5-7B or smaller on a laptop.</li>
        <li><strong>Caveat.</strong> This is a reference repo, not an Oracle-shipped library. The other slides on this deck are official integrations; this one is "here's what reasoning looks like when you can't lean on a 70B-class model."</li>
      </ul>
    </div>
  </section>
  ```

- [ ] **Step 13.2: Verify slide 19 inserted**

Run: `grep -E 'id="slide-(18|19|23)"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: three lines, in order slide-18, slide-19, slide-23.

- [ ] **Step 13.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): add slide 19 — agent-reasoning (compact, not Oracle-official)"
```

---

## Task 14: Slide 20 — A10 GPU + Qwen on Ollama / vLLM, NEW

**Position:** after slide 19, before slide 23.

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 14.1: Insert slide 20**

Edit:
- old_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 12 — ADVANCED USE CASES
       Three projects composed from skills/ building blocks
       ========================================================= -->
  <section class="slide" id="slide-23">
  ```

- new_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 20 — A10 GPU + Qwen on Ollama / vLLM
       Local inference plane, OpenAI-compat endpoints
       ========================================================= -->
  <section class="slide" id="slide-20">
    <div class="slide-num">20 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Intermediate</span>
      <span class="active">Advanced</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Local inference · A10 · INT4 quantization</div>
      <h2 class="section-title reveal" contenteditable="false">24 GB of VRAM. A 35B-param mixture-of-experts. <em>INT4</em> quantization.</h2>
      <div class="stat-row reveal" style="grid-template-columns: repeat(3, 1fr);">
        <div class="stat">
          <div class="stat-val">35B / 3B</div>
          <div class="stat-label" contenteditable="false">Qwen3.5-35B-A3B — 35B total params, 3B active per token, 256 experts (9 active)</div>
        </div>
        <div class="stat">
          <div class="stat-val">~17.5 GB</div>
          <div class="stat-label" contenteditable="false">on disk at INT4 quantization — fits A10 24 GB with headroom for KV cache</div>
        </div>
        <div class="stat">
          <div class="stat-val">2</div>
          <div class="stat-label" contenteditable="false">OpenAI-compat servers ready to swap behind the same client: <code>ollama serve</code> / <code>vllm.serve</code></div>
        </div>
      </div>
      <div class="two-col reveal" style="margin-top: 0.4em;">
        <div class="col-stack">
          <p class="section-lede" contenteditable="false"><strong>Ollama.</strong> Drop-in. Serves multiple models. GGUF format. Best for laptop work and small-fleet workshops where ergonomics beat throughput.</p>
        </div>
        <div class="col-stack">
          <p class="section-lede" contenteditable="false"><strong>vLLM.</strong> Paged attention, continuous batching, higher throughput per GPU-second. Best for served APIs at scale or multi-tenant inference.</p>
        </div>
      </div>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">Same OpenAI client (<code>base_url</code> + <code>api_key</code>) talks to either — and to the OCI GenAI bearer endpoint from slide 5. The model and the host are wire-compatible swaps.</p>
    </div>
  </section>
  ```

- [ ] **Step 14.2: Verify**

Run: `grep -E 'id="slide-(19|20|23)"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: three lines, in order slide-19, slide-20, slide-23.

- [ ] **Step 14.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): add slide 20 — A10 GPU + Qwen on Ollama/vLLM"
```

---

## Task 15: Slide 21 — Distillation + reasoning traces, NEW

**Position:** after slide 20, before slide 23.

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 15.1: Insert slide 21**

Edit:
- old_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 12 — ADVANCED USE CASES
       Three projects composed from skills/ building blocks
       ========================================================= -->
  <section class="slide" id="slide-23">
  ```

- new_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 21 — DISTILLATION + REASONING TRACES
       Big teacher generates traces; small student fine-tunes on them
       ========================================================= -->
  <section class="slide" id="slide-21">
    <div class="slide-num">21 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Intermediate</span>
      <span class="active">Advanced</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Big teacher · small student · traces in between</div>
      <h2 class="section-title reveal" contenteditable="false">Big teacher, small student — and the <em>traces</em> in between.</h2>
      <div class="two-col reveal">
        <div class="col-stack">
          <p class="section-lede" contenteditable="false">When the deployed model has to be small (latency, cost, on-device) but the answers should look big-model-shaped, distillation moves the reasoning capacity instead of the weights.</p>
          <ul class="bullets" contenteditable="false">
            <li><strong>Teacher.</strong> Qwen3.5-35B-A3B or Grok-4 generates a chain-of-thought reasoning trace per question.</li>
            <li><strong>Trace splitter.</strong> <code>split_reasoning.py</code> segments each trace into <code>(prompt, reasoning, answer)</code> triples.</li>
            <li><strong>Student.</strong> Smaller Qwen (e.g. 7B) is fine-tuned on the triples — supervised, no RL.</li>
            <li><strong>Result.</strong> The student produces teacher-shaped reasoning at student-shaped cost.</li>
          </ul>
        </div>
  <pre class="code" contenteditable="false"><span class="com"># 1. Teacher generates reasoning traces</span>
  $ python apps/agent-reasoning/<span class="fn">generate_reasoning_outputs</span>.py \
      --model qwen3.5:35b-a3b \
      --questions data/questions.jsonl \
      --out traces/raw.jsonl

  <span class="com"># 2. Split each trace into (prompt, reasoning, answer)</span>
  $ python apps/agent-reasoning/<span class="fn">split_reasoning</span>.py \
      --in  traces/raw.jsonl \
      --out traces/triples.jsonl

  <span class="com"># 3. Fine-tune the student on the triples</span>
  $ trl sft --model qwen3.5:7b \
            --dataset traces/triples.jsonl \
            --output_dir student-7b-distilled</pre>
      </div>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">Oracle isn't shipping this pipeline — but it's how every workshop attendee should be thinking about deploying small models locally on the same A10 box.</p>
    </div>
  </section>
  ```

- [ ] **Step 15.2: Verify**

Run: `grep -E 'id="slide-(20|21|23)"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: three lines, in order slide-20, slide-21, slide-23.

- [ ] **Step 15.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): add slide 21 — distillation + reasoning traces"
```

---

## Task 16: Slide 22 — picooraclaw, NEW

**Position:** after slide 21, before slide 23 (advanced badges).

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 16.1: Insert slide 22**

Edit:
- old_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 12 — ADVANCED USE CASES
       Three projects composed from skills/ building blocks
       ========================================================= -->
  <section class="slide" id="slide-23">
  ```

- new_string:
  ```
    </div>
  </section>

  <!-- =========================================================
       SLIDE 22 — PICOORACLAW
       Coding agent on OpenAI-compat endpoints, Oracle as storage
       ========================================================= -->
  <section class="slide" id="slide-22">
    <div class="slide-num">22 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Intermediate</span>
      <span class="active">Advanced</span>
    </div>
    <div class="slide-content">
      <div class="section-eyebrow reveal" contenteditable="false">Coding agent · OpenAI-compat · Oracle storage</div>
      <h2 class="section-title reveal" contenteditable="false"><code>picooraclaw</code> — a Go coding agent. Oracle is its <em>memory</em>.</h2>
      <div class="arch reveal">
        <div class="arch-box primary">
          <div class="arch-label" contenteditable="false">Inference</div>
          <div class="arch-title" contenteditable="false">OpenAI-compat I/O</div>
          <div class="arch-detail" contenteditable="false">Bring your own endpoint: OCI GenAI, Ollama, vLLM, OpenAI. Same wire format, swap by env var.</div>
        </div>
        <div class="arch-box">
          <div class="arch-label" contenteditable="false">Storage</div>
          <div class="arch-title" contenteditable="false">Oracle 26ai</div>
          <div class="arch-detail" contenteditable="false">Sessions, conversations, tool runs, snapshots. Replaces SQLite/Postgres in the upstream Picoclaw.</div>
        </div>
        <div class="arch-box">
          <div class="arch-label" contenteditable="false">Posture</div>
          <div class="arch-title" contenteditable="false">DB-as-only-store</div>
          <div class="arch-detail" contenteditable="false">Same invariant as the advanced choose-your-path tier. No Redis, no Chroma, no hidden caches.</div>
        </div>
      </div>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">Snapshot fork of <a href="https://github.com/picoclaw/picoclaw" style="color: var(--accent);">Picoclaw</a> with an Oracle layer applied on top — clean isolation so it tracks upstream. Sync method: cherry-pick upstream onto a fresh branch + reapply the Oracle layer as one commit. Sibling forks: <code>oraclaw</code> (TypeScript / openclaw), <code>zerooraclaw</code> (zeroclaw).</p>
    </div>
  </section>
  ```

- [ ] **Step 16.2: Verify**

Run: `grep -E 'id="slide-(21|22|23)"' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: three lines, in order slide-21, slide-22, slide-23.

- [ ] **Step 16.3: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): add slide 22 — picooraclaw (Oracle-backed coding agent)"
```

---

## Task 17: Light touchups for forward-references

The spec calls for one-line forward-references on slides 9 and 16. The breadcrumb on slide 9 also currently says `Beginner` is `active` — it was correct under the old numbering (current slide 8 was the *first* intermediate slide); now that slide 8 is the lede, slide 9 is the second intermediate slide, so the breadcrumb logic still holds — the active tier is `Intermediate`. Verify and fix if needed.

**Files:**
- Modify: `guides/cyp-2026-05/build-with-oracle-easy.html`

- [ ] **Step 17.1: Inspect slide 9's current breadcrumb (the old slide 8 schemas-vs-tools)**

Run: `grep -B1 -A8 'id="slide-9"' guides/cyp-2026-05/build-with-oracle-easy.html | head -15`
Expected: contains `<span class="active">Intermediate</span>`. If it does not, fix it in step 17.1b. Otherwise skip 17.1b.

- [ ] **Step 17.1b (conditional): Fix slide 9 breadcrumb if it still shows old active tier**

Only if the previous step shows the breadcrumb is wrong (i.e. `active` is on `Beginner` for slide 9).

Edit (replace_all=false; the slide-9 breadcrumb is a unique pattern):
- old_string:
  ```
  <section class="slide" id="slide-9">
    <div class="slide-num">09 / 28</div>
    <div class="slide-breadcrumb">
      <span class="inactive">Title</span>
      <span class="inactive">Promise</span>
      <span class="inactive">Stack</span>
      <span class="inactive">Beginner</span>
      <span class="active">Intermediate</span>
    </div>
  ```
- new_string: (same — confirm match; this is a no-op edit if already correct, used as a probe)

  *(If the actual content differs, write out the corrected breadcrumb here matching the deck's existing patterns. Do not invent new classes.)*

- [ ] **Step 17.2: Add a forward-reference line to slide 9 mentioning slide 10 (Ollama MCP)**

Slide 9 (the schemas-vs-tools deep-dive) currently ends with a `<pre class="code">` block. Append a short paragraph after it inside the `two-col`'s right column or below the `two-col` block.

Find the close of slide 9's `</pre>` followed by `</div>\n  </div>\n</section>`. We append a `<p class="section-lede reveal">` between the two-col close and the slide-content close.

Edit:
- old_string:
  ```
  <span class="com"># Agent loop: LLM picks tool → SQLcl tees → result → LLM</span></pre>
      </div>
    </div>
  </section>
  ```

- new_string:
  ```
  <span class="com"># Agent loop: LLM picks tool → SQLcl tees → result → LLM</span></pre>
      </div>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">Slide 10 shows the same four tools driven by a <em>local</em> Qwen via Ollama instead of Grok-4 over OCI — protocol unchanged.</p>
    </div>
  </section>
  ```

- [ ] **Step 17.3: Add a forward-reference line to slide 16 (converged DB) mentioning slide 17 (visual-oracledb)**

Slide 16 is the old slide 11 ("Oracle stops being *a* store") with one closing `<ul>` then `</div></div></section>`. Append a sentence to the existing trailing `<ul>` block — or add a new `<p>` after it.

Edit:
- old_string:
  ```
        <li><strong>Hybrid retrieval.</strong> A single agent answers questions that need <em>both</em> a PDF chunk <em>and</em> a structured runbook row to respond well.</li>
      </ul>
    </div>
  </section>
  ```

- new_string:
  ```
        <li><strong>Hybrid retrieval.</strong> A single agent answers questions that need <em>both</em> a PDF chunk <em>and</em> a structured runbook row to respond well.</li>
      </ul>
      <p class="section-lede reveal" style="margin-top: 0.4em;" contenteditable="false">Slide 17 (<code>visual-oracledb</code>) shows the same converged story extended to graph traversal and JSON Duality, all on the same connection.</p>
    </div>
  </section>
  ```

- [ ] **Step 17.4: Commit**

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): light touchups — forward-references from slides 9 and 16"
```

---

## Task 18: Final audit pass

Verify all slides are present, numbered correctly, and the breadcrumbs are sane.

**Files:**
- (read-only verification of `guides/cyp-2026-05/build-with-oracle-easy.html`)

- [ ] **Step 18.1: Confirm 28 `.slide` sections exist**

Run: `grep -c '<section class="slide' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: `28`

- [ ] **Step 18.2: Confirm IDs are 1..28 with no gaps or duplicates**

Run: `grep -E '<section class="slide.*id="slide-' guides/cyp-2026-05/build-with-oracle-easy.html | sed -E 's/.*id="slide-([0-9]+)".*/\1/' | sort -n | uniq -c`
Expected: 28 lines, each showing `1 N` for N = 1..28.

- [ ] **Step 18.3: Confirm `slide-num` numerators match IDs**

Run:
```bash
paste \
  <(grep -oE 'id="slide-[0-9]+"' guides/cyp-2026-05/build-with-oracle-easy.html | sed -E 's/[^0-9]//g') \
  <(grep -oE '[0-9]{2} / 28</div>' guides/cyp-2026-05/build-with-oracle-easy.html | sed -E 's/[^0-9 ]//g' | awk '{print $1}')
```
Expected: 28 lines, with the two columns equal on every line (after stripping leading zeros from the numerator column — `01 == 1`, etc.).

- [ ] **Step 18.4: Confirm denominator is `/ 28` everywhere**

Run: `grep -c '/ 28</div>' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: `28`

Run: `grep -c '/ 17</div>' guides/cyp-2026-05/build-with-oracle-easy.html`
Expected: `0`

- [ ] **Step 18.5: Confirm tier-active breadcrumb pattern**

For each slide, the active tier should match the spec's tier mapping:

```bash
grep -B5 'class="active"' guides/cyp-2026-05/build-with-oracle-easy.html | grep -E 'id="slide-|active' | head -80
```

Eyeball check:
- Slides 1, 2, 3, 4: `Title` / `Promise` / `Three Paths` / `Stack` active.
- Slides 5, 6, 7: `Beginner` active.
- Slides 8, 9, 10, 11, 12: `Intermediate` active.
- Slides 13–23: `Advanced` active.
- Slide 24: `Advanced` (cold→warm — still advanced topic).
- Slide 25: `Advanced` (friction passes — also advanced anchor).
- Slide 26: `Demo` active.
- Slide 27: `Q&A` active.
- Slide 28: `Close` active.

If any breadcrumb diverges, fix it inline now (it's just a class swap on the matching `<span>`).

- [ ] **Step 18.6: Browser-render smoke**

The deck is meant to render in a modern browser. Open it locally and scroll through all 28 slides:

```bash
# from a developer machine with a browser available:
xdg-open guides/cyp-2026-05/build-with-oracle-easy.html  # Linux
# or
open guides/cyp-2026-05/build-with-oracle-easy.html      # macOS
```

Walk all 28 slides with arrow keys. Confirm:
- No slide overflows its viewport (`overflow: hidden` on `.slide` should clip but every body should fit).
- Numbers in the top-left chrome read `01 / 28` through `28 / 28`.
- The orange-card title slide (1) and orange-card outro slide (28) animate in.
- Code blocks render in JetBrains Mono with the orange `kw`, yellow `str`, blue `fn`.
- All `<em>` highlights show in orange.

If a slide overflows on a 1080p viewport, identify which class is too tall and trim. The most likely offenders are slide 14 (4-column `arch`) and slides with `two-col` + a long `pre.code` — the existing CSS already has a hard `max-height` clamp at 720px so overflow should be rare.

- [ ] **Step 18.7: Commit any audit fixes**

If steps 18.1–18.6 surfaced bugs and they were fixed inline:

```bash
git add guides/cyp-2026-05/build-with-oracle-easy.html
git commit -m "deck(cyp): audit-pass fixes after 28-slide expansion"
```

If no bugs were found, skip this commit.

---

## Self-review

**1. Spec coverage:**

Each spec section maps to a task as follows:

| Spec section | Task |
|---|---|
| Slide 5★ — beginner lede | Task 3 |
| Slide 6★ — multi-source RAG | Task 4 |
| Slide 8★ — Oracle MCP lede | Task 5 |
| Slide 10★ — Ollama MCP | Task 6 |
| Slide 11★ — AI SQL gen + Claude Code | Task 7 |
| Slide 13★ — OAMP lede | Task 8 |
| Slide 14★ — langchain-oracledb value props | Task 9 |
| Slide 15★ — in-DB ONNX + onnx2oracle | Task 10 |
| Slide 17★ — visual-oracledb | Task 11 |
| Slide 18★ — multi-agent RAG | Task 12 |
| Slide 19★ — agent-reasoning compact | Task 13 |
| Slide 20★ — A10 + Qwen on Ollama/vLLM | Task 14 |
| Slide 21★ — distillation + traces | Task 15 |
| Slide 22★ — picooraclaw | Task 16 |
| Touchups slides 9, 16 | Task 17 |
| Global renumber + audit | Tasks 1, 2, 18 |

All 14 changing slides covered. ✓

**2. Placeholder scan:** No "TBD" / "TODO" / "fill in details" / "similar to Task N". Every slide body is shipped in full. ✓

**3. Type / class consistency:** Every new slide uses pre-existing CSS classes (`slide`, `signal-card`, `section-eyebrow`, `section-title`, `two-col`, `col-stack`, `pre.code`, `badge-grid`, `arch`, `arch-box`, `arch-box.primary`, `stat-row`, `stat`, `stat-val`, `stat-label`, `bullets`). Two slides override `arch` `grid-template-columns` inline (slide 14 → 4 cols, slide 20 → 3 cols) — both are inline `style` attrs only, no class names invented. ✓

**4. Order-of-operations correctness:** The id-collision risk in task 2 is addressed by step 2.9b (renaming old slide 7 → slide 8 *before* renaming old slide 6 → slide 7). The `replace_all` global denominator swap in task 1 is safe because `/ 17</div>` is unique to numerator/denominator pairs. Insertions in tasks 4, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16 each pin to a *unique* anchor — the close of the immediately-preceding section followed by the comment block of the next one — so no insertion can land in the wrong slot. ✓

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-05-cyp-deck-expansion.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
