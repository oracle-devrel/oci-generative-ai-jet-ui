# Data Model: Usage Feedback

## Use (`ccctx_feedback`, migration 9)

| Column | Type | Rules |
|---|---|---|
| `id` | number, identity, primary key | |
| `repo_id` | number, not null | references `ccctx_repos (id)` on delete cascade |
| `path` | varchar2(1024 char), not null | the symbol's file path, or the page's directory |
| `name` | varchar2(1024 char), not null | the symbol's or page's name, as search hits show it |
| `kind` | varchar2(32), not null | the symbol's kind, or `page`. Never `fact` |
| `how` | varchar2(8), not null | `cited` or `opened` (check constraint) |
| `client` | varchar2(256) | the MCP client's name and version, or `cli` |
| `session_id` | varchar2(64), not null | the server process's UUID, or `cli:<uuid>` per hand-added use |
| `run_id` | number | references `ccctx_memory_runs (id)` on delete set null; the search that returned it |
| `used_at` | timestamp with time zone, not null | default `systimestamp`; at most now (a backdated use is earlier) |

- **Index**: `ccctx_feedback_result_ix` on `(repo_id, name)`.
- **One use per result per session** (FR-005): the writer `MERGE`s on `(session_id, repo_id, path, name)`. A cited use
  replaces an opened one (`how`, and `used_at` set to now). Repeated uses of either kind change nothing.
- **Base weight**: `cited` 1.0, `opened` 0.5.

## Result feedback (derived, never stored)

For one identity `(repo_id, path, name)`:

- **uses**: `count(*)`
- **weight**: `Σ base × power(0.5, age_days / half_life)`, where `age_days = cast(systimestamp as date) -
  cast(used_at as date)` (fractional days)
- **boost**: `cap × least(1, weight / 5)`
- **last use**: `max(used_at)`
- **indexed**: whether a symbol (`ccctx_symbols` joined to `ccctx_files`) or a page (`ccctx_wiki_pages` at
  `directory`) with that identity exists now

Settings: `cap` = `CCCTX_FEEDBACK_CAP` (default 0.20, 0 to 1); `half_life` = `CCCTX_FEEDBACK_HALF_LIFE_DAYS` (default
30, positive). Saturation weight: 5, a constant.

## Search result additions (`semantic.Result`, `server.SearchHit`)

| Field | Meaning |
|---|---|
| `score` | the score the hit was ranked by: `relevance × (1 + feedback)` |
| `relevance` | the fused (or one-sided) score before feedback |
| `feedback` | the boost, 0 to `cap`; 0 for facts, for results without uses, and when feedback is off |

## Returned-results map (in memory, server process)

`(repo, path, name) → run dict` of the latest `search_code` that returned it in this process. It has no TTL. The run
dict's `id` is filled in by the writer once the run is stored.

## Run additions (`memory.RunView`)

| Field | Meaning |
|---|---|
| `used` | names of this run's results that have a use linked to the run, in result order |

## Gold set (`gold.json`)

```json
{"version": 1,
 "questions": [{"question": "how are URL rules matched to view functions?", "repo": "flask",
                "paths": ["src/flask/app.py", "src/flask/sansio/app.py"]}]}
```

- `version`: an integer. Bump it when questions or paths change.
- `questions`: a non-empty list.
- Each question: a non-empty `question`, an optional `repo` (it must be registered), and `paths` (a non-empty list of
  repository-relative files or directories).

## Evaluation result

`questions` (N), `hits` (n), `recall` = n/N to two decimals, and the questions missed, in file order.

## State

A use has no states. Its influence falls continuously with age, and it ends only by `ccctx feedback reset` or by
removal of its repository.
