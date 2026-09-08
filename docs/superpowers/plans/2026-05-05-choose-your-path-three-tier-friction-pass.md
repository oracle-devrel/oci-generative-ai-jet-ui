# choose-your-path three-tier friction pass — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Walk the `choose-your-path` skill set as a real user across 4 scaffolded projects (1 beginner, 1 intermediate, 2 advanced), against the live Oracle 26ai Free container + OCI Grok 4 endpoint already verified on this machine. Capture friction, then consolidate findings into skill edits on `cyp-friction-pass-1`.

**Architecture:** Each of the 4 runs is one isolated subagent (Opus, max thinking) walking its tier's `SKILL.md` literally and writing 3 evidence files into `choose-your-path/tests/<run-name>/` — `verify_evidence.txt` (verify.py output), `_chat_evidence.md`, `_friction.md`. The runs are forbidden from editing `choose-your-path/` itself; all skill edits happen in a single consolidation phase after all four runs finish, so friction findings are comparable across a fixed skill state.

**Tech Stack:**
- **Infra:** Docker 29.4.2 + Compose v5.1.3, Oracle 26ai Free image
- **LLM:** OCI Generative AI Grok 4 (`us-chicago-1`), validated by `/tmp/grok_probe.py`
- **Embeddings:** MiniLM-L6-v2 (Python-side via `HuggingFaceEmbeddings` for beginner; in-DB ONNX `MY_MINILM_V1` for intermediate/advanced, following `github.com/jasperan/onnx2oracle`)
- **Python:** Conda envs per project (one per run dir): `cyp-beginner`, `cyp-intermediate`, `cyp-adv-hybrid`, `cyp-adv-selfmem`, plus the existing probe env `cyp-probe` for shared smoke calls
- **MCP:** `oracle-database-mcp-server` (intermediate, advanced)
- **SQLcl tee:** `sql` from Oracle SQLcl zip on Ubuntu 24.04 (intermediate only) — installed in Task 4
- **Branch:** `cyp-friction-pass-1` (already created; spec at commits `48278073`, `3f4444cf`)

**Spec:** `docs/superpowers/specs/2026-05-05-choose-your-path-three-tier-friction-pass-design.md`

---

## File Structure

```
choose-your-path/tests/                          (gitignored)
├── beginner-pdfs/                               run 1: walks beginner/SKILL.md
│   ├── (everything the skill scaffolds)
│   ├── verify_evidence.txt                      stdout of `python verify.py`
│   ├── _chat_evidence.md                        captured user-msg → grounded response
│   └── _friction.md                             friction findings
├── intermediate-nl2sql/                         run 2: walks intermediate/SKILL.md
│   ├── (everything the skill scaffolds)
│   ├── sql/                                     SQLcl-tee scripts (new surface area)
│   ├── logs/                                    SQLcl tee output
│   ├── README_SQLCL.md                          documents the tee extension
│   ├── verify_evidence.txt
│   ├── _chat_evidence.md
│   └── _friction.md
├── advanced-hybrid-analyst/                     run 3: walks advanced/SKILL.md (idea 1)
│   ├── (everything the skill scaffolds)
│   ├── verify_evidence.txt
│   ├── _chat_evidence.md
│   └── _friction.md
└── advanced-self-mem/                           run 4: walks advanced/SKILL.md (idea 2)
    ├── (everything the skill scaffolds)
    ├── verify_evidence.txt                      includes 2 verify runs (cold + warm)
    ├── _chat_evidence.md                        captures both runs; warm run must
    │                                              retrieve a SESSION_SUMMARIES row
    │                                              written by the cold run
    └── _friction.md

choose-your-path/                                friction-pass writes happen ONLY in
└── (existing contents — unchanged during runs)  the consolidation phase (Task 9)

docs/superpowers/
├── specs/2026-05-05-...-design.md               (already committed)
└── plans/2026-05-05-...-friction-pass.md        (this file)

scripts/cyp-runs/                                (new — orchestration scripts)
├── prefetch_minilm.py                           pre-cache MiniLM ~90MB once before runs
├── seed_pdfs/                                   3 small public-domain PDFs for beginner
│   ├── alice-chap1.pdf
│   ├── alice-chap2.pdf
│   └── alice-chap3.pdf
└── seed_runbooks/                               3 short runbooks/glossary/decisions for adv-1
    ├── glossary.md
    ├── runbook-restart-pipeline.md
    └── decision-2025-q4-vector-store.md
```

**Why these boundaries:**
- One subagent per run means each run holds one tier's worth of context. The orchestrator (this plan's executor) holds the cross-run consolidation.
- `_friction.md` lives next to its run dir so a single subagent owns one tier's findings end-to-end. The taxonomy (`where / what / expected / fix applied / proposed skill edit`) is rigid so the consolidation phase can dedupe by `proposed skill edit` mechanically.
- `scripts/cyp-runs/` is shared seed material so each run starts from the same corpus shape — keeps friction findings comparable.

---

## Task 1: Pre-flight infra checks

**Files:**
- Read: `~/.oci/config`, `/usr/bin/docker`, `~/miniconda3/envs/cyp-probe/bin/python`
- Test: ad-hoc bash + `/tmp/grok_probe.py` (already exists)

- [ ] **Step 1: Re-validate Docker, OCI, Grok 4**

```bash
docker --version
docker ps  # should not error; user is in docker group OR sudo works
test -r ~/.oci/config && echo "oci config: OK"
OCI_COMPARTMENT_ID=ocid1.compartment.oc1..aaaaaaaauyfykbiauv4nntvl3b57ydx3wcrqsnax7bbbvhov4vmdvqo2nqca \
  ~/miniconda3/envs/cyp-probe/bin/python /tmp/grok_probe.py
```

