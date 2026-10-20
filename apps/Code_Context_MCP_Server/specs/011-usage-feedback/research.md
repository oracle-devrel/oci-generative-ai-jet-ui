# Research: Usage Feedback

All decisions below resolve the plan's open points. No NEEDS CLARIFICATION remains.

## R1. Storing uses

- **Decision**: one table, `ccctx_feedback`, one row per use. Each row holds:
  - **Identity**: the result's `repo_id`, `path` and `name` (a page's path is its directory), plus its `kind` for
    display.
  - **The use**: how it was used (`cited`, `opened`), the client, the session, the run that returned it (nullable)
    and `used_at`.
  - **Dedupe**: one use per result per session (FR-005) is kept by the writer's `MERGE` on `(session, repo_id,
    path, name)`, not by a unique constraint: path and name are each up to 1024 characters, which is past Oracle's
    index key limit. One writer thread does every MCP write, so the `MERGE` cannot race itself. An index on
    `(repo_id, name)` serves the merge and the search lookup.
- **Rationale**: symbols are deleted and re-inserted on re-ingest, with new IDs, so a foreign key to a symbol would
  lose feedback on every ingest. The identity survives as long as the code stays where it is. A moved symbol starts
  fresh, as the spec says.
- **Alternatives**: a counter per result (rejected: decay needs each use's age, and the spec says the aggregate is
  never a running total); feedback inside the run's JSON (rejected: the CLI's backdated and hand-added uses have no
  run, and decay would need JSON queries over all runs).

## R2. Sessions and returned results

- **Decision**: the server is stdio-only (`mcp.run("stdio")`), so one process is one session. `server.SESSION` is a
  UUID made at start. `search_code` keeps a dict from `(repo, path, name)` to the run dict that returned it,
  overwritten by later searches, so a use links to the latest search. A use for something that is not in the dict:
  - `get_symbol` and `read_wiki` record nothing (FR-003).
  - `mark_used` records the cited use with no run link.
- **Rationale**: no protocol-level session ID is needed, and nothing is persisted that the process cannot answer
  for.
- **Ceiling**: the dict grows by at most 50 entries per search, for the process's life. `# ponytail:` comment; key it
  by `ctx.session` if a multi-session transport is ever added.

## R3. Writing uses

- **Decision**: uses go into the same queue as runs (`memory.record`), as a dict tagged `"use"`. The single writer
  thread writes items in order.
  - **Run link**: `store_runs` stores each new ID back on its run dict. A use queued after its run reads `run["id"]`
    at write time; if the run was dropped (write failure, test isolation), the use is written unlinked.
  - **Dedupe**: a `MERGE` on the session key inserts the use, or upgrades an opened use to cited.
- **Rationale**: no second thread or connection; ordering comes for free; failure handling (logged, never reaches
  the client) is shared (FR-008).
- **CLI**: `ccctx feedback add` writes synchronously with its own session per use (`cli:<uuid>`), so `--count 1000`
  makes 1000 uses.

## R4. Weight and boost

- **Decision**:
  - **Weight**: `weight = Σ base × 0.5^(age_days / half_life)`, with base 1.0 for cited and 0.5 for opened, computed
    in SQL from `used_at` at read time.
  - **Boost**: `boost = cap × min(1, weight / 5)`.
  - **Defaults**: cap 0.20 (`CCCTX_FEEDBACK_CAP`, 0 to 1, where 0 switches feedback off) and half-life 30 days
    (`CCCTX_FEEDBACK_HALF_LIFE_DAYS`, positive). The saturation weight 5 is a documented constant.
- **Rationale**:
  - **Linear, then capped**: halving a weight below saturation halves its boost, which makes the decay test read
    plainly. One fresh citation gives 4%, five give the full 20%, and a thousand still give 20%.
  - **Computed at read time**: decay needs no background job and backdating needs no special case.
- **Alternatives**: a saturating curve `w / (w + 1)` (rejected: halving the weight doesn't halve the boost, and one
  use already gives half the cap); `log(1 + uses)` (rejected: unbounded without a clamp).

## R5. Applying the boost

- **Decision**: in `semantic.search`, after `_fuse`, one query reads the weights of the candidates' identities.
  - **Symbols**: each candidate's score becomes `score × (1 + boost)`, and the fused list is stably re-sorted by it.
  - **Definitions**: the definitions list (`first`) is built and sorted the same way, but still goes ahead of
    everything else (FR-012).
  - **Pages**: a page's similarity is multiplied by `1 + boost` (at most 1.0) before `_place`.
  - **Facts**: never boosted.
  - **Switch**: `search(..., feedback=True)`. With `False`, or a cap of 0, the query is skipped and the order is
    exactly the old one.
