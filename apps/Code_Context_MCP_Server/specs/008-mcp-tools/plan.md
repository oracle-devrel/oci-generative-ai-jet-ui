# Implementation Plan: Code Context Tools for AI Clients

**Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

## Summary

The stdio server from earlier steps becomes the client-facing product. `ccctx mcp` starts it, and its tool set is reshaped into six tools with model-oriented descriptions: `search_code`, `get_symbol`, `find_callers`, `impact_of`, plus `list_repositories` and `find_callees`. `health` and the old `search`, `callers`, `calls` and `impact` names are removed, and the version moves to 1.0.0.

Most of the work reuses what exists. The hybrid search core gains a language filter, a result count and a snippet per hit, and `ccctx search` gains matching `--language` and `--limit` options so the two stay identical. A new `graph.definitions` reads named definitions back with their stored source, using the same name rules as the graph commands. The graph tools are the step 7 tools renamed. No schema change is needed: `ccctx_symbols.source` already holds every definition's text and `ccctx_files.language` its language.

## Project Structure

```text
pyproject.toml              version 1.0.0
src/golestan_code_mcp/
  __init__.py               __version__ = "1.0.0"
  semantic.py               search(): language filter, limit 1-50, language and snippet on each Result
  graph.py                  definitions(): named definitions with source, total and cut flags
  cli.py                    `ccctx mcp`; search --language and --limit
  server.py                 six tools, parameter descriptions, read-only annotations
tests/
  test_semantic.py          language filter, limit, snippet, refusals
  test_graph.py             definitions(): qualified, bare, repo scope, cap, long source, unknown name
  test_cli.py               mcp command starts the server; search --language and --limit
  test_server.py            tool list and schemas, parity with the core and CLI, refusals as results
README.md                   install, Inspector, `claude mcp add`, tool reference, rename note
```

**Structure Decision**: no new module. Search behavior stays in `semantic.py`, name matching in `graph.py`, and `server.py` stays a thin layer of envelopes over the core, as the constitution requires of the CLI and server.

## Constitution Check

| Principle | Assessment |
|---|---|
| I. Database-Native Intelligence | PASS. Search, source lookup and graph queries all run in the database. Nothing new leaves it. |
| II. Structure-Aware Ingestion | PASS. Ingestion is unchanged. `get_symbol` returns the syntactic units ingestion stored. |
| III. MCP as the Single Interface | PASS. Every query capability stays reachable over MCP, through `find_callees` and `list_repositories` as well as the four named tools. Renaming tools is a breaking change, so the version goes to 1.0.0 and the README records the rename. Results stay bounded and carry repository, path and lines. |
| IV. Hybrid, Explainable Retrieval | PASS. `search_code` is the hybrid search and keeps the fused, keyword and semantic scores on every hit. |
| V. Self-Improvement with Provenance | Not touched by this step. |
| VI. Measured Quality | PASS. Each tool has a contract test through an in-memory client. The retrieval evaluation (`test_eval.py`) is rerun because search output changes, although the ranking does not. Tool choice is measured with five questions in a real client (SC-003). |
| VII. Safety & Simplicity | PASS. `get_symbol` serves stored source and never reads or runs the indexed repository. No listener, no new dependency, no new module. Credentials still come from the environment or `.env`. |

Re-checked after design: no change. The contracts add no table, process or dependency.
