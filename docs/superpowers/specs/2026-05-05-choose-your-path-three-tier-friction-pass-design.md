# choose-your-path — three-tier friction pass

**Date:** 2026-05-05
**Branch (work):** main → `cyp-friction-pass-1` (created at implementation time)
**Status:** design

## Goal

Walk the `choose-your-path` skill set as a real user across **four scaffolded projects** (one beginner, one intermediate, two advanced), against a live Oracle 26ai Free container and the OCI Generative AI Grok 4 endpoint already verified on this machine. Capture every point of friction. Feed those findings back into the skills as edits so the next user — typically an Oracle DevRel influencer — meets minimal resistance.

The deliverable is **not** four scaffolded apps. The deliverable is a set of **skill edits** (committed to the developer hub) and an **evidence trail** (the four working scaffolds, each with `verify.py` green and one captured chat exchange) that justifies them. but, also the scaffolded apps need to be build and everything, so they are also deliverables for this testing.

## Why now

`choose-your-path/` was last touched on 2026-05-01 (commits `c82b01f2` … `85bf7234`). It has never been walked end-to-end as a user against live infrastructure on this machine. The skill claims agent-agnostic markdown with no per-tier surprises — the only honest test of that claim is to perform the walk. Skill bugs found this way are concrete and citeable; bugs imagined from reading code are speculative.

## Scope

### In scope

| Tier | Project | Path skill | Notes |
| --- | --- | --- | --- |
| beginner | PDFs-to-chat (idea 1 of 3) | `choose-your-path/beginner/SKILL.md` | Most friction-prone of the three (PDF chunking is the canonical beginner stumble). Python-side MiniLM embeddings (`HuggingFaceEmbeddings`, 384 dim). |
| intermediate | NL2SQL data explorer (idea 1 of 3) **+ SQLcl-tee logging extension** | `choose-your-path/intermediate/SKILL.md` | MCP is the headline — SQLcl tee is supporting evidence (human-readable logs of every SQL the agent issues). The SQLcl tee is **new surface area** not in the skill today; friction-finding pass decides whether to fold it into the skill or leave it as an opt-in extension. ONNX export-and-register follows `github.com/jasperan/onnx2oracle` as the canonical known-good reference; any divergence between the intermediate skill's instructions and onnx2oracle becomes a friction finding. |
| advanced | Hybrid analyst (idea 1 of 3) | `choose-your-path/advanced/SKILL.md` | Multi-collection `OracleVS` (GLOSSARY / RUNBOOKS / DECISIONS / CONVERSATIONS) + MCP + chat history. The "what would I actually ship at work" angle. ONNX export-and-register follows `github.com/jasperan/onnx2oracle`; divergence is a finding. |
| advanced | Self-improving research agent (idea 2 of 3) | `choose-your-path/advanced/SKILL.md` | Oracle-as-only-state-store with persistent agent memory. Run-twice memory-recall is the verify pivot. ONNX export-and-register follows `github.com/jasperan/onnx2oracle`; divergence is a finding. |

Each project lands in `choose-your-path/tests/<run-name>/` (gitignored). The four runs are:

- `choose-your-path/tests/beginner-pdfs/`
- `choose-your-path/tests/intermediate-nl2sql/`
- `choose-your-path/tests/advanced-hybrid-analyst/`
- `choose-your-path/tests/advanced-self-mem/`

Each run carries a `_friction.md` file at its root capturing every step where the skill misled, surprised, or required a workaround.

### Out of scope

- Beginner ideas 2 + 3 (Markdown-to-chat, Web-pages-to-chat). Same skeleton as PDFs.
- Intermediate ideas 2 + 3 (Schema doc generator, Hybrid retrieval). Same shape as NL2SQL.
- Advanced idea 3 (Conversational schema designer). Riskiest (DDL via MCP in `read_write` mode); deferred.
- The `archive/` directory's superseded ideas. Frozen on purpose.
- Ollama fallback paths. The active tiers are OCI-only by design.
- `verify.py` "Bar C" adversarial breaking. Out of scope; deferred to a follow-up if the user wants it.

## Success bar (per project)

**Bar B** as agreed in brainstorming:

1. **`verify.py` exits 0** with the per-tier expected line:
   - beginner: `verify: OK (db, vector, inference)`
   - intermediate: `verify: OK (db, vector, inference, mcp)`
   - advanced: `verify: OK (db, vector, inference, mcp, memory, no_forbidden_imports)`