Expected output: `[ok] grok-4 replied: 'pong'` (already seen during setup).

If any check fails, stop and surface — every run depends on these.

- [ ] **Step 2: Confirm we're on `cyp-friction-pass-1` branch**

```bash
git rev-parse --abbrev-ref HEAD
```

Expected: `cyp-friction-pass-1`. If not, `git checkout cyp-friction-pass-1`.

- [ ] **Step 3: Confirm spec is committed**

```bash
git log --oneline -5
ls docs/superpowers/specs/2026-05-05-choose-your-path-three-tier-friction-pass-design.md
```

Expected: see commits `48278073` (initial spec) and `3f4444cf` (onnx2oracle amendment) in the log.

No commit at this task — pre-flight is read-only.

---

## Task 2: Pre-cache MiniLM weights (avoid first-run HF stall)

**Files:**
- Create: `scripts/cyp-runs/prefetch_minilm.py`
- Create: directory `scripts/cyp-runs/`

- [ ] **Step 1: Write the prefetch script**

Create `scripts/cyp-runs/prefetch_minilm.py`:

```python
"""Pre-cache sentence-transformers/all-MiniLM-L6-v2 (~90MB) so beginner run
doesn't stall on first-time HF download. Idempotent."""
from sentence_transformers import SentenceTransformer

print("downloading sentence-transformers/all-MiniLM-L6-v2 ...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
v = model.encode(["dim check"])
assert v.shape == (1, 384), f"unexpected shape: {v.shape}"
print(f"cached. dim={v.shape[1]}")
```

- [ ] **Step 2: Install sentence-transformers into cyp-probe env**

```bash
~/miniconda3/envs/cyp-probe/bin/pip install --quiet sentence-transformers
```

Expected: silent install (~30s, includes torch).

- [ ] **Step 3: Run the prefetch**

```bash
~/miniconda3/envs/cyp-probe/bin/python scripts/cyp-runs/prefetch_minilm.py
```

Expected: `cached. dim=384`. First time: ~30-60s for the download. Cache lives in `~/.cache/huggingface/hub/`.

- [ ] **Step 4: Commit the script**

```bash
git add scripts/cyp-runs/prefetch_minilm.py
git commit -m "scripts: prefetch MiniLM weights for cyp friction pass"
```

---

## Task 3: Seed corpora (beginner PDFs, advanced-1 runbooks)

**Files:**
- Create: `scripts/cyp-runs/seed_pdfs/alice-chap1.pdf` … `alice-chap3.pdf`
- Create: `scripts/cyp-runs/seed_runbooks/glossary.md` … etc
- Create: `scripts/cyp-runs/make_seed_pdfs.py` (generator)

- [ ] **Step 1: Write the PDF generator**

Create `scripts/cyp-runs/make_seed_pdfs.py`:

```python
"""Generate 3 small PDFs (one chapter each) for the beginner run's corpus.
Uses Alice in Wonderland (public domain) chunks so the chat-evidence step
has groundable, citable content."""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

CHAPTERS = {
    "alice-chap1.pdf": (
        "Chapter I: Down the Rabbit-Hole",
        [
            "Alice was beginning to get very tired of sitting by her sister on the bank,",
            "and of having nothing to do: once or twice she had peeped into the book her",
            "sister was reading, but it had no pictures or conversations in it,",
            "'and what is the use of a book,' thought Alice, 'without pictures or conversations?'",
            "So she was considering in her own mind whether the pleasure of making a",
            "daisy-chain would be worth the trouble of getting up and picking the daisies,",
            "when suddenly a White Rabbit with pink eyes ran close by her.",
        ],
    ),
    "alice-chap2.pdf": (
        "Chapter II: The Pool of Tears",
        [
            "'Curiouser and curiouser!' cried Alice (she was so much surprised, that for",
            "the moment she quite forgot how to speak good English).",
            "'Now I'm opening out like the largest telescope that ever was! Good-bye, feet!'",
            "for when she looked down at her feet, they seemed to be almost out of sight,",
            "they were getting so far off.",
            "'Oh, my poor little feet, I wonder who will put on your shoes and stockings",
            "for you now, dears?'",
        ],
    ),
    "alice-chap3.pdf": (
        "Chapter III: A Caucus-Race and a Long Tale",
        [
            "They were indeed a queer-looking party that assembled on the bank--the birds",
            "with draggled feathers, the animals with their fur clinging close to them,",
            "and all dripping wet, cross, and uncomfortable.",
            "The first question of course was, how to get dry again: they had a",
            "consultation about this, and after a few minutes it seemed quite natural to",
            "Alice to find herself talking familiarly with them.",
        ],
    ),
}

OUT = Path(__file__).parent / "seed_pdfs"
OUT.mkdir(exist_ok=True)

for name, (title, lines) in CHAPTERS.items():
    c = canvas.Canvas(str(OUT / name), pagesize=letter)
    c.setFont("Helvetica-Bold", 16); c.drawString(72, 720, title)
    c.setFont("Helvetica", 11)
    y = 690
    for line in lines:
        c.drawString(72, y, line); y -= 18
    c.showPage(); c.save()
    print(f"wrote {name}")
```

- [ ] **Step 2: Install reportlab + run the generator**

```bash
~/miniconda3/envs/cyp-probe/bin/pip install --quiet reportlab
~/miniconda3/envs/cyp-probe/bin/python scripts/cyp-runs/make_seed_pdfs.py
ls scripts/cyp-runs/seed_pdfs/
```

