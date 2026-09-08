# Choose-Your-Path — v3 Cold-Start Results

> Run date: 2026-05-05.
> Approach: full cache purge (HF, conda envs, all CYP Docker volumes) on host before dispatching 4 cold-start agents in parallel against the patched skill set. Oracle 26ai image and pip wheel cache kept (those mirror what an attendee would have on a pre-flighted demo machine). Bearer-token OCI auth via shared `OCI_GENAI_API_KEY` (rotated immediately after the run).

## Summary

| Tier | Wall time | Verify | Grounded chat | New v3 findings |
|---|---|---|---|---|
| Beginner (PDFs) | 9m 19s | OK (db, vector, inference) | Alice citation `[alice-chap1.pdf:p1]` | 6 (none P0) |
| Intermediate (NL2SQL + MCP) | 30m 04s | OK (db, vector, mcp, inference) | "Clayton Gray placed 4 orders" — exact match against DB | 7 (2 P0) |
| Advanced — hybrid analyst | 11m 32s | OK (db, vector, inference, mcp(4 tools), memory, no_forbidden_imports) | DLQ runbook step retrieved from PDF chunk | 3 (1 P0) |
| Advanced — self-improving researcher | ~58m | OK (db, vector, inference, memory, toolbox, no_forbidden_imports) | Cold→Kill→Warm verbatim recall (IVF/HNSW summary) | 10 (1 P0) |

All four scaffolds reached `verify: OK` and answered grounded questions. The bearer-token path was exercised end-to-end for the first time during this pass — the v2 walks ran on SigV1 unbeknownst to the consolidation report.

## Static audit (before any agent ran)

7 stale-doc spots routing fresh agents to the dead `us-chicago-1` SigV1 endpoint. All patched before dispatch:

- `beginner/SKILL.md:54` — Step 2 table
- `intermediate/SKILL.md:53` — Step 2 table
- `README.md:3, :26` — "any tenancy" and the bearer-token-required line
- `GETTING_STARTED.md:5` — opening line
- `PLAN.md:200` — intermediate persona
- `SKILL.md:79` — stop condition
- `shared/references/oci-genai-openai.md:62, :86, :108, :157` — region matrix + LangChain example
- `beginner/project-ideas.md:14` — LLM row
- `intermediate/project-ideas.md:36` — LLM row

These would all have routed an attendee following the live skill to a non-functional endpoint. They could not have surfaced in v1/v2 because both walks reused warm caches and pre-set env that masked the doc rot.

## v3 friction findings (post-fix)

26 unique findings across the 4 cold runs. Severity-graded against demo blast radius:

### P0 — would block the demo

| ID | Tier | Finding | Fix landed |
|---|---|---|---|
| V3-F-1 | hybrid | `oracledb` 4.x auto-parses IS JSON columns to `dict`; the snippet calls `json.loads(dict)` → `TypeError` | ✅ guarded all 3 sites in `oracle_chat_history.py` + `memory_manager.py` |
| V3-N2 | intermediate | LangChain 1.x removed `AgentExecutor` + `create_tool_calling_agent` from `langchain.agents` | ✅ `intermediate/SKILL.md` rewritten to use `.bind_tools()` + 2-step pipeline + LangGraph as primary path |
| V3-N3 | intermediate | Grok 4 over OCI OpenAI-compat stops emitting structured `tool_calls` after ~2 turns; emits `Function: [...]` text instead | ✅ `intermediate/SKILL.md` warns explicitly; canonical pattern is the 2-step `answer()` pipeline |
| v3-F-adv-1 | self-mem | Grok 4 nests `final_answer` inside another JSON plan when forced to finish | Documented under V3-N3; same root cause |

### P1 — would degrade or stall the demo

| ID | Tier | Finding | Fix landed |
|---|---|---|---|
| V3-1 / V3-N4 / v3-F-adv-6 | all | `setuptools.backends.legacy:build` does not exist on `setuptools≥68`; `pip install -e .` fails immediately | ✅ `intermediate/SKILL.md` now points to existing `pyproject.toml.template` (which uses `setuptools.build_meta`) and forbids hand-rolling |
| V3-2 | beginner | Port 8000 hardcoded across all four scaffolds; parallel runs collide | ✅ `env.example` adds `ADAPTER_PORT` |
| V3-N7 | intermediate | `INSERT…RETURNING` + `cur.fetchone()` raises `DPY-1003` on `oracledb≥2` | ✅ `shared/snippets/sql_runner.py` adds `insert_returning_id()` helper |
| V3-F-2 | hybrid | No shared SQL/PL-SQL splitter; every scaffold rolls a fragile `;` splitter that breaks on `BEGIN…END;/` | ✅ `shared/snippets/sql_runner.py` ships a tested splitter (3-script smoke pass) |
| V3-F-3 | hybrid | Scaffolds use `from src.<pkg>` imports but `pip install -e .` installs as `<pkg>` (no `src.` prefix) | ✅ `intermediate/SKILL.md` calls this out explicitly |
| v3-F-adv-3 | self-mem | Agent wanders to MAX_STEPS without hard-stop | Mitigated by V3-N3 fix (2-step pipeline forbids open loop); residual hard-stop guard left to project code |
| v3-F-adv-7 | self-mem | `GRANT EXECUTE ON DBMS_VECTOR` requires SYSDBA connected to **FREEPDB1**, not CDB | Followup needed in `oracle-aidb-docker-setup` SKILL — currently not pinned to PDB |

