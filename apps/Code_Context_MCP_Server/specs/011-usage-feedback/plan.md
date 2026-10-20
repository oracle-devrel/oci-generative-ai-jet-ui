# Implementation Plan: Usage Feedback

**Branch**: `011-usage-feedback` | **Date**: 2026-10-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-usage-feedback/spec.md`

## Summary

A new `feedback` module records uses, turns them into a bounded boost at search time, and backs `ccctx feedback`
and `ccctx eval`.

**Recording**: a ninth MCP tool, `mark_used`, records a cited use. `search_code` remembers, per server session,
which results it returned and in which run. When `get_symbol` or `read_wiki` then opens one of them, an opened use is
recorded. Uses go through the existing background run writer, so they follow their run in order, and they never delay
or fail a tool call (R2, R3). A use is one row in a new `ccctx_feedback` table (migration 9), keyed by the result's
repository, path and name, so it survives a re-ingest (R1).

**Ranking**: a result's weight is the sum of its uses' base weights (cited 1.0, opened 0.5), halved every 30 days of
age, computed in SQL when read. Its boost is `cap × min(1, weight / 5)`, with a cap of 20% (R4). `semantic.search`
multiplies each candidate's fused score by `1 + boost` and re-sorts only the candidates it already found. Exact
identifier definitions keep coming first. A page's similarity is boosted the same way for placement. Facts are never
boosted (R5). Every hit shows `relevance` (the score before feedback) and `feedback` (the boost) (R6). A `feedback`
switch (`--no-feedback` on the CLI) ranks without it.

**Operating**: `ccctx feedback list|add|reset` shows weights and boosts, records uses by hand (backdated or many at
once), and wipes a repository's feedback (R9). `ccctx memory list` shows how many of each search's results were
used (R12).

**Measuring**: `ccctx eval --gold gold.json [--with-feedback]` runs a versioned 20-question gold set straight
through `semantic.search`, which records nothing, and prints `Questions` and `recall@10` (R10). The server moves to
1.3.0.

## Technical Context

**Language/Version**: Python 3.11+ (venv 3.11.8)

**Primary Dependencies**: unchanged. `mcp` 1.30 (FastMCP), `oracledb` 26 thin mode. No new package.

**Storage**: Oracle AI Database 26ai.
- **Migration 9**: `ccctx_feedback`, one row per use, with foreign keys to the repository (on delete cascade) and to
  the run that returned the result (on delete set null).

**Testing**: pytest against the local database.
- **Contract tests**: `mark_used`, the new hit fields and the `feedback` switch, the opened uses of `get_symbol` and
  `read_wiki`, and nine tools, in `test_server.py`.
- **Integration tests**: weight, decay, cap, ordering and reset in a new `test_feedback.py`; the CLI in
  `test_cli.py`; the gold evaluation, the hammer check and with-feedback recall in `test_eval.py`.
- **Isolation**: `conftest.py` drops uses for non-`t-` repositories, as it already does for runs.

**Target Platform**: Windows 11 and Linux, stdio MCP server plus the `ccctx` CLI.

**Project Type**: a single Python package, both library and CLI (`src/golestan_code_mcp`).

**Performance Goals**: feedback adds one grouped query per search over a small table, which keeps searches with
feedback within 10% of searches without it (SC-007). Recording stays off the answering path.

**Constraints**:
- The boost never exceeds the cap, and never adds a result.
- Evaluation and CLI search record neither runs nor uses.

**Scale/Scope**: thousands of uses per repository. The per-session record of returned results grows by at most 50
entries per search, for the life of one stdio process.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Checked against constitution **1.1.0**.

| Principle | Assessment |
|---|---|
| I. Database-native intelligence | PASS. Uses are stored, and their decayed weights computed, in Oracle. Nothing is sent outside. |
| II. Structure-aware ingestion | PASS. Ingestion is unchanged. Feedback keys on the parsed symbol's identity, so it survives a re-ingest of unchanged code. |
| III. MCP as the single interface | PASS. `mark_used` is additive, so 1.3.0 (MINOR). `search_code` gains two hit fields and one optional argument; existing calls answer as before, plus the fields. `mark_used` answers in the usual envelope. The CLI calls the same `feedback` functions. |
| IV. Hybrid, explainable retrieval | PASS. Every hit shows the score before feedback and its boost. The cap and half-life are configurable (`CCCTX_FEEDBACK_CAP`, `CCCTX_FEEDBACK_HALF_LIFE_DAYS`) with documented defaults. The retrieval evaluation gains a versioned gold set run with and without feedback. |
| V. Self-improvement with provenance | PASS. Uses are recorded with client, session, time and the run that returned the result. Influence is bounded by the cap, decays by half-life, and is resettable with `ccctx feedback reset`. Feedback never touches indexed content. |
| VI. Measured quality | PASS. Tests come first: a contract test for `mark_used`, recording tests for opened uses, integration tests for weight, cap and decay, and the gold evaluation, the hammer check and with-feedback recall. |
| VII. Safety and simplicity | PASS. One module, one table, no new dependency. Recording reuses the run writer. `add` and `reset` are CLI-only. |

Re-checked after Phase 1: no change.

## Project Structure

### Documentation (this feature)

```text
specs/011-usage-feedback/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── tools.md     # mark_used, search_code changes, opened uses
│   └── cli.md       # ccctx feedback, ccctx eval, search and memory list changes
└── tasks.md         # /speckit-tasks
```

### Source Code (repository root)

```text
gold.json                         # new: the versioned gold set (20 questions, flask and gin)
src/golestan_code_mcp/
├── feedback.py                   # new: record/merge uses, weights and boosts, list/add/reset, eval
├── schema.py                     # migration 9: ccctx_feedback
├── semantic.py                   # Result.relevance/feedback; boost the candidates; feedback switch
├── server.py                     # mark_used; returned-results map; opened uses; SearchHit fields; feedback arg
├── memory.py                     # writer takes uses after runs; run ids kept on the run; RunView.used; NO_FACTS
├── config.py                     # feedback_cap, feedback_half_life
└── cli.py                        # feedback list|add|reset, eval, search --no-feedback and columns, memory list used
tests/
├── conftest.py                   # drop uses for real repositories unless requested
├── test_feedback.py              # new
├── test_server.py, test_cli.py, test_eval.py, test_schema.py, test_config.py
README.md, .env.example, pyproject.toml, src/golestan_code_mcp/__init__.py   # 1.3.0
```

**Structure Decision**: the existing single package. Feedback gets its own module, as memory and wiki did, because it
is used by search, the server and the CLI.

## Complexity Tracking

No violations.