Expected: 3 PDFs listed.

- [ ] **Step 3: Write the runbooks for advanced-1**

Create three text files. Keep them short — the advanced-1 router classifier needs to see these as distinct "kinds" (glossary vs runbook vs decision).

`scripts/cyp-runs/seed_runbooks/glossary.md`:

```markdown
# Glossary

**MRR** — Monthly Recurring Revenue. Sum of subscription fees normalised to a monthly cadence.

**Churn (logo)** — Number of customers who cancelled in a period, divided by customers at start of period. Distinct from revenue churn.

**Cohort** — Customers grouped by signup month. We slice MRR by cohort to see retention curves.
```

`scripts/cyp-runs/seed_runbooks/runbook-restart-pipeline.md`:

```markdown
# Runbook: Restart the ingest pipeline

When the ingest pipeline alarms with `BACKLOG > 10000`:

1. Check the dead-letter queue length: `oci queue list-messages --queue-id $DLQ_OCID`.
2. If the DLQ is non-empty, page #data-platform; the upstream is likely emitting malformed events.
3. If the DLQ is empty, restart workers: `kubectl rollout restart deployment/ingest-worker -n data`.
4. Watch backlog for 5 minutes. If it does not drain, escalate.
```

`scripts/cyp-runs/seed_runbooks/decision-2025-q4-vector-store.md`:

```markdown
# Decision: Adopt Oracle AI Vector Search for production embeddings

**Date:** 2025-12-04
**Author:** Ignacio Marin

We will use Oracle AI Vector Search as the production vector store, replacing
our previous Pinecone + Postgres split.

Key reasons:
- Single store for vector + relational + chat history simplifies ops.
- In-DB ONNX embeddings remove embedding API egress and quota risk.
- The MCP server gives our agents typed SQL + vector tools without us writing
  glue code.

Tradeoff: a one-time ONNX export + register pipeline cost (per onnx2oracle).
```

- [ ] **Step 4: Commit seed corpora**

```bash
git add scripts/cyp-runs/make_seed_pdfs.py scripts/cyp-runs/seed_pdfs/ scripts/cyp-runs/seed_runbooks/
git commit -m "scripts: seed PDFs (beginner) and runbooks (advanced-1) for friction pass"
```

---

## Task 4: Install Oracle SQLcl (intermediate run prerequisite)

**Files:**
- Create: `~/opt/sqlcl/` (Oracle SQLcl extracted here, outside the repo)
- Modify: `~/.bashrc` (PATH addition for SQLcl)

- [ ] **Step 1: Confirm Java is present (SQLcl is a Java app)**

```bash
java -version 2>&1 | head -1
```

If absent, install: `sudo apt-get install -y -qq default-jre-headless`. SQLcl needs JRE 11+.

- [ ] **Step 2: Download + extract SQLcl**

```bash
mkdir -p ~/opt
cd ~/opt
curl -fsSLo sqlcl-latest.zip https://download.oracle.com/otn_software/java/sqldeveloper/sqlcl-latest.zip
unzip -q sqlcl-latest.zip
ls sqlcl/bin/sql
~/opt/sqlcl/bin/sql -V
```

Expected: SQLcl version line. If the download fails (Oracle download URL changed), the intermediate run is **blocked** per the spec — do not substitute another tool. Surface the failure in the run's `_friction.md` (this Task is itself a friction surface for the intermediate skill).

- [ ] **Step 3: Add SQLcl to PATH**

```bash
grep -q 'opt/sqlcl/bin' ~/.bashrc || echo 'export PATH="$HOME/opt/sqlcl/bin:$PATH"' >> ~/.bashrc
export PATH="$HOME/opt/sqlcl/bin:$PATH"
which sql
```

Expected: `/home/ubuntu/opt/sqlcl/bin/sql`.

- [ ] **Step 4: No commit — install lives outside the repo**

SQLcl install is host-state, not repo-state. The intermediate run's `README_SQLCL.md` will document the install steps so the next user can reproduce.

---

## Task 5: Run #1 — beginner PDFs-to-chat (sequential, smokes the stack)

**Files:**
- Create: `choose-your-path/tests/beginner-pdfs/` (entire scaffold via skill)
- Create: `choose-your-path/tests/beginner-pdfs/verify_evidence.txt`
- Create: `choose-your-path/tests/beginner-pdfs/_chat_evidence.md`
- Create: `choose-your-path/tests/beginner-pdfs/_friction.md`

- [ ] **Step 1: Dispatch the run subagent**

Use the `Agent` tool with `subagent_type: oh-my-claudecode:executor`, `model: opus`. Prompt (full text — the agent has zero conversation context):

````
You are run #1 of the choose-your-path three-tier friction pass.

**Spec:** /home/ubuntu/work/oracle-ai-developer-hub/docs/superpowers/specs/2026-05-05-choose-your-path-three-tier-friction-pass-design.md (read it before starting)
**Plan:** /home/ubuntu/work/oracle-ai-developer-hub/docs/superpowers/plans/2026-05-05-choose-your-path-three-tier-friction-pass.md (this is the orchestrating plan; you are Task 5)

**Your job:** Walk `choose-your-path/beginner/SKILL.md` literally as a real user would. Build the **PDFs-to-chat (idea 1)** project. Land everything in `/home/ubuntu/work/oracle-ai-developer-hub/choose-your-path/tests/beginner-pdfs/`.

