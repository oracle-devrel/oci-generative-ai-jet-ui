# Contract: MCP tools (server 1.0.0)

Replaces `specs/001-dev-environment-setup/contracts/health-tool.md`, `specs/005-hybrid-search/contracts/search-tool.md` and `specs/007-code-graph/contracts/graph-tools.md`. Started by `ccctx mcp` (see `cli.md`), over stdio only: no port, no authentication. Standard output carries protocol messages only; every log line goes to standard error.

The server lists exactly six tools. This is a breaking change (constitution III), so the version is `1.0.0`.

| Tool | Core call | CLI twin | Was |
|---|---|---|---|
| `search_code` | `semantic.search` (hybrid) | `ccctx search` | `search` |
| `get_symbol` | `graph.definitions` (new) | none | new |
| `find_callers` | `graph.callers` | `ccctx callers` | `callers` |
| `find_callees` | `graph.calls` | `ccctx calls` | `calls` |
| `impact_of` | `graph.impact` | `ccctx impact` | `impact` |
| `list_repositories` | `registry.list_repos` | `ccctx repo list` | unchanged |

`health`, `search`, `callers`, `calls` and `impact` are removed. The `repos` list parameter and `search`'s `mode` and `question` are removed: `repo` takes one repository name, and `search_code` is always hybrid.

Every tool carries `annotations.readOnlyHint: true`. Every parameter is declared as `Annotated[<type>, Field(description=...)]`, so its description appears in the input schema next to its default. Ranges are stated in the description and checked in the core, not declared as `minimum`/`maximum`.

## Common rules

- **Refusals are results.** For bad input, an unknown repository or language, a missing search model or an unreachable database, a tool returns its envelope with `status: "unavailable"`, a one-line `reason` with no password, empty `results`, and `isError: false`. The server keeps running.
- **Wrong argument type or an argument the tool does not take**: rejected by input validation before the tool runs, as an `isError: true` result whose text names the argument. Never a protocol error, never a crash. FastMCP ignores unknown arguments by default, so the server must reject them itself.
- **Database down** (or settings missing): `reason` is the driver's message without the password, for example `DPY-6005: cannot connect to database ...` (or the config error text). The next call after the database is back succeeds without a restart. The server does not connect at startup.
- **Names** follow the graph rules: case-sensitive; a bare name `x` matches `x` and `<anything>.x`; a qualified name matches only that definition. Line windows (`kind: "chunk"`) have no names and never match.
- **Bounded**: `search_code` at most `limit` (1 to 50), `get_symbol` at most 5 matches and 400 source lines each, graph tools at most 200 rows.
- **Located**: every returned item carries `repo`, `path` and a line (`line`, or `start_line` and `end_line`, 1-based inclusive).
- **Logging**: one stderr record per call, `{"event": "tool", "tool": "<name>", "ms": <int>, "status": "ok" | "unavailable" | "error", "results": <int | null>}`. Never the arguments, never source text.
- A registered but unindexed repository is empty, not an error: tools return `status: "ok"` with no results (or `no symbol named ...` for a name lookup).

Valid `language` values, in this order (the values the chunker assigns, sorted): `batch`, `css`, `go`, `html`, `ini`, `javascript`, `json`, `markdown`, `proto`, `python`, `rst`, `shell`, `sql`, `text`, `toml`, `yaml`.

## Descriptions

These are the exact tool descriptions. They follow research R4: the question answered, when to use it over its neighbors, what comes back, the next step.

**`search_code`**: Find code by what it does or by name: "how are requests routed?", "where are sessions saved?", "url_for". Use this first when you do not yet know which symbol to look at. If you already know the name, use get_symbol to read it, find_callers for its call sites, or impact_of for what a change would affect. Returns up to limit hits (default 10), best first. Each hit has the repository, path, symbol name, kind, language, line range, a snippet of the symbol's opening lines, and the scores behind its rank: the fused score, the keyword rank and the semantic rank (null when that side did not find it). Keyword and semantic search are fused, and the definitions of an exact identifier come first. Next step: call get_symbol with a hit's name to read its full source.

**`get_symbol`**: Read the full source of a named definition (function, method, class, type) when you know its name, for example from a search_code hit. Use this instead of search_code when the name is known, and instead of opening files: it returns the source exactly as it was indexed. A bare name returns every definition with that name, each labeled with its qualified name; pass a qualified name or a repo to narrow. Returns up to 5 matches, each with its qualified name, kind, repository, path, line range and source. A source longer than 400 lines is cut there and marked cut, and its full line range is still given. total is the number of matches and truncated is true when more than 5 matched. Unparsed files indexed as line windows have no names and are not found here; use search_code for them.

