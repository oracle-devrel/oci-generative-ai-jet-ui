# Contract: MCP tools (server 1.3.0)

Extends `specs/010-agent-memory/contracts/tools.md`. Every rule there still applies.
- **Every tool**: still recorded as a run.
- **`search_code`**: two new hit fields and one optional argument.
- **`get_symbol`, `read_wiki`**: answers unchanged; they may now record an opened use.
- **The other tools**: unchanged.

The server lists exactly nine tools. Everything is additive, so the version is `1.3.0` (MINOR, constitution III).

| Tool | Core call | CLI twin | Change |
|---|---|---|---|
| `mark_used` | `feedback.mark` | `ccctx feedback add` | new |
| `search_code` | `semantic.search(..., feedback=)` | `ccctx search [--no-feedback]` | `relevance`, `feedback` fields; `feedback` argument |
| `get_symbol` | unchanged | | records opened uses (research R8) |
| `read_wiki` | unchanged | | records an opened use for a page (research R8) |

## `mark_used`

**`mark_used`**: Tell the server a result helped: call this for each search hit you cite in your answer or rely on. Pass the hit's repo, path and name exactly as search_code returned them. Results that clients mark get a small, capped boost in later searches, and the boost fades over 30 days. Reading a hit with get_symbol or read_wiki already counts as a lighter use, so mark only what you actually used.

**Annotations**: `readOnlyHint: false`, `idempotentHint: true`, `destructiveHint: false`.

| Parameter | Type | Description |
|---|---|---|
| `repo` | string, required | The hit's repository, exactly as search_code returned it, for example flask. |
| `path` | string, required | The hit's path, exactly as search_code returned it (a page hit's directory). |
| `name` | string, required | The hit's name, exactly as search_code returned it, for example url_for or Flask.url_for. |

**Result**:

```json
{"status": "ok", "reason": null, "repo": "flask", "path": "src/flask/helpers.py", "name": "url_for",
 "kind": "function", "linked": true}
```

| Field | Meaning |
|---|---|
| `status` | `ok`, or `unavailable` with a reason |
| `reason` | null when `ok`. Otherwise: `no repository named 'x'`, `not found: no indexed symbol or page named 'n' at 'p' in 'r'`, or the database's reason |
| `kind` | the symbol's kind or `page`; null when not found |
| `linked` | whether a `search_code` in this session returned it. Its use is linked to that run |

- **Recording**: one cited use per result per session. A second call, or a call after an opened use, leaves one
  cited use (FR-005).
- **Failures**: recording is in the background. A recording failure never changes the answer (FR-008).
- **Facts**: a `fact` hit's identity resolves to the symbol it is about, at the same path and name, so marking a
  fact hit marks its code.

## `search_code`

**New argument**:

| Parameter | Type | Description |
|---|---|---|
| `feedback` | boolean, default `true` | Raise results that earlier sessions used, by at most 20 percent of their score. false ranks by relevance alone, exactly as with no feedback recorded. Default true. |

**Description**: two changes to the 010 text. The scores sentence, quoted after "Scores:", replaces the 008 one. The added sentence, quoted after "Added:", follows it.

Scores: "the scores behind its rank: the score, the relevance (the score before feedback), the feedback boost, the keyword rank and the semantic rank (null when that side did not find it)."

Added: "The feedback field is the boost from earlier sessions marking the result used: at most 0.2 (20 percent), fading over 30 days; relevance is the score before it."

**New hit fields**, on every hit:

```json
{"rank": 3, "score": 41.6, "relevance": 40.0, "feedback": 0.04, "similarity": 0.61, "keyword_rank": 3,
 "semantic_rank": 4, "repo": "flask", "kind": "function", "name": "get_db", ...}
```

| Field | Meaning |
|---|---|
| `relevance` | the score before feedback |
| `feedback` | the boost, 0 to the cap (default 0.2); 0 for facts and without uses |
| `score` | `relevance × (1 + feedback)`; the order hits are ranked by, after identifier definitions |

- **Ordering**: identifier definitions first, then the boosted fused order. Pages and facts are placed as before,
  with a page's similarity boosted by its own feedback.
- **Never adds**: feedback never adds a hit that the search did not find for the question (FR-011).
- **Opened uses**: the results are remembered for opened uses. With `feedback: false` they are still remembered:
  using a result is unrelated to how it was ranked.

## `get_symbol` and `read_wiki`: opened uses

After an `ok` answer, every returned symbol (`get_symbol`), or the returned page (`read_wiki` with `page`), that a
`search_code` in this session returned gets an opened use, linked to that search's run. Nothing else changes, and the
descriptions stay the same.

## Contract tests (`tests/test_server.py`)

- **Tool list**: exactly nine tools, with `mark_used`'s parameters and annotations.
- **`mark_used`**: a found result answers `ok` with `linked` true after a search, and false without one. A missing
  result answers `unavailable` with a reason containing `not found`, and records nothing. An unknown repository
  answers `unavailable`.
- **Dedupe**: search, then `get_symbol` on a hit, then `mark_used` on the same hit leaves one cited use linked to the
  search run.
- **No search, no use**: `get_symbol` without a prior search records no use.
- **Hit fields**: every hit has `relevance` and `feedback`. `feedback` is in [0, 0.2], and `score` equals `relevance
  × (1 + feedback)` within rounding. `feedback: false` gives `feedback` 0 on every hit and the same order as a
  database with no feedback.
