# Contract: MCP tool `search`

Added beside `health` and `list_repositories`. Implemented through `semantic.search`, the same call `ccctx search` uses, so for one question both return the same symbols, order and scores (SC-008).

## Input

| Field | Type | Required | Meaning |
|---|---|---|---|
| `question` | `string` | yes | Plain-English question. |
| `repo` | `string \| null` | no, default `null` | Restrict to one registered repository. |

## Output (structured content)

```json
{
  "status": "ok",
  "reason": null,
  "results": [
    {"rank": 1, "similarity": 0.6123, "repo": "flask", "kind": "method",
     "name": "Flask.dispatch_request", "path": "src/flask/app.py",
     "start_line": 870, "end_line": 895}
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `status` | `"ok" \| "unavailable"` | |
| `reason` | `string \| null` | `null` when `ok`; the cause when `unavailable`. |
| `results` | array, at most `10` | Ordered by `similarity` descending; every `similarity >= 0.3`. Empty when nothing reaches the floor (still `ok`). |
| `results[].rank` | `int` | 1-based. |
| `results[].similarity` | `float` | `1 - cosine distance`, unrounded. |
| `results[].repo`, `kind`, `name`, `path` | `string` | `kind` is `chunk` for fallback windows. |
| `results[].start_line`, `end_line` | `int` | 1-based, inclusive. |

## Failures

Never raises; `isError` is always `false`. Each becomes `status: "unavailable"`, `results: []`, with a reason and no secret:

| Cause | `reason` |
|---|---|
| Empty question | `question must not be empty` |
| Unknown repo | `no repository named '<name>'` |
| Model missing | `embedding model ALL_MINILM_L12_V2 is not set up; run `ccctx model load`` |
| Database down | `database unreachable: <reason>` (or the config error text) |