**`find_callers`**: Who calls this? Lists every call to the definitions matching name: the calling symbol, its kind, the repository, path and line of the call, and which definition is called. Use it before changing a function's signature or behavior, to see its direct call sites. For everything a change could reach through chains of calls, use impact_of; for what this symbol itself calls, use find_callees. Calls come from the parse tree, so comments, docstrings and strings never count. A call at module level has kind file and name (module). At most 200 rows; truncated is true when more exist. Next step: get_symbol on a caller to read it.

**`find_callees`**: What does this call? Lists the indexed symbols called from the body of each definition matching name, with the line of each call and where the called symbol is defined (repository, path, line range). Use it to follow what a function does one level down; for who calls it, use find_callers. Calls into code that is not indexed, such as the standard library or dependencies, are not listed. At most 200 rows; truncated is true when more exist. Next step: get_symbol on a callee to read it.

**`impact_of`**: What could break if I change this? Lists every symbol that reaches the definitions matching name through calls in at most depth hops, once each at its shortest distance (hops), nearest first, with the repository, path and line range. Use it to gauge the reach of a change; for just the direct call sites and their lines, use find_callers. At most 200 rows; truncated is true when more exist. Next step: get_symbol on the nearest symbols to see how they use it.

**`list_repositories`**: Which codebases can I ask about? Lists the registered repositories with their paths and how many files and symbols each holds. Use it to learn the valid repo values for the other tools, or after a repo was refused. A repository with 0 files is registered but not indexed yet.

### Parameter descriptions

| Tool | Parameter | Type, default | Description |
|---|---|---|---|
| `search_code` | `query` | `string`, required | A question in plain English (how are requests routed) or an identifier (url_for). Taken literally; there is no query syntax. |
| `search_code` | `repo` | `string \| null`, `null` | Search only this registered repository, for example flask. list_repositories gives the valid names. Default: all repositories. |
| `search_code` | `language` | `string \| null`, `null` | Search only files of this language: one of batch, css, go, html, ini, javascript, json, markdown, proto, python, rst, shell, sql, text, toml, yaml. Default: all languages. |
| `search_code` | `limit` | `int`, `10` | How many hits to return, 1 to 50. Default 10. |
| `get_symbol`, `find_callers`, `find_callees`, `impact_of` | `name` | `string`, required | A bare name (url_for), which matches url_for and every Class.url_for, or a qualified name (Flask.url_for), which matches only that definition. Case-sensitive. |
| `get_symbol`, `find_callers`, `find_callees`, `impact_of` | `repo` | `string \| null`, `null` | Look only in this registered repository, for example flask. list_repositories gives the valid names. Default: all repositories. |
| `impact_of` | `depth` | `int`, `3` | How many call hops to follow, 1 to 5. Default 3. 1 gives only the direct callers. |

Parameter order in the schema: `search_code(query, repo, language, limit)`, `get_symbol(name, repo)`, `find_callers(name, repo)`, `find_callees(name, repo)`, `impact_of(name, depth, repo)`, `list_repositories()`.

## `search_code`

Same hits, same order and same scores as `ccctx search "<query>" --repo <repo> --language <language> --limit <limit>` (hybrid mode).