**Forbidden:**
- Editing ANY file under `/home/ubuntu/work/oracle-ai-developer-hub/choose-your-path/` itself. Your job is to walk the skill, not to fix it. All skill edits happen in the consolidation phase, run by the orchestrator. If you find friction, log it — do not patch the skill.
- Substituting tools. If a step fails and the skill points at a fix, follow it. If no fix is documented, log it as friction and surface the failure.
- Skipping the interview. The skill's interview is part of what's being tested — answer each question as a real user would, but record every Q/A pair in `_friction.md` so we can see whether the interview wasn't useful.

**Resolved interview answers** (use these; record any deviations as friction):
- Q1 path: beginner (already locked by spec)
- Q2 target_dir: `/home/ubuntu/work/oracle-ai-developer-hub/choose-your-path/tests/beginner-pdfs/`
- Q3 db target: local Docker
- Q4 inference: OCI GenAI Grok 4 (us-chicago-1), MiniLM Python-side. `OCI_COMPARTMENT_ID=ocid1.compartment.oc1..aaaaaaaauyfykbiauv4nntvl3b57ydx3wcrqsnax7bbbvhov4vmdvqo2nqca`. `~/.oci/config` already configured.
- Q5 topic: idea 1 (PDFs-to-chat)
- Q6 notebook: no

**Seed corpus:** copy the 3 PDFs from `/home/ubuntu/work/oracle-ai-developer-hub/scripts/cyp-runs/seed_pdfs/` into `<target_dir>/data/pdfs/` after the skill scaffolds the project. Run the project's `ingest.py` against them.

**Conda env:** create `cyp-beginner` from `conda-forge` (override-channels), python=3.12, pip. Install the project's deps via `~/miniconda3/envs/cyp-beginner/bin/pip install -e .` from inside the target dir. Use `~/miniconda3/envs/cyp-beginner/bin/python` for everything; do NOT rely on `conda activate` (it doesn't work in non-interactive bash).

**Pre-existing finding to honor (do NOT silently fix):** the spec section "Pre-existing findings" notes that `choose-your-path/beginner/SKILL.md:124` says `assert dim == 1024` but should be `384`. When you write the project's `verify.py`, use 384 (the correct value, matching every other line in the skill). In `_friction.md` add a finding pointing at that line so the consolidation phase fixes the skill itself.

**Success bar (Bar B):**
1. `verify_evidence.txt` shows `verify: OK (db, vector, inference)` from running `python verify.py` (capture full stdout).
2. `_chat_evidence.md` shows ONE chat exchange where you ask the FastAPI adapter (running on :8000) a question whose answer requires retrieval from one of the 3 ingested PDFs, with citation in the form `(filename:page)`. Use `curl` against `/v1/chat/completions` (Open WebUI not required for evidence — the API call is enough). Capture both the request and the response. The response MUST be grounded in the ingested PDFs (e.g. "what does Alice think about books?" → answer cites alice-chap1.pdf and quotes the line about pictures and conversations). If the response is the model's pre-trained guess (no citation, no quote from the PDF), the run is NOT done.
3. `_friction.md` exists, even if empty.

**Friction format** (rigid, so consolidation can dedupe):
```
## <short title>
- **where:** <skill file path:line range OR step number>
- **what:** <literal observed behavior or message>
- **expected:** <what the skill led you to expect>
- **fix applied (if any):** <one line; null if blocked>
- **proposed skill edit:** <"edit X in <file>:<line> to say Y" — concrete>
```

**Verify recovery:** if `verify.py` fails, follow `choose-your-path/shared/verify.md`'s 3-retry recovery loop. Log each failure + fix in `_friction.md`. If still failing after 3 retries, mark the run BLOCKED (write a final entry titled "BLOCKED" with the unresolved error) and stop.

**Stop the adapter when done.** Do not leave the FastAPI process running. The chat evidence comes from a single API call, not a persistent server.

**Final report:** when done, write to stdout: "RUN 1 done. verify={OK|FAIL}. friction findings: <count>. blocked={yes|no}." Then exit.

Cleanup: do NOT remove the project dir, the docker container, or the conda env — the orchestrator inspects all of these in Task 9.
````

Run the agent in the foreground (we need its result before Task 6 starts).

- [ ] **Step 2: Inspect the run's output**

```bash
ls choose-your-path/tests/beginner-pdfs/
cat choose-your-path/tests/beginner-pdfs/verify_evidence.txt
cat choose-your-path/tests/beginner-pdfs/_chat_evidence.md
cat choose-your-path/tests/beginner-pdfs/_friction.md
```

If `verify: OK` is missing OR `_chat_evidence.md` lacks a grounded response with citation, the run did not meet Bar B — re-dispatch the agent with explicit feedback about what was missing. Max 2 re-dispatches before declaring the run blocked.

- [ ] **Step 3: Snapshot the run**

```bash
cd choose-your-path/tests/beginner-pdfs
docker compose ps
docker compose down  # leave volumes; future runs may reuse
cd /home/ubuntu/work/oracle-ai-developer-hub
```

- [ ] **Step 4: No commit yet — evidence is gitignored, friction merges in Task 9**

The `choose-your-path/tests/` dir is gitignored. Don't try to commit it. The `_friction.md` content gets *summarized* in the Task 9 commit message, not committed as files.

---

## Task 6: Run #2 — intermediate NL2SQL + MCP + SQLcl tee (sequential)

**Files:**
- Create: `choose-your-path/tests/intermediate-nl2sql/` (entire scaffold via skill)
- Create: `choose-your-path/tests/intermediate-nl2sql/sql/`
- Create: `choose-your-path/tests/intermediate-nl2sql/logs/`
- Create: `choose-your-path/tests/intermediate-nl2sql/README_SQLCL.md`
- Create: `choose-your-path/tests/intermediate-nl2sql/{verify_evidence.txt,_chat_evidence.md,_friction.md}`

