# Contract: MCP tool `search` (modes, repositories, ranks)

Extends `specs/004-semantic-search/contracts/search-tool.md`. Still implemented through `semantic.search`, the same call `ccctx search` uses, so for the same query, mode and repositories both return the same symbols, order and scores (SC-008). Inputs and output fields are only added, so existing calls keep working.

## Input

| Field | Type | Required | Meaning |
|---|---|---|---|
| `question` | `string` | yes | Identifier or plain-English question. Treated literally. |
| `mode` | `"vector" \| "text" \| "hybrid"` | no, default `"hybrid"` | Same as `ccctx search --mode`. |
| `repos` | `string[] \| null` | no, default `null` | Restrict to these registered repositories; duplicates searched once. `null` or empty means all. |
| `repo` | `string \| null` | no, default `null` | Kept from step 4. Merged into `repos`. |

## Output (structured content)

```json
{
  "status": "ok",
  "reason": null,
  "results": [
    {"rank": 1, "score": 48.3, "keyword_rank": 1, "semantic_rank": 3,
     "similarity": 0.7271, "repo": "flask", "kind": "function",
     "name": "url_for", "path": "src/flask/helpers.py",
     "start_line": 188, "end_line": 240}
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `status` | `"ok" \| "unavailable"` | |
| `reason` | `string \| null` | `null` when `ok`; the cause when `unavailable`. |
| `results` | array, at most `10` | Final rank order: definition matches first (`hybrid`, `text`), then fused order. Empty when nothing matches (still `ok`). |
| `results[].rank` | `int` | 1-based final rank. |
| `results[].score` | `float` | Fused score (0-100), unrounded. In `vector`/`text` mode, that side's score. |
| `results[].keyword_rank` | `int \| null` | `null` when the keyword side did not find it (the CLI's `-`). |
| `results[].semantic_rank` | `int \| null` | `null` when the semantic side did not find it. |
| `results[].similarity` | `float \| null` | Kept from step 4: the index's cosine similarity, `vector_score / 50 - 1`. `null` when the semantic side did not find it. In `vector` mode every value is `>= 0.3`. |
| `results[].repo`, `kind`, `name`, `path` | `string` | `kind` is `chunk` for fallback windows. |
| `results[].start_line`, `end_line` | `int` | 1-based, inclusive. |

## Failures

Never raises; `isError` is always `false`. Each becomes `status: "unavailable"`, `results: []`, with a reason and no secret:

| Cause | `reason` |
|---|---|
| Empty question | `the question is empty` |
| Unknown mode | `unknown mode '<mode>'; valid modes: vector, text, hybrid` |
| Unknown repository (first, in given order) | `no repository named '<name>'` |
| Model or hybrid index missing | `embedding model ALL_MINILM_L12_V2 is not set up; run `ccctx model load`` |
| Database down | `database unreachable: <reason>` (or the config error text) |
