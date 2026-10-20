# Implementation Plan: Agent Memory

**Branch**: `010-agent-memory` | **Date**: 2026-10-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-agent-memory/spec.md`

## Summary

A new `memory` module gives the server three layers: runs (every MCP call), facts (one per subject per repository),
and a `recall` tool. Facts live in Oracle's AI Agent Memory package (`oracleagentmemory`), as the user decided.

**Recording**: `server._logged` builds a run from the arguments, the client's handshake info, and the result's
identities and locations (never source text). It queues the run for one background writer that inserts into our
`ccctx_memory_runs` tables (research R2 to R4).

**Distilling**: `memory.consolidate` turns each run not yet consolidated into one finding about the first result's
code (clarification Q1, R5), and merges findings by subject key into package `fact` records.
- **Metadata**: findings, question wordings, run IDs, references, confidence, state and distiller (R6, R7).
- **Text**: written by the configured model through the package's `Llm` adapter, or by local templates when none is
  configured (R13, constitution 1.1.0).
- **Lifecycle**: stale facts become `INVALID` records, and contradictions become package `contradicts` links.

**Keeping up with the code**: each consolidation first re-checks fresh facts. A removed subject makes the fact
stale. An edited one is re-asked: its stored tool calls run again against the new index, and the fact stays fresh
only if the same subject answers (clarification Q2, R8). `ccctx ingest` consolidates after the wiki refresh, and a
failure never undoes the ingestion (R9).

**Recall**: `recall` and `ccctx memory list|consolidate|facts` read the result. Topic ranking uses the package's
search over facts, embedded by `OracleDBEmbedder` with the in-database model search already uses (R10). The server
gains `instructions` telling clients to recall first (R11), and moves to 1.2.0.

**Facts in search** (Principle V): `search_code` and `ccctx search` also return fresh facts as `fact` hits. They are
placed by in-database similarity with the wiki-page rule, and never above an exact identifier match (FR-021, R14).

## Technical Context

**Language/Version**: Python 3.11+ (venv 3.11.8)

**Primary Dependencies**:
- `mcp` 1.30: FastMCP, `instructions`, `get_context()` for `clientInfo`.
- `oracledb` 26 thin mode.
- New: `oracleagentmemory` 26.8, which brings `litellm`, `aiohttp`, `httpx`, `pillow`, `cryptography` and `numpy`.
  It is imported lazily (R1).

**Storage**: Oracle AI Database 26ai.
- **Migration 8**: our two run tables, with JSON columns for arguments and results, plus a Python step that has the
  package create its `ccctx_mem_` tables (facts and their links).
- **Runtime**: package clients use `SchemaPolicy.REQUIRE_EXISTING`, so no table is created outside a migration.

**Testing**: pytest.
- **Contract tests**: `recall` and recording for all eight tools, in `test_server.py`.
- **Integration tests**: against the local database, in `test_memory.py`, `test_ingest.py` and `test_cli.py`.
- **The model**: tests use the template distiller, plus a fake `Llm` for the model path. No test needs a network or a
  key.

**Target Platform**: Windows 11 and Linux, stdio MCP server plus the `ccctx` CLI.

**Project Type**: a single Python package, both library and CLI (`src/golestan_code_mcp`).

**Performance Goals**:
- Consolidating 1,000 runs takes under 1 minute with the template distiller (SC-004). Model calls are reported
  separately.
- `recall` answers under 2 seconds whatever the log size (SC-007).
- Recording adds under 5% to tool latency (SC-008), and never imports the package.
- Search with facts keeps the retrieval evaluation's top-5 hit rate (SC-009, SC-011). The package import (about a
  second) is paid once per process, and only when a repository in scope has facts.

**Constraints**:
- Runs never hold source (FR-002).
- Recording never reaches the client (FR-003).
- With no model configured, nothing leaves the database and no key is needed (FR-008a).
- Merging, confidence and staleness never depend on the model (R13).

**Scale/Scope**: thousands of runs a week across 2 sample repositories. Facts grow with distinct subjects (tens to
hundreds per repository), not with runs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Checked against constitution **1.1.0**.

| Principle | Assessment |
|---|---|
| I. Database-native intelligence | PASS under the 1.1.0 exception. Indexing is unchanged and sends nothing out. Memory distillation sends tool results and the subject's source only to a model the operator configures with `CCCTX_MEMORY_MODEL`. Without one, the template distiller sends nothing and no key is needed. The per-fact prompt is the only model call: package linking is off. What is sent is listed in R13 and the README. Model text naming code that isn't in the findings is rejected. Every fact records its distiller. Fact embeddings and fact-hit similarities use the in-database model. |
| II. Structure-aware ingestion | PASS. Ingestion only gains a consolidation call after it commits. Facts reference symbols at their parsed boundaries. |
| III. MCP as the single interface | PASS. `recall` is additive, so 1.2.0 (MINOR). The seven tools keep their contracts. `recall` is bounded (at most 50 facts, 10 runs), never calls the model, and every fact carries the repository, path and line range of its code. The CLI calls the same `memory` functions. |
| IV. Hybrid, explainable retrieval | PASS. Code hits keep their fused ranking. Fact hits are placed by their shown similarity with the wiki-page rule, and never above an exact identifier match (R14). Facts expose their confidence and the counts behind it, and recall's order is documented (R10). The retrieval evaluation is rerun. |
| V. Self-improvement with provenance | PASS. Facts are searchable alongside code through `search_code` (FR-021). Every fact records its source runs, consolidator, distiller, timestamps and the content hash of each record it references. Changed code is re-asked, not trusted. Runs record the calling client. Memory never alters indexed content. |
| VI. Measured quality | PASS. Tests come first: a `recall` contract test, recording tests for every tool, and integration tests for merging, idempotency, re-ask and staleness. The model path is tested with a fake `Llm`. The retrieval evaluation is rerun as a regression check. |
| VII. Safety and simplicity | PASS with one tracked cost: the package's dependencies (Complexity Tracking). Indexed code is only read. The staleness check uses a scratch clone. One module, two tables, one background thread. |

Re-checked after Phase 1: no change.

## Project Structure

### Documentation (this feature)

```text
specs/010-agent-memory/
├── plan.md              # this file
├── research.md          # R1 to R13
├── data-model.md        # migration 8 run tables, the fact record and its metadata, state transitions
├── quickstart.md        # the live checks for US1 to US4, with and without a model
├── contracts/
│   ├── cli.md           # ccctx memory list|consolidate|facts, the ingest Memory line
│   └── tools.md         # recall, server instructions, recording for all tools, 1.2.0
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/golestan_code_mcp/
├── memory.py      # new: recorder (queue + writer thread), findings, consolidate, recheck/re-ask,
│                  #      distillers (template, package Llm), facts, recall, forget, search_facts,
│                  #      create_package_schema
├── schema.py      # migration 8: ccctx_memory_runs, ccctx_memory_run_repos, the package-schema Python step
├── semantic.py    # fact hits merged into search with the page placement rule
├── config.py      # CCCTX_MEMORY_MODEL, _BASE, _KEY (all optional)
├── server.py      # _logged records a run; recall tool; FastMCP instructions; 1.2.0
├── ingest.py      # consolidate after the wiki refresh; Summary.memory
├── cli.py         # memory list|consolidate|facts; Memory line in the ingest summary
├── registry.py    # note: a future repo removal must call memory.forget
└── __init__.py    # 1.2.0
tests/
├── test_memory.py   # new: findings per tool, merge, confidence, idempotency, re-ask, forget, recall order,
│                    #      template and fake-Llm distillers
├── test_semantic.py # fact hits: placement, filters, limit, stale excluded
├── test_server.py   # recall contract, search_code fact hits, every tool recorded, recording failure
├── test_ingest.py   # consolidation after ingest, failure does not undo it
├── test_cli.py      # memory commands and outputs, ingest Memory line
├── test_config.py   # the memory model settings
└── test_schema.py   # migration 8
README.md, pyproject.toml, uv.lock, .env.example```

**Structure Decision**: memory is one new module, like `wiki.py`: a new capability called from `server.py`,
`ingest.py`, `semantic.py` and `cli.py`. It wraps the package behind six functions (`create_package_schema`,
`consolidate`, `facts`, `recall`, `search_facts`, `forget`), so no other module imports `oracleagentmemory`.

## Complexity Tracking

| Cost | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `oracleagentmemory` and its six heavy dependencies (`litellm`, `aiohttp`, `httpx`, `pillow`, `cryptography`, `numpy`) | The user chose to use Oracle's AI Agent Memory package in full, including its model, for fact storage, search, links and distillation (clarification 2026-10-12) | Our own five tables with no new dependency (the first plan) were rejected by the user. Import cost is contained by importing lazily (R1). |
| The package's automatic thread extraction is not used | Facts must keep run IDs and merge by subject key (FR-007, FR-009) | Thread extraction writes free-text memories without either. The package's `Llm` is called directly per fact instead (R1, R13). |
| A Python step inside migration 8 | The package's tables must come from a migration (Technology & Data Constraints) | Letting the package create tables on first use puts schema changes outside `ccctx db migrate`. Copying the package's DDL into SQL migrations would drift from the package's own versions. |
| A background writer thread for runs | Recording must not slow or change answers (FR-003, SC-008) | An insert on the tool's own connection misses refused calls, and a second connection per call costs more than the call (R2). |