- **Rationale**: only candidates the index already returned for the question are touched, so nothing is added
  (FR-011).
  - **"database connection pooling"**: in flask, scores fall from 96 to 15 across the top 13, and the hundredth
    candidate is far lower. A symbol outside the top ~13 cannot reach the top 10 with ×1.2.
  - **Gold questions**: SC-003's bound (a score of at least 1/1.2 of the tenth hit's) is exactly what ×1.2 allows.
- **Alternatives**: an additive feedback component in RRF (rejected: RRF scores are rank-based, so a fixed addition
  means different things at different depths, and "20 percent" would not be literal); boosting before fusion
  (rejected: it changes which candidates come back).

## R6. Explaining the score

- **Decision**: `Result` and `SearchHit` gain `relevance` (the score before feedback; equal to `score` when the
  boost is 0) and `feedback` (the boost as a fraction, 0 to the cap). `ccctx search` shows a `FEEDBACK` column such
  as `+4%`, blank at 0.
- **Rationale**: constitution IV asks for the component scores. Showing the fraction makes the cap visible in every
  hit (SC-004).

## R7. `mark_used`

- **Decision**: `mark_used(repo, path, name)` resolves an indexed symbol at that path and name, or else a wiki page
  at that directory and name, and records a cited use.
  - **Answer**: `{status, reason, repo, path, name, kind, linked}`, where `linked` says whether a search in this
    session returned it.
  - **Unknown repository, or nothing indexed there**: `status: "unavailable"` with a reason that says "not found",
    and nothing is recorded (FR-006). This matches the other tools' envelope.
  - **Annotations**: not read-only, idempotent.
  - **Memory**: the call is logged as a run like every tool, and added to `memory.NO_FACTS`, so it distils nothing.
- **Rationale**: the client already has all three values from the hit it cites. A rowid or hit token would not
  survive across sessions.

## R8. Opened uses

- **Decision**: after `get_symbol` answers `ok`, each returned symbol whose `(repo, path, name)` is in the session's
  returned-results map gets an opened use. After `read_wiki` answers `ok` with a page, the same goes for the page's
  `(repo, directory, name)`. Listing the wiki's pages (no page asked) records nothing.
- **Rationale**: reading the source or the page of a hit is what "opening" means for this server. Graph tools
  (`find_callers` and the others) are navigation, not use, and are left out.

## R9. `ccctx feedback`

- **Decision**:
  - **`list --repo R`**: one row per result. Columns: kind, name, path, uses, weight (two decimals), boost
    (percent), last use, indexed (yes/no). Highest weight first.
  - **`add NAME --repo R [--path P] [--days-ago N] [--count C]`**: resolves like `mark_used`. Without `--path`, the
    name must be unique in the repository, or the command lists the candidates and fails. It records C cited uses
    dated N days ago, attributed to client `cli`. A negative N is refused.
  - **`reset --repo R | --all`**: deletes the uses and prints the count.
- **Rationale**: `add` gives the brief's hammer and backdating tests a direct handle, without SQL.

## R10. `ccctx eval`

- **Decision**:
  - **Gold file**: `gold.json` at the repository root, `{"version": 1, "questions": [{"question", "repo", "paths":
    [...]}]}`. `repo` is optional and scopes the search.
  - **Run**: `ccctx eval --gold FILE [--with-feedback] [--limit 10]` calls `semantic.search(..., feedback=<flag>,
    limit=10)` per question.
  - **Hit rule**: a question is a hit when any result's path equals an expected path, or lies under an expected
    directory.
  - **Output**: `Questions: N`, then `recall@10: 0.65 (13/20)`, then `missed: <question>` per miss.
  - **Errors**: a missing file, invalid JSON, a wrong shape or an unregistered repository stops the run with a
    message and exit status 1.
- **Rationale**: going straight to `semantic.search`, not through the server, means no run and no use is recorded
  (FR-021). The existing `test_eval.py` identifier set stays as it is.
- **Gold set**: 20 plain-language questions, about 12 over flask and 8 over gin, written against the indexed code
  (routing, sessions, blueprints, config, templates, JSON, context, middleware, binding, rendering). The measured
  baseline is recorded in quickstart.md and asserted as a floor in `test_eval.py`.

## R11. Removed code and repositories

- **Decision**: feedback references code by identity, so nothing cascades on re-ingest. `list` marks rows whose
  symbol or page no longer exists as not indexed. Search only boosts candidates, which are always indexed, so stale
  feedback boosts nothing (FR-024). The repository foreign key cascades, so removing a repository removes its
  feedback.

## R12. Showing use in past tool calls

- **Decision**: `memory.runs` counts each run's linked uses (`ccctx_feedback.run_id`), and `RunView` gains `used`
  (the names used). `ccctx memory list` shows `used 2/10` on search runs (FR-007, SC-001). `recall`'s run summaries
  are unchanged.