2. **One real chat exchange captured to disk** — `_chat_evidence.md` showing user message + grounded response. Per tier:
   - beginner: a question whose answer requires retrieval from at least one ingested PDF, with citation `(filename:page)`.
   - intermediate: a NL question that triggers `list_tables → describe_table → run_sql`, with the executed SQL surfaced in the response **and** captured in the SQLcl tee log.
   - advanced-1: a question that routes through the router classifier and pulls from at least one of GLOSSARY / RUNBOOKS / DECISIONS, with the SQL or vector hit cited.
   - advanced-2: run twice in separate processes; second run must demonstrably retrieve a `SESSION_SUMMARIES` row written by the first run (the test of "memory persists, agent self lives in Oracle").
3. **Friction log written** for the run. Even if zero friction. An empty `_friction.md` is itself a finding.

A run is **not done** until all three pieces are on disk and the chat evidence is non-empty and grounded (not the model's pre-trained guess).

## Architecture

### How the runs are driven

Each run is one **subagent invocation** (`oh-my-claudecode:executor`, model=opus, max thinking) that:

1. Receives the run name, target dir, the chosen project idea, the friction-log path, and a pointer to this spec.
2. Reads the appropriate path `SKILL.md` end-to-end before starting (no skipping the references step).
3. Walks the skill literally, including the interview. The agent answers the interview's six questions on its own using the spec's resolved choices — but **records every question/answer pair in `_friction.md`** so we can see places where the interview wasn't useful or asked the wrong thing.
4. Runs `verify.py`. On failure, follows `shared/verify.md`'s 3-retry recovery loop, **logging each failure + applied fix** to `_friction.md`.
5. Captures the chat evidence per the success-bar table above.
6. On success, marks the run done. On 3-retry failure, marks the run blocked and surfaces enough context for the orchestrator to decide.

The orchestrator (this conversation, after writing-plans hands off) drives the four subagents via `oh-my-claudecode:ralph` (single-task self-referential loop until verification reviewer approves). One subagent per run. Beginner runs first (cheapest, smokes the whole stack); intermediate second; the two advanced runs **in parallel** at the end.

### SQLcl-tee logging extension (intermediate)

Inside `tests/intermediate-nl2sql/`, in addition to whatever the skill scaffolds, we add:

- **`sql/`** — directory for SQLcl scripts the agent generates.
- **A logging hook in `adapter.py`**: when the agent emits a `run_sql` tool call, the adapter writes the SQL to `sql/run_<timestamp>.sql`, invokes `sql -L /opt/oracle/sqlcl/bin/sql -S <connect> @sql/run_<timestamp>.sql > logs/sqlcl_<timestamp>.log 2>&1` in the background (best-effort; never blocks the agent's response), and embeds a `[sqlcl_log]` reference in the streamed response.
- **`README_SQLCL.md`** — explains the extension and how to inspect logs.

Why a separate file: this is **net-new surface area not in the skill today**. The friction-finding step decides whether to fold it into `intermediate/SKILL.md` permanently. If yes, it becomes part of the canonical scaffold. If no, it stays as an opt-in pattern documented in `shared/references/`.

### Forbidden during runs

- Per-run agents may **not** edit files under `choose-your-path/` itself. Their job is to run the skill, not to fix it. Skill edits happen only after all four runs are done, in the consolidation phase, by the orchestrator. This guarantees that all four runs see the **same skill state**, so friction findings are comparable and not skewed by mid-pass changes.
- Per-run agents may **not** modify the OCI config or the Oracle container's compose file once the docker-setup skill produced it. If the compose file is wrong, that's a finding, not a workaround.

### Friction taxonomy

`_friction.md` entries use this format so consolidation is mechanical:

```
## <short title>
- **where:** path to skill file + line range, OR step number in the SKILL
- **what:** literal observed behavior or message
- **expected:** what the skill led the user to expect
- **fix applied (if any):** one-line description; null if blocked
- **proposed skill edit:** "edit X in <file>:<line> to say Y" — concrete enough that the consolidation phase can apply it without re-deriving the cause
```

The consolidation phase walks all four `_friction.md` files, dedupes by **proposed skill edit**, and produces a single batch of edits committed on `cyp-friction-pass-1`.

### Pre-existing findings (already spotted while reading)

These are noted now so they don't get rediscovered noisily during the runs:

1. **`choose-your-path/beginner/SKILL.md:124`** says `assert dim == 1024` in the verify spec. Every other line in the skill (and the project-ideas.md, the OVERVIEW, the README) says `384` for MiniLM-L6-v2. Copy-paste from a previous larger-model variant. → edit to `384`.
2. **`choose-your-path/intermediate/SKILL.md:74`** asserts the helper writes an `InDBEmbeddings` subclass. Whether the helper actually ships it (vs. naming it differently or not at all) is a verify-time question. The intermediate run will surface the answer.

These two are seeded into `cyp-friction-pass-1` so the runs don't have to rediscover (1), and the run that hits (2) writes the answer into its `_friction.md` rather than re-asking.

## Data flow

```
brainstorming  →  this spec  →  writing-plans  →  ralplan  →  team of 4 ralph-loop subagents
                                                                  │
                                                                  ├── beginner-pdfs (sequential first)
                                                                  ├── intermediate-nl2sql (sequential)
                                                                  ├── advanced-hybrid-analyst (parallel)
                                                                  └── advanced-self-mem        (parallel)
                                                                  │
                                                                  ▼
                                                            4 _friction.md files
                                                                  │
                                                                  ▼
                                                  consolidation phase (orchestrator)
                                                                  │
                                                                  ▼
                                                  cyp-friction-pass-1 PR with skill edits
```

The handoff between brainstorming and the run team is the spec at this path. The handoff between the run team and the consolidation phase is the four `_friction.md` files plus the four `verify` exit codes.

## Error handling

| Failure mode | Response |
| --- | --- |
| `verify.py` fails with a known fix in `shared/verify.md` | Apply per the recovery loop, max 3 retries. Each fix logged. |
| `verify.py` fails with an unknown error after 3 retries | Run is **blocked**, not failed. Surface stderr + state. Other runs continue. The orchestrator decides whether to repair or punt to a follow-up. |
| Docker container won't come up | Run blocks immediately. Most likely a port conflict; the docker-setup skill ought to detect this — capture as a P0 friction finding. |
| Grok 4 returns 429 / quota | Pause the run, wait, retry once. If still failing, mark blocked. |
| Grok 4 returns a model-routing error (region mismatch) | This shouldn't happen — the probe already validated `us-chicago-1`. If it does, capture as a friction finding pointing at the OCI config validator in the skill. |
| ONNX export fails (intermediate / advanced) | Surface error, capture finding. Likely BertTokenizer vs. SentencePiece confusion — the skill already calls this out in step 0; verify the warning landed where it needed to. |
| `_friction.md` is empty | Don't fabricate findings. Empty is a valid result — it means the run hit zero surprises. The consolidation phase notes it. |
| One advanced run blocks the other | They run in parallel but in **separate Docker projects** (different compose project name and container/volume names) so they don't share state. If they conflict on port 1521 / 3000 / 8000, that's a finding pointing at the docker-setup skill (it should accept a port offset input). |

## Testing

This spec is itself the test plan for `choose-your-path` — the runs are how we test it. There is **no separate "unit-test the skills" step** because the skills are markdown procedures, not code. The closest analogue is:

- **Each run's `verify.py`** — the skill's own self-test, gated per the success bar.
- **The chat-evidence step** — a behavioral check that goes beyond verify (verify proves wires connected; chat evidence proves the project actually does the thing).
- **The consolidation phase** — re-reads each updated skill section and confirms the edit lines up with the friction citation.

After consolidation, a **fifth run** (out of scope for this spec, but recommended as a follow-up) would re-walk one tier with the edits applied and confirm friction dropped. That validation is deferred.

## Open questions / risks

- **OCI cost.** Each tier makes Grok 4 calls during verify and chat evidence. Beginner ≤ 3 calls; intermediate ≤ 8 (tool-call rounds); advanced ≤ ~15 each (router + agent + memory writes). Total budget: a few dollars on the Grok 4 on-demand price. Acceptable.
- **MiniLM model download.** First run pulls ~90MB from HF. If HF is rate-limited, beginner blocks. Mitigation: pre-cache once before kicking off runs.
- **Two advanced runs in parallel.** Risk of hitting OCI quota. Mitigation: if 429s start, sequence them.
- **The SQLcl tee** assumes SQLcl is installable; on Ubuntu 24.04 it's a Java app distributed as a zip. The run agent installs SQLcl via Oracle's published zip + a JRE, captures every step in the friction log, and **does not substitute another tool**. The user explicitly asked for SQLcl-tee logging — substituting `sqlplus` would silently change what's being demonstrated. If SQLcl install genuinely cannot complete, the run is **blocked** at that step and surfaced for orchestrator decision; it is not "softened" into a different tool.
- **Bar B "grounded response" is judgment-call**, not a hard checker. The run agent has to decide whether the chat exchange is grounded; the orchestrator spot-checks one per tier during consolidation. If we discover this is fuzzy, future passes can add a per-tier rubric.

## Definition of done

- 4 dirs under `choose-your-path/tests/` exist; each contains `verify.py` exit-0 evidence, `_chat_evidence.md`, and `_friction.md`.
- `cyp-friction-pass-1` branch on the `oracle-ai-developer-hub` repo carries skill edits citing each consolidated friction finding.
- A short summary table in the consolidation commit message lists: # of edits applied, # of edits deferred, runs blocked (with reason). No PR opened by the agent — that's the user's call.
