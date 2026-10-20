# Contract: MCP tools `callers`, `calls`, `impact`

New tools beside `search` (`specs/005-hybrid-search/contracts/search-tool.md`). Adding tools is not a breaking change. Each tool calls the same core as the CLI (`graph.callers`, `graph.calls`, `graph.impact`), so for the same name, depth and repositories it returns the same rows in the same order as `ccctx callers`, `ccctx calls` and `ccctx impact` (SC-006). Name matching, call resolution and ordering are those of `contracts/cli.md`. Every call is logged through `_logged`. The embedding model is not required.

## Tools

| Tool | Description |
|---|---|
| `callers(name, repo=None, repos=None)` | List every call to the symbols matching `name`, with the calling symbol, repository, path and line. Calls come from the parse tree, so comments, docstrings and strings never appear. |
| `calls(name, repo=None, repos=None)` | List the indexed symbols called from the body of each definition matching `name`, with the line of each call and where the called symbol is defined. |
| `impact(name, depth=3, repo=None, repos=None)` | List every symbol that reaches `name` through calls in at most `depth` hops (1 to 5), once each at its shortest distance, nearest first. |

## Input

| Field | Type | Required | Meaning |
|---|---|---|---|
| `name` | `string` | yes | A bare name (`url_for`) or a qualified name (`Flask.url_for`). Case-sensitive. |
| `depth` | `int` | no, default `3` | `impact` only. From `1` to `5`. |
| `repos` | `string[] \| null` | no, default `null` | Restrict to these registered repositories. Duplicates are used once. `null` or empty means all. |
| `repo` | `string \| null` | no, default `null` | Merged into `repos`, as in `search`. |

## Output (structured content)

```json
{
  "status": "ok",
  "reason": null,
  "results": [ ... ],
  "truncated": false
}
```

| Field | Type | Meaning |
|---|---|---|
| `status` | `"ok" \| "unavailable"` | |
| `reason` | `string \| null` | `null` when `ok`. The cause when `unavailable`. |
| `results` | array, at most `200` | In the CLI's row order. Empty when nothing calls or is called (still `ok`). |
| `truncated` | `bool` | `true` when more than `200` results existed and only the first `200` are returned. |

The cap keeps every response bounded (constitution III). The CLI prints every row.

### `callers` results

```json
{"repo": "flask", "kind": "method", "name": "FlaskClient.open",
 "path": "src/flask/testing.py", "line": 205, "callee": "url_for"}
```

| Field | Type | Meaning |
|---|---|---|
| `repo`, `path` | `string` | Where the call is. |
| `kind` | `string` | The calling symbol's kind. `file` for a module-level call. |
| `name` | `string` | The qualified name of the calling symbol. `(module)` for a module-level call. |
| `line` | `int` | The 1-based line of the call. |
| `callee` | `string` | The qualified name of the definition called, for example `url_for` or `Flask.url_for`. |

### `calls` results

```json
{"caller": "url_for", "line": 236, "repo": "flask", "kind": "method",
 "name": "Flask.url_for", "path": "src/flask/app.py", "start_line": 1003, "end_line": 1121}
```

| Field | Type | Meaning |
|---|---|---|
| `caller` | `string` | The qualified name of the matched definition that makes the call. |
| `line` | `int` | The 1-based line of the call. |
| `repo`, `kind`, `name`, `path` | `string` | The called symbol. |
| `start_line`, `end_line` | `int` | Where the called symbol is defined, 1-based inclusive. |

### `impact` results

```json
{"hops": 1, "repo": "flask", "kind": "method", "name": "FlaskClient.open",
 "path": "src/flask/testing.py", "start_line": 180, "end_line": 230}
```

| Field | Type | Meaning |
|---|---|---|
| `hops` | `int` | The shortest number of call hops to a matched definition, from `1` to `depth`. |
| `repo`, `kind`, `name`, `path` | `string` | The affected symbol. |
| `start_line`, `end_line` | `int` | 1-based, inclusive. |

## Failures

Never raises, and `isError` is always `false`. Each refusal returns `status: "unavailable"`, `results: []`, `truncated: false` and a reason with no secret. Depth and the empty name are checked before connecting.

| Cause | `reason` |
|---|---|
| Empty or whitespace-only name | `the name is empty` |
| Depth outside 1 to 5 (`impact`) | `depth must be between 1 and 5` |
| Unknown repository (first, in given order) | `no repository named '<name>'` |
| No definition matches the name | `no symbol named '<name>'` |
| Database down | `database unreachable: <reason>` (or the config error text) |
