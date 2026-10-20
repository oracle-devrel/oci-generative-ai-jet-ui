# Contract: MCP tools (server 1.2.0)

Extends `specs/009-module-wiki/contracts/tools.md`. Every rule there still applies.
- **Every tool**: each call is now recorded as a run (research R2), which never changes an answer.
- **`search_code`**: it gains `fact` hits (FR-021, research R14).
- **The other six existing tools** keep their parameters, results and descriptions.

The server lists exactly eight tools. A new tool and a new hit kind are both additive, so the version is `1.2.0`
(MINOR, constitution III).

| Tool | Core call | CLI twin | Change |
|---|---|---|---|
| `recall` | `memory.recall` | `ccctx memory facts`, `ccctx memory list` | new |
| `search_code` | `semantic.search`, now with `memory.search_facts` | `ccctx search` | `fact` hits, one sentence added to the description |

## `search_code`: fact hits

**Description**: one sentence is added after the sentence about page hits: "A hit of kind fact is something an
earlier session worked out about the code at its path; recall lists all of them." Parameters are unchanged.

```json
{"rank": 2, "score": 0.0, "similarity": 0.7104, "keyword_rank": null, "semantic_rank": 1,
 "repo": "flask", "kind": "fact", "name": "url_for", "path": "src/flask/helpers.py",
 "start_line": 188, "end_line": 246, "language": "python", "state": "fresh",
 "snippet": "`url_for` is a function in `src/flask/helpers.py`. It is called by 12 symbols, ..."}
```

| Field | Fact hit |
|---|---|
| `kind` | `fact` |
| `name` | The fact's subject |
| `path`, `start_line`, `end_line` | The subject's current location |
| `language` | The subject's language |
| `state` | Always `fresh`. Stale facts are not returned |
| `snippet` | The fact text, at most 800 characters |
| `score` | `0.0`: facts are placed by similarity, not fused |
| `keyword_rank` | `null` |
| `semantic_rank` | The rank among fact hits |

- **Placement**: per research R14, never above a definition that exactly matches an identifier, and counted
  toward `limit`.
- **Filters**: `repo` and `language` apply to facts as to symbols.

## Server instructions

`FastMCP("golestan_code_mcp", instructions=...)`:

> This server indexes codebases and remembers what earlier sessions learned about them. At the start of a session,
> call recall (with the repository if you know it) to load the facts already worked out. Call recall before
> searching for something an earlier session may already have found. Use search_code, get_symbol and the graph
> tools for what recall does not answer.

## `recall`

### Description

**`recall`**: Call this at the start of a session, and before searching, to load what earlier sessions already worked out about a codebase. Returns the stored facts, fresh first and most confident first, or most related to topic when one is given, and the most recent tool calls. Each fact has its subject (a symbol or wiki page), its text, a confidence from 0 to 1, whether it is fresh or stale (and why), what wrote its text (a configured model or the template distiller), the IDs of the runs it was distilled from, and the repository, path and line range of the code it describes. A stale fact describes code that has changed since; check it with get_symbol before relying on it. Facts are distilled from earlier calls by ccctx memory consolidate and after every ingestion. Next step: get_symbol on a fact's subject to read its source, or search_code for what recall does not cover.

### Parameters

| Name | Type | Description |
|---|---|---|
| `repo` | `str \| None` | Recall only this registered repository, for example flask. list_repositories gives the valid names. Default: all repositories. |
| `topic` | `str \| None` | Put the facts most related to this first, for example "sessions" or "url_for". Default: most confident first. |
| `limit` | `int` | How many facts to return, 1 to 50. Default 20. |

Unknown arguments are refused, like the other tools.

### Result

```json
{"status": "ok", "reason": null, "total": 9, "truncated": false,
 "facts": [{"id": "3f9a1c2e-...", "repo": "flask", "subject": "url_for", "kind": "function", "state": "fresh",
            "stale_reason": null, "confidence": 0.938, "distiller": "template/1",
            "text": "`url_for` is a function in `src/flask/helpers.py`. It is called by 12 symbols, ...",
            "questions": ["where is url_for defined", "where's url_for defined?"],
            "runs": [40, 41, 42, 44], "updated_at": "2026-10-12T08:15:02Z",
            "sources": [{"role": "subject", "name": "url_for", "kind": "function", "repo": "flask",
                         "path": "src/flask/helpers.py", "start_line": 188, "end_line": 246}]}],
 "runs": [{"id": 44, "at": "2026-10-12T08:14:40Z", "tool": "search_code", "question": "where's url_for defined?",
           "client": "claude-code 2.1.4", "status": "ok", "result_count": 10,
           "top": {"repo": "flask", "kind": "function", "name": "url_for", "path": "src/flask/helpers.py",
                   "start_line": 188, "end_line": 246}}]}
```

| Field | Type | Rule |
|---|---|---|
| `facts` | list, at most `limit` | Order per research R10 |
| `facts[].id` | `str` | The package record ID |
| `facts[].kind` | `str` | The subject's kind: a symbol kind, or `page` |
| `facts[].distiller` | `str` | `template/1`, or `llm:<model>` when the configured model wrote the text |
| `facts[].questions` | list, at most 5 | Newest first |
| `facts[].runs` | list, at most 20 | The newest run IDs, oldest first |
| `facts[].sources` | list | The subject first, then related records. A removed record has `path`, `start_line` and `end_line` null |
| `runs` | list, at most 10 | The newest runs in scope, without `recall`'s own runs |
| `runs[].top` | object or null | The first result's identity and location |
| `total` | `int` | Facts in scope |
| `truncated` | `bool` | `total > len(facts)` |

- **Unknown repository**: `status: "unavailable"` with `reason: "no repository named '<name>'"` and empty lists.
- **Database down**: `status: "unavailable"` with the driver's reason, like the other tools.
- **Topic**: an empty topic is refused before connecting. A repository with no memory gives `ok` with empty lists.

Annotations: `readOnlyHint: true`. It writes nothing except its own run, and never calls the configured model.

## Recording (all eight tools)

- **Every call is a run**, including refused ones and `recall` itself (FR-001), with the fields in `data-model.md`.
- **Recording never changes the result.** If the database is down, the run is dropped and stderr gets
  `{"event": "memory_record_failed", "tool": ..., "reason": ...}`. Nothing else changes.
- **The existing `{"event": "tool", ...}` stderr record is unchanged**, and still carries no arguments or results.