- [ ] **Step 1: Dispatch the run subagent**

`Agent` with `subagent_type: oh-my-claudecode:executor`, `model: opus`:

````
You are run #2 of the choose-your-path three-tier friction pass.

**Spec + Plan:** same paths as run #1 (read both first).

**Your job:** Walk `choose-your-path/intermediate/SKILL.md` literally. Build **NL2SQL data explorer (idea 1)** PLUS the SQLcl-tee logging extension specified in the spec. Land everything in `/home/ubuntu/work/oracle-ai-developer-hub/choose-your-path/tests/intermediate-nl2sql/`.

**Forbidden** (same as run #1): no edits under `choose-your-path/`, no tool substitutions. SQLcl is mandatory — if SQLcl install fails, the run is BLOCKED, not "softened" to sqlplus.

**Resolved interview answers:**
- Q1 path: intermediate
- Q2 target_dir: `/home/ubuntu/work/oracle-ai-developer-hub/choose-your-path/tests/intermediate-nl2sql/`
- Q3 db target: local Docker
- Q4 inference: OCI GenAI Grok 4 + in-DB ONNX `MY_MINILM_V1`. Same `OCI_COMPARTMENT_ID` as run #1.
- Q5 topic: idea 1 (NL2SQL data explorer)
- Q6 notebook: yes (intermediate default)
- Q7 sql_mode: read_only (idea 1 doesn't need read_write)

**ONNX export-and-register (load-bearing):** the spec names `github.com/jasperan/onnx2oracle` as the canonical reference. Read `choose-your-path/shared/references/onnx-in-db-embeddings.md` first, then cross-check against `https://github.com/jasperan/onnx2oracle` (use WebFetch for the README). Any divergence — different `optimum.onnxruntime` invocation, different opset, different tokenizer wrapping, different `LOAD_ONNX_MODEL` invocation — is a friction finding. Use the **onnx2oracle** approach as ground truth; the skill's instructions are the candidate under review.

**Conda env:** `cyp-intermediate`, same conda-forge / python=3.12 / pip pattern as run #1. The intermediate skill will pip-install `optimum[onnxruntime]`, `onnxruntime>=1.18`, `onnxruntime-extensions`, `transformers`, `Faker`, etc.

**SQLcl tee extension** (NEW SURFACE AREA — not in the skill today). After the skill finishes scaffolding, you add:
1. `<target>/sql/` — directory for SQL scripts the agent's `run_sql` tool calls drop here, named `run_<unix_timestamp>.sql`.
2. A logging hook in `src/<package_slug>/adapter.py`: when the agent emits a `run_sql` tool call, the adapter (a) writes the SQL to `sql/run_<ts>.sql`, (b) shells out (best-effort, never blocks the response) to:
   ```
   sql -L -S "$DB_USER/$DB_PASSWORD@$DB_DSN" @sql/run_<ts>.sql > logs/sqlcl_<ts>.log 2>&1
   ```
   in a background `subprocess.Popen`, (c) embeds a `[sqlcl_log: logs/sqlcl_<ts>.log]` token at the END of the streamed response (after the agent's normal answer).
3. `<target>/README_SQLCL.md` documenting:
   - What the extension does and why (MCP shows the SQL the agent emits; SQLcl shows the actual rows + bind variables + execution plan if you append `EXPLAIN PLAN FOR` etc).
   - Install steps (point at Task 4 of this plan).
   - How to inspect logs.
   - Decision question for the consolidation phase: should this be folded into `intermediate/SKILL.md` permanently? Capture your opinion based on what implementing the tee taught you.

The SQLcl tee is opinionated — if you find that the spec's hook design has a problem (e.g. interferes with streaming), log it as friction and choose the smallest viable change to make it work, documenting that change.

**Pre-existing finding to honor:** spec notes `choose-your-path/intermediate/SKILL.md:74` claims the helper writes an `InDBEmbeddings` subclass. Your run will surface whether the helper actually ships it. If the helper writes something differently named (or doesn't ship it at all), capture as friction.

**Success bar (Bar B):**
1. `verify_evidence.txt` shows `verify: OK (db, vector, inference, mcp)`.
2. `_chat_evidence.md` shows ONE chat exchange where the user asks a NL question that triggers `list_tables → describe_table → run_sql`. The evidence file MUST contain:
   - The user message
   - The full agent response (with the SQL it ran surfaced in the response, per `intermediate/project-ideas.md` line 60-61)
   - The corresponding SQLcl log file path AND its contents (the human-readable result)
3. `_friction.md` exists.

Same friction format and recovery loop as run #1.

**Final report:** "RUN 2 done. verify={OK|FAIL}. friction: <count>. sqlcl_tee: {ok|broken}. blocked={yes|no}."
````

Run foreground (we need its result before Task 7).

- [ ] **Step 2: Inspect run output**

```bash
ls choose-your-path/tests/intermediate-nl2sql/
cat choose-your-path/tests/intermediate-nl2sql/verify_evidence.txt
cat choose-your-path/tests/intermediate-nl2sql/_chat_evidence.md
ls choose-your-path/tests/intermediate-nl2sql/logs/  # should have sqlcl_*.log
cat choose-your-path/tests/intermediate-nl2sql/_friction.md
```

Same re-dispatch policy as run #1: max 2 retries on Bar-B miss.

- [ ] **Step 3: Snapshot**

```bash
cd choose-your-path/tests/intermediate-nl2sql
docker compose ps
docker compose down
cd /home/ubuntu/work/oracle-ai-developer-hub
```

- [ ] **Step 4: No commit (gitignored)**

---

## Task 7: Runs #3 + #4 — advanced hybrid analyst + advanced self-mem (PARALLEL)

**Files:**
- Create: `choose-your-path/tests/advanced-hybrid-analyst/` and `…/advanced-self-mem/`
- Each contains: full scaffold + `verify_evidence.txt` + `_chat_evidence.md` + `_friction.md`

**Critical:** these run in parallel, but each spawns its own Docker compose project. Pre-task setup ensures port and project-name isolation.

- [ ] **Step 1: Decide port allocation up-front**

| Run | Oracle port (host) | Open WebUI port | Adapter port |
| --- | --- | --- | --- |
| advanced-hybrid-analyst | 1531 | 3010 | 8010 |
| advanced-self-mem | 1541 | 3020 | 8020 |

The `oracle-aidb-docker-setup` skill accepts a `port` input. The run subagents must pass these. The Open WebUI / adapter ports are tier-skill-controlled — the subagent must override the defaults documented in `advanced/SKILL.md` and capture this need-to-override as a friction finding (the skill should accept a port-offset input out of the box).

- [ ] **Step 2: Dispatch BOTH subagents in parallel (single message, two `Agent` tool calls)**

**Run #3 prompt:**

````
You are run #3 of the choose-your-path three-tier friction pass.

**Spec + Plan:** same paths as runs #1+#2.

**Your job:** Walk `choose-your-path/advanced/SKILL.md` literally. Build **idea 1: Hybrid analyst (NL2SQL + doc-RAG)**. Land everything in `/home/ubuntu/work/oracle-ai-developer-hub/choose-your-path/tests/advanced-hybrid-analyst/`.

**Forbidden** (same as runs #1+#2): no edits under `choose-your-path/`, no tool substitutions, all skill edits happen in consolidation.

**Resolved interview answers:**
- Q1 path: advanced
- Q2 target_dir: `.../tests/advanced-hybrid-analyst/`
- Q3 db target: local Docker
- Q4 inference: OCI GenAI Grok 4 + in-DB ONNX `MY_MINILM_V1`
- Q5 topic: idea 1 (Hybrid analyst)
- Q6 notebook: yes (mandatory at advanced)
- Q7 sql_mode: read_only
- Q8 demo focus: "polished UI demo" (8 cells in notebook, last launches the adapter)

**Port overrides (parallel-run isolation):** Oracle host port=1531, Open WebUI=3010, adapter=8010. Compose project name=`adv-hybrid` (set via `COMPOSE_PROJECT_NAME=adv-hybrid` in `<target>/.env`). Volume name=`oracle_adv_hybrid_data`. The advanced skill defaults differ — when you discover what to override, log it as a friction finding pointing at the skill's lack of port-offset input.

**Conda env:** `cyp-adv-hybrid`.

**ONNX export-and-register:** same onnx2oracle ground-truth check as run #2. Re-running the export is fine (it's idempotent at the DB level); just don't share the ONNX file with run #4.

**Seed corpora:** copy from `/home/ubuntu/work/oracle-ai-developer-hub/scripts/cyp-runs/seed_runbooks/` to `<target>/data/`. Distribute:
- `glossary.md` → `<target>/data/glossary/glossary.md` → ingest into GLOSSARY collection
- `runbook-restart-pipeline.md` → `<target>/data/runbooks/` → RUNBOOKS collection
- `decision-2025-q4-vector-store.md` → `<target>/data/decisions/` → DECISIONS collection

(The advanced/SKILL.md step 7 + 10 says ingest.py walks data/ subdirs.)

The advanced skill ALSO scaffolds the seed_dummy.sql (10 fake tables, ~50K rows). Run that too.

**Success bar (Bar B):**
1. `verify_evidence.txt` shows `verify: OK (db, vector, inference, mcp, memory, no_forbidden_imports)`.
2. `_chat_evidence.md` shows ONE chat exchange where the user asks a question that the router classifies and routes (e.g. "what does our Q3 decision say about vector stores?" → router picks "knowledge", agent uses `vector_search` against DECISIONS, cites `decision-2025-q4-vector-store.md`). The exchange MUST cite the source — either a SQL statement (data path) or a vector-hit chunk (knowledge path).
3. `_friction.md` exists.

Same friction format and recovery loop.

**Final report:** "RUN 3 done. verify={OK|FAIL}. friction: <count>. blocked={yes|no}."
````

**Run #4 prompt:**

````
You are run #4 of the choose-your-path three-tier friction pass.

**Spec + Plan:** same paths.

**Your job:** Walk `choose-your-path/advanced/SKILL.md` literally. Build **idea 2: Self-improving research agent (Oracle-as-only-state-store with persistent agent memory)**. Land everything in `/home/ubuntu/work/oracle-ai-developer-hub/choose-your-path/tests/advanced-self-mem/`.

**Forbidden** (same as other runs).

**Resolved interview answers:**
- Q1 path: advanced
- Q2 target_dir: `.../tests/advanced-self-mem/`
- Q3 db target: local Docker
- Q4 inference: OCI GenAI Grok 4 + in-DB ONNX
- Q5 topic: idea 2 (Self-improving research agent)
- Q6 notebook: yes (mandatory)
- Q7 sql_mode: read_only
- Q8 demo focus: "deep_dive" (12-15 cells walking memory + MCP + agent loop + ONNX SQL)

**Port overrides:** Oracle=1541, Open WebUI=3020, adapter=8020. Compose project=`adv-selfmem`. Volume=`oracle_adv_selfmem_data`.

**Conda env:** `cyp-adv-selfmem`.

**The verify pivot for THIS run:** memory must persist across processes. The bar:
- Run the agent ONCE: give it the task `"Research the difference between Arrow and Parquet for time-series workloads. Save what you learn."`. Let the agent call `web_fetch` (or hit a small mock; if web_fetch fails, the run logs that as friction and uses the seed runbook content as the input corpus instead — capture the substitution honestly).
- Verify `SESSION_SUMMARIES` has 1 row after run 1.
- Run the agent AGAIN, in a SEPARATE process (`python -m <pkg>.adapter` exits between runs): give it the task `"What did I research about Arrow last time?"`.
- The second run MUST retrieve the SESSION_SUMMARIES row written by the first run, and the response MUST quote text from it. If the agent answers from pre-trained knowledge ("Arrow is a columnar format...") without retrieving the actual row, the run does NOT meet Bar B.

`_chat_evidence.md` MUST capture BOTH runs' user-message and response, plus the SQL evidence that SESSION_SUMMARIES contained the relevant row before run 2 started (a `SELECT id, content_preview FROM SESSION_SUMMARIES` between runs).

**Success bar (Bar B):**
1. `verify_evidence.txt` shows `verify: OK (db, vector, inference, mcp, memory, no_forbidden_imports)`.
2. `_chat_evidence.md` per the verify pivot above.
3. `_friction.md` exists.

**Final report:** "RUN 4 done. verify={OK|FAIL}. friction: <count>. memory_persists={yes|no}. blocked={yes|no}."
````

Both `Agent` calls go in **one assistant message** so they execute concurrently.

- [ ] **Step 3: Inspect both run outputs**

```bash
for run in advanced-hybrid-analyst advanced-self-mem; do
  echo "=== $run ==="
  cat choose-your-path/tests/$run/verify_evidence.txt 2>&1 | tail -5
  echo "--- chat ---"
  head -30 choose-your-path/tests/$run/_chat_evidence.md
  echo "--- friction count ---"
  grep -c '^## ' choose-your-path/tests/$run/_friction.md 2>&1 || echo "0"
done
```

If either misses Bar B, re-dispatch (max 2 retries each, independent of the other).

- [ ] **Step 4: Snapshot both**

```bash
for run in advanced-hybrid-analyst advanced-self-mem; do
  (cd choose-your-path/tests/$run && docker compose down)
done
```

- [ ] **Step 5: No commit (gitignored)**

---

## Task 8: Aggregate friction findings

**Files:**
- Create: `docs/superpowers/specs/2026-05-05-cyp-friction-findings.md` (consolidation worksheet — committed to repo)

- [ ] **Step 1: Read every `_friction.md`**

```bash
for run in beginner-pdfs intermediate-nl2sql advanced-hybrid-analyst advanced-self-mem; do
  echo "=== $run ==="
  cat choose-your-path/tests/$run/_friction.md
  echo
done
```

- [ ] **Step 2: Write the consolidation worksheet**

Create `docs/superpowers/specs/2026-05-05-cyp-friction-findings.md` with this structure:

```markdown
# choose-your-path friction findings — 2026-05-05

Consolidated from 4 runs in `choose-your-path/tests/`.

## Findings (deduped by proposed skill edit)

### F1 — <short title>
- **Severity:** P0 / P1 / P2
- **Surfaced in:** beginner-pdfs, intermediate-nl2sql (count)
- **Where:** `choose-your-path/<file>:<line>`
- **What:** <symptom>
- **Proposed edit:** <concrete rewrite>

(repeat per finding)

## Pre-seeded findings (from spec)

### P1 — beginner SKILL.md:124 dim assertion
- 1024 → 384

### P2 — intermediate SKILL.md:74 InDBEmbeddings reference
- (resolution per run #2 evidence)

## Decision: SQLcl tee — fold into skill, leave as opt-in, or drop?
- (per run #2's `README_SQLCL.md` opinion + orchestrator judgment)

## Runs blocked
- (none / list)

## Findings deferred to a follow-up pass
- (any P2 not worth fixing this round)
```

The worksheet IS the spec for Task 9's edits. Be concrete: every finding's "Proposed edit" must be the actual file:line and the actual replacement text. If a finding lacks a concrete edit, mark it deferred.

- [ ] **Step 3: Commit the worksheet**

```bash
git add docs/superpowers/specs/2026-05-05-cyp-friction-findings.md
git commit -m "docs(spec): consolidate cyp friction findings from 4 runs"
```

---

## Task 9: Apply skill edits (the deliverable)

**Files:**
- Modify: `choose-your-path/beginner/SKILL.md` (at minimum the line-124 fix)
- Modify: `choose-your-path/intermediate/SKILL.md`, `…/advanced/SKILL.md` (per findings)
- Modify: `choose-your-path/skills/<*>/SKILL.md` (per findings)
- Modify: `choose-your-path/shared/{interview.md,verify.md,references/<*>.md,snippets/<*>.py}` (per findings)
- Possibly modify: `choose-your-path/intermediate/SKILL.md` to fold in SQLcl tee, OR `choose-your-path/shared/references/sqlcl-tee.md` (new file) for opt-in

- [ ] **Step 1: Apply pre-seeded P1 (beginner dim assertion)**

```bash
# Edit choose-your-path/beginner/SKILL.md line 124:
# Before:  - Round-trip: `embedder.embed_query("dim check")` → assert dim == 1024.
# After:   - Round-trip: `embedder.embed_query("dim check")` → assert dim == 384.
```

Use the Edit tool with old_string/new_string. Verify the diff is exactly one line.

- [ ] **Step 2: Apply each finding from the worksheet, one Edit per finding**

For each finding F1..Fn with severity P0/P1, apply the proposed edit verbatim. P2 findings get logged in the consolidation commit message under "deferred" — don't apply them this pass.

After EACH edit, run a quick sanity grep to confirm the change landed:

```bash
grep -n "<expected new text>" choose-your-path/<file>
```

- [ ] **Step 3: Resolve the SQLcl-tee decision**

Three possibilities, decide based on the worksheet:

(a) **Fold into skill** — edit `choose-your-path/intermediate/SKILL.md` step 3c-14 (`adapter.py`) to include the SQLcl-tee hook by default; add a `shared/references/sqlcl-tee.md` documenting install + behavior. Update `shared/interview.md` if the user should be asked.

(b) **Opt-in pattern** — create `choose-your-path/shared/references/sqlcl-tee.md` that documents the pattern but doesn't change the skill. Add a one-line "see also" pointer from `intermediate/SKILL.md`.

(c) **Drop** — the run uncovered enough friction to suggest the tee isn't worth the surface area. Don't add anything. Capture the rationale in the consolidation commit message.

- [ ] **Step 4: Re-read each modified skill section to confirm coherence**

For each modified file, read just the modified region (Edit tool's diff context is enough) and confirm:
- The edit doesn't break a cross-reference (e.g. if `intermediate/SKILL.md` references `shared/references/X.md` and we renamed X, fix the reference).
- The edit doesn't contradict another part of the same file.

- [ ] **Step 5: Stage all skill changes and commit**

```bash
git status
git diff choose-your-path/
git add choose-your-path/
git commit -m "$(cat <<'EOF'
fix(choose-your-path): apply friction findings from three-tier walk

Walked beginner-pdfs / intermediate-nl2sql / advanced-hybrid-analyst /
advanced-self-mem against live Oracle 26ai Free + OCI Grok 4. Each run
landed verify: OK and produced grounded chat evidence (see commit
trailer for run-by-run summary).

Findings worksheet: docs/superpowers/specs/2026-05-05-cyp-friction-findings.md

Summary:
- <N> P0 + <N> P1 edits applied
- <N> P2 deferred (see worksheet)
- SQLcl tee: <fold|opt-in|dropped>
- Runs blocked: <none|list>

Run-by-run:
- beginner-pdfs:           verify OK, friction: <N>
- intermediate-nl2sql:     verify OK, friction: <N>, sqlcl_tee: <ok|broken>
- advanced-hybrid-analyst: verify OK, friction: <N>
- advanced-self-mem:       verify OK, friction: <N>, memory_persists: yes
EOF
)"
```

Fill in the `<N>` placeholders with the actual counts from the worksheet before committing.

- [ ] **Step 6: Final state check**

```bash
git log --oneline cyp-friction-pass-1 ^main
```

Expected commits on the branch:
1. `48278073` docs(spec): add … design
2. `3f4444cf` docs(spec): cite onnx2oracle …
3. `<hash>` scripts: prefetch MiniLM …
4. `<hash>` scripts: seed PDFs and runbooks …
5. `<hash>` docs(spec): consolidate cyp friction findings …
6. `<hash>` fix(choose-your-path): apply friction findings …

Do NOT push and do NOT open a PR — per the spec's Definition of Done, that's the user's call.

---

## Self-Review

**1. Spec coverage:**
- Goal (4 runs walking the skill end-to-end) → Tasks 5, 6, 7. ✓
- Bar B (verify + chat evidence + friction) → each run task's success bar. ✓
- "Forbidden mid-pass skill edits" → spelled out in every run prompt. ✓
- onnx2oracle as canonical reference → run #2 + #3 + #4 prompts. ✓
- SQLcl-tee no-substitution rule → Task 4 + run #2 prompt + Task 9 step 3 decision. ✓
- Pre-existing finding (beginner:124) → run #1 prompt + Task 9 step 1 (P1 fix). ✓
- Two advanced runs in parallel with port isolation → Task 7 step 1. ✓
- Consolidation phase produces single batch of edits → Task 8 + Task 9. ✓
- No PR opened by agent → Task 9 step 6 explicit. ✓

**2. Placeholder scan:** `<N>` placeholders in the Task 9 commit message are intentional — they're filled with concrete counts at commit time, not at plan-write time. No "TBD", no "implement later". The Task 8 worksheet template has `<short title>` etc. which are *fields* (the user fills them when writing the worksheet), not plan placeholders.

**3. Type consistency:**
- Run dirs named consistently (`beginner-pdfs`, `intermediate-nl2sql`, `advanced-hybrid-analyst`, `advanced-self-mem`) across the file structure section, every run task, and Task 8's grep loop. ✓
- Conda env names consistent (`cyp-beginner`, `cyp-intermediate`, `cyp-adv-hybrid`, `cyp-adv-selfmem`). ✓
- Verify-OK lines per tier match the spec exactly. ✓
- Port allocation (1531/3010/8010 vs 1541/3020/8020) consistent across run #3 + #4 prompts. ✓

Plan is complete. No issues to fix.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-05-choose-your-path-three-tier-friction-pass.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best fit here because tasks 5-7 are themselves subagent dispatches; running them inline pollutes the orchestrator's context with 4× verify logs.

**2. Inline Execution** — I execute tasks in this session via executing-plans, batch with checkpoints. Cleaner state, but tasks 5-7 will burn ~40k tokens each on intermediate output.

Which approach?