```json
{
  "status": "ok",
  "reason": null,
  "results": [
    {"rank": 1, "score": 48.3, "keyword_rank": 1, "semantic_rank": 3, "similarity": 0.7271,
     "repo": "flask", "kind": "method", "name": "Flask.dispatch_request", "language": "python",
     "path": "src/flask/app.py", "start_line": 966, "end_line": 990,
     "snippet": "def dispatch_request(self, ctx: AppContext) -> ft.ResponseReturnValue:\n    \"\"\"Does the request dispatching. ..."}
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `status` | `"ok" \| "unavailable"` | |
| `reason` | `string \| null` | `null` when `ok`. |
| `results` | array, at most `limit` | Final rank order. Empty when nothing matches (still `ok`). |
| `rank` | `int` | 1-based. |
| `score` | `float` | Fused score (0 to 100), unrounded. |
| `keyword_rank`, `semantic_rank` | `int \| null` | `null` when that side did not find the hit. |
| `similarity` | `float \| null` | Cosine similarity (0 to 1), `null` when the semantic side did not find the hit. |
| `repo`, `kind`, `name`, `path` | `string` | `kind` is `chunk` for a line window. |
| `language` | `string` | The file's language, one of the valid `language` values. |
| `start_line`, `end_line` | `int` | 1-based, inclusive. |
| `snippet` | `string` | The opening lines of the hit's indexed source: at most 10 lines and at most 800 characters, no trailing newline. |

Scope: a hit is kept when both its repository and its language match. With a filter, the candidate pool is widened until `limit` in-scope hits are found or the pool is exhausted.

| Cause | `reason` |
|---|---|
| Empty or whitespace-only query | `the question is empty` |
| `limit` outside 1 to 50 | `limit must be between 1 and 50` |
| Unknown language | `unknown language '<language>'; valid languages: batch, css, go, html, ini, javascript, json, markdown, proto, python, rst, shell, sql, text, toml, yaml` |
| Unknown repository | `no repository named '<repo>'` |
| Model or hybrid index missing | `embedding model ALL_MINILM_L12_V2 is not set up; run `ccctx model load`` |
| Database down | the driver's message, e.g. `DPY-6005: cannot connect to database ...` |

The query, `limit` and `language` are checked before connecting, in that order.

## `get_symbol`

Core: `graph.definitions(conn, name, repos) -> tuple[list[Definition], int]`, the first 5 matches and the total. No model needed. Reads stored source only; never reads or runs the repository.

```json
{
  "status": "ok",
  "reason": null,
  "results": [
    {"name": "Flask.dispatch_request", "kind": "method", "repo": "flask",
     "path": "src/flask/app.py", "start_line": 966, "end_line": 990,
     "source": "def dispatch_request(self, ctx: AppContext) -> ft.ResponseReturnValue:\n...", "cut": false}
  ],
  "total": 1,
  "truncated": false
}
```

| Field | Type | Meaning |
|---|---|---|
| `status`, `reason` | as above | |
| `results` | array, at most `5` | Ordered by repository name, path, start line. |
| `name` | `string` | The qualified name of the definition. |
| `kind`, `repo`, `path` | `string` | Never `chunk`. |
| `start_line`, `end_line` | `int` | The full definition's range, even when `source` is cut. |
| `source` | `string` | The indexed source, at most its first 400 lines. |
| `cut` | `bool` | `true` when the source had more than 400 lines. |
| `total` | `int` | Number of matching definitions. `0` only when unavailable. |
| `truncated` | `bool` | `true` when `total` > 5. |

| Cause | `reason` |
|---|---|
| Empty or whitespace-only name | `the name is empty` |
| Unknown repository (checked first) | `no repository named '<repo>'` |
| No named definition matches | `no symbol named '<name>'` |
| Database down | the driver's message, e.g. `DPY-6005: cannot connect to database ...` |

Refusals return `results: []`, `total: 0`, `truncated: false`.

## `find_callers`, `find_callees`, `impact_of`

Same rows, same order as `ccctx callers <name> --repo <repo>`, `ccctx calls <name> --repo <repo>` and `ccctx impact <name> --depth <depth> --repo <repo>`. No model needed. Envelope, row fields and failures are those of `specs/007-code-graph/contracts/graph-tools.md`, unchanged apart from the tool names and the dropped `repos` parameter:

```json
{"status": "ok", "reason": null, "results": [ ... ], "truncated": false}
```

| Tool | Row fields |
|---|---|
| `find_callers` | `repo`, `kind`, `name`, `path`, `line`, `callee` |
| `find_callees` | `caller`, `line`, `repo`, `kind`, `name`, `path`, `start_line`, `end_line` |
| `impact_of` | `hops`, `repo`, `kind`, `name`, `path`, `start_line`, `end_line` |

`results` holds at most `200` rows; `truncated` is `true` when more existed.

| Cause | `reason` |
|---|---|
| Empty or whitespace-only name | `the name is empty` |
| `depth` outside 1 to 5 (`impact_of`) | `depth must be between 1 and 5` |
| Unknown repository | `no repository named '<repo>'` |
| No definition matches | `no symbol named '<name>'` |
| Database down | the driver's message, e.g. `DPY-6005: cannot connect to database ...` |

## `list_repositories`

Unchanged from `specs/002-repo-registry/contracts/list-repositories-tool.md` (no input; `database`, `reason`, `repositories[]` with `name`, `path`, `files`, `symbols`), apart from the description above and the read-only annotation.