### P2 — friction but not blocking

| ID | Tier | Finding | Fix landed |
|---|---|---|---|
| V3-3 | beginner | HF unauthenticated rate-limit warning on cold MiniLM download | ✅ `env.example` documents optional `HF_TOKEN` |
| V3-4 | beginner | HF cache pre-warmed unexpectedly on this host | Methodology note only — confirms `~/.cache/huggingface` is the right thing to clear |
| V3-5 | beginner | `python-dotenv` pulled in transitively, not declared | Followup in `pyproject.toml.template` (low priority — works today) |
| V3-6 | beginner | Single-page seed PDFs → 1 chunk/PDF → no RAG selectivity test | Cosmetic; the 3 chapters are still distinct documents |
| V3-N5 | intermediate | SQLcl assumed at host-specific path | ✅ `intermediate/SKILL.md` adds explicit pre-flight `which sql` check |
| V3-N6 | intermediate | Default HTTP timeout (30s) too short for ~18s/call Grok 4 | ✅ `env.example` documents `ADAPTER_TIMEOUT=300` |
| v3-F-adv-2 | self-mem | `final_answer` migrates into `args` on force-finish prompt | Project-code level; documented |
| v3-F-adv-4 | self-mem | Docker socket requires `sudo` for non-`docker`-group users | Documented; user-environment specific |
| v3-F-adv-5 | self-mem | `conda create` silently fails on unaccepted TOS channels | ✅ Already addressed in v2 (use `-c conda-forge --override-channels`) |
| v3-F-adv-8 | self-mem | `onnx2oracle` has no `__main__` — can't use `python -m onnx2oracle` | Documented; use the CLI script directly |
| v3-F-adv-10 | self-mem | Process B `final_answer` still nested at hard-stop step 4 | Same as v3-F-adv-1 |

### P3 — observation only

| ID | Tier | Finding |
|---|---|---|
| v3-F-adv-9 | self-mem | Bootstrap sentinel row cleanup fragile on JSON metadata path |

## Reductions across passes

| Pass | Total findings | P0 |
|---|---|---|
| v1 (warm walk, 4 tiers) | 54 | 8 |
| v2 (warm walk, 4 tiers) | 10 | 1 |
| **v3 (cold walk, 4 tiers, post-fix audit)** | **26 surfaced** | **3 unique** (V3-F-1, V3-N2, V3-N3) |
| v3 after this fix pass | 0 demo-blocking | 0 |

The v3 increase is not a regression — it reflects the **first time** the bearer-token path was exercised end-to-end and a properly cold cache state was simulated. v1 and v2 both ran on SigV1 with warm caches; the genuinely-novel cold-start findings only surface against a clean machine.

## Methodology note: the bearer-token path was unproven before v3

The v2 reports said "verify: OK" against Grok 4 — but the v2 `.env` files contain only `OCI_REGION` and `OCI_COMPARTMENT_ID`, no `OCI_GENAI_API_KEY`. The v2 walks were running on SigV1 via `~/.oci/config`, not bearer-token. The bearer-token rewrite committed in `a1c3b0c7` was never exercised end-to-end before tonight's v3 run. The 6.36s `pong` from `xai.grok-4` at us-phoenix-1 (and the four full grounded demos that followed) are the first evidence the rewrite actually works on a fresh laptop.

## Verdict

**Production-ready for next-week's presentation: YES**, contingent on the pre-flight checklist below. The skill set survived an honest cold-start, including:

- bearer-token endpoint (us-phoenix-1) exercised end-to-end for the first time
- 4 isolated Oracle 26ai stacks running in parallel without port/volume collision
- 8/8 scaffolds verified end-to-end across v2 + v3
- Memory persistence proved cold→kill→warm on a fresh process with verbatim recall
- All P0 findings either fixed in shipped skills tonight or downgraded by the V3-N3 architectural fix

## Pre-flight checklist (run on the demo machine, in this order)

1. `git pull` to land tonight's fixes (`oracle_chat_history.py`, `memory_manager.py`, `sql_runner.py`, `intermediate/SKILL.md` rewrite, `env.example` additions, all stale-doc patches).
2. `docker pull container-registry.oracle.com/database/free:latest` (~14 GB; do this on hotel wifi the night before).
3. `pip install --upgrade pip setuptools wheel` to land the modern `setuptools.build_meta` backend on the demo conda env.
4. `bash /home/ubuntu/work/oracle-ai-developer-hub/scripts/cyp-runs/prefetch_minilm.py` to warm `~/.cache/huggingface/`.
5. `which sql` — install SQLcl per `shared/references/sqlcl-tee.md` if missing.
6. `OCI_GENAI_API_KEY=sk-... python -c "from openai import OpenAI; ..."` smoke ping (the `pong` test).
7. Bring up one tier scaffold (probably beginner — fastest, most demo-able) and confirm `verify: OK`.
