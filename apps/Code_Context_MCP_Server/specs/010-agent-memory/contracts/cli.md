# Contract: `ccctx memory` and the ingest summary

Exit codes, the error format and refusing input before connecting follow `specs/002-repo-registry/contracts/cli.md`.
An unknown `--repo` exits 1 with `error: no repository named '<name>'`. A `--limit` that is not a positive integer
exits 2 (argparse), like `ccctx symbols`.

## `ccctx memory list [--repo NAME] [--limit N]`

The newest runs first, default limit 20. With `--repo`, only runs belonging to that repository (research R4).

```text
RUN  WHEN                 TOOL          QUESTION                 CLIENT                 STATUS  RESULTS  TOP
 42  2026-10-12 10:14:03  find_callers  url_for                  claude-code 2.1.4      ok           12  redirect_to_login src/flask/app.py:88
 41  2026-10-12 10:13:58  get_symbol    url_for                  claude-code 2.1.4      ok            2  url_for src/flask/helpers.py:188-246
 40  2026-10-12 10:13:51  search_code   where is url_for defined claude-code 2.1.4      ok           10  url_for src/flask/helpers.py:188-246
```

- **QUESTION**: the run's question, or `-` when it has none.
- **CLIENT**: the client's name and version, or `-`.
- **STATUS**: `ok`, `unavailable` or `error`. When it isn't `ok`, TOP shows the reason.
- **TOP**: the first result's name and location (`path:start-end`, `path:line` for a call, `path` for a page), or `-`.

No runs: `no runs recorded`.

## `ccctx memory consolidate [--repo NAME]`

Without `--repo`, every repository that has runs or facts. One line per repository:

```text
flask: 20 runs read, 4 created, 15 merged, 1 weakened, 0 stale, 1 re-asked in 0.4s (template/1)
```

- **merged**: a finding added to an existing fact.
- **weakened**: a fact a contradiction lowered.
- **stale**: facts marked stale by the re-check.
- **re-asked**: facts whose code changed and were asked again (research R8).
- **The distiller**: in parentheses. With a model configured, `(llm:anthropic/claude-sonnet-5-5: 4, template/1: 1)`
  counts the facts each distiller wrote, so a fallback is visible.

Running it again with nothing new prints
`flask: 0 runs read, 0 created, 0 merged, 0 weakened, 0 stale, 0 re-asked in 0.0s (template/1)`.

## `ccctx memory facts [--repo NAME] [--limit N]`

Fresh first, then by confidence, then the most recently updated. Default limit 20.

```text
FACT      REPO   SUBJECT              CONFIDENCE  STATE  DISTILLER   RUNS         TEXT
3f9a1c2e  flask  url_for              0.938       fresh  template/1  40,41,42,44  `url_for` is a function in `src/flask/helpers.py`. It is called by 12 symbols, including …
a07b55d1  flask  flask/json           0.500       fresh  template/1  45           `flask/json` is the wiki page for `src/flask/json`: …
c1e0d9f4  flask  Flask.make_response  0.750       stale  template/1  31,33        … (stale: `Flask.make_response` was removed)
```

- **FACT**: the first 8 characters of the package record ID.
- **DISTILLER**: `template/1` or `llm:<model>`.
- **RUNS**: the fact's run IDs, oldest first. Every one appears in `ccctx memory list`.
- **TEXT**: cut at 120 characters. A stale fact ends with its reason.

No facts: `no facts`.

## `ccctx search`: fact rows

`ccctx search` calls the same `semantic.search` as `search_code`, so fact hits appear in its table with KIND
`fact`, KEYWORD `-`, the subject as NAME, and the subject's PATH and LINES. Nothing else in its output changes.

## `ccctx ingest NAME`: new summary line

After the wiki lines, when consolidation read a run or changed a fact:

```text
Memory    3 runs read, 1 created, 2 merged, 0 weakened, 1 stale, 2 re-asked
```

When consolidation fails, the ingestion still exits 0. The summary prints
`Memory    not consolidated: <reason>` and stderr gets `warning: memory not consolidated: <reason>`.
