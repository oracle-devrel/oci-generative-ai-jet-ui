# Quickstart: Usage Feedback

Validates the feature end to end against the local database, with flask and gin registered and ingested and the
embedding model loaded.

## Setup

```powershell
uv sync
uv run ccctx db migrate              # applies migration 9 (usage feedback)
uv run ccctx feedback reset --all    # start from no feedback
```

## 1. Baseline (User Story 4)

```powershell
uv run ccctx eval --gold gold.json
```

Expect `Questions: 20`, then `recall@10: <r> (<n>/20)`, then one `missed:` line per miss. They are the floor that
`tests/test_eval.py` asserts (`BASELINE_HITS`).

Measured 2026-10-13 for gold.json version 1, with no feedback recorded:

```text
Questions: 20
recall@10: 0.90 (18/20)
missed: how do tests send requests to the app without running a server?
missed: how is HTTP basic authentication checked?
```

Both misses are ranking misses, not wrong gold paths: docs and test files (`docs/testing.rst`, `auth_test.go`) outrank
`src/flask/testing.py` and `auth.go`.

## 2. Recording use (User Story 1)

In an MCP client (MCP Inspector CLI, or `claude -p`):
1. `search_code` "how are sessions saved?", repository flask.
2. `get_symbol` on the second hit.
3. `mark_used` with the first hit's repo, path and name.

Then:

```powershell
uv run ccctx memory list --repo flask --limit 3    # the search shows RESULTS 2/10
uv run ccctx feedback list --repo flask            # first hit: weight 1.00, +4%; second: 0.50, +2%
```

`mark_used` with a made-up name answers `unavailable` with "not found", and the list doesn't change.

## 3. With feedback (User Story 2, SC-002)

For at least 5 gold questions, mark their expected results as used: in client sessions, as in step 2, or with
`ccctx feedback add <name> --repo <repo> --path <path> --count 3`. Then:

```powershell
uv run ccctx eval --gold gold.json --with-feedback   # recall >= the baseline
uv run ccctx eval --gold gold.json                   # still exactly the baseline
```

## 4. The cap (SC-003, SC-004)

```powershell
uv run ccctx feedback add url_for --repo flask --path src/flask/helpers.py --count 1000
uv run ccctx feedback list --repo flask                  # url_for: weight 1000.00, +20%
uv run ccctx search "database connection pooling"        # url_for is not listed; no FEEDBACK above +20%
uv run ccctx search "url_for"                            # definitions first, as before
```

## 5. Decay (User Story 3, SC-005)

```powershell
uv run ccctx feedback reset --repo flask
uv run ccctx feedback add url_for  --repo flask --path src/flask/helpers.py
uv run ccctx feedback add redirect --repo flask --path src/flask/helpers.py --days-ago 30
uv run ccctx feedback add abort    --repo flask --path src/flask/helpers.py --days-ago 60
uv run ccctx feedback list --repo flask
```

Expect weights 1.00, 0.50 and 0.25, and boosts +4%, +2% and +1%.

## 6. Reset (SC-008)

```powershell
uv run ccctx feedback reset --repo flask             # deleted N uses in flask
uv run ccctx feedback list --repo flask              # no feedback recorded for flask
```

Search order equals `ccctx search ... --no-feedback`.

## 7. Regression

```powershell
uv run pytest
```

The full suite passes, including `test_eval.py` (identifier top-1 still 10/10, SC-006). Search latency with feedback
is within 10% of `--no-feedback` (SC-007): `test_feedback.py` times both.

## Verified 2026-10-13

Against the local database, with flask and gin ingested, server 1.3.0.

**1. Baseline.** `Questions: 20`, `recall@10: 0.90 (18/20)`, missing the testing-client and basic-auth questions
(see step 1).

**2. Recording**, through one stdio MCP session against `ccctx mcp` (a Python `mcp` client: search, `get_symbol` on
the second symbol hit, `mark_used` on hit 1, then `mark_used` on a made-up name):

```text
  RUN  WHEN                 TOOL         QUESTION                      CLIENT     STATUS       RESULTS  TOP
24412  2026-10-13 08:18:47  mark_used    made_up_name                  mcp 0.1.0  unavailable        0  not found: no indexed symbol or page named 'made_up_name' at 'docs/api.rst' in 'flask'
24411  2026-10-13 08:18:47  mark_used    api.rst:51-110                mcp 0.1.0  ok                 0  -
24410  2026-10-13 08:18:47  get_symbol   SecureCookieSessionInterface  mcp 0.1.0  ok                 1  SecureCookieSessionInterface src/flask/sessions.py:284-385
24409  2026-10-13 08:18:47  search_code  how are sessions saved?       mcp 0.1.0  ok              2/10  api.rst:51-110 docs/api.rst:51-110

KIND   NAME                          PATH                   USES  WEIGHT  BOOST  LAST USED            INDEXED
chunk  api.rst:51-110                docs/api.rst              1    1.00    +4%  2026-10-13 08:18:47  yes
class  SecureCookieSessionInterface  src/flask/sessions.py     1    0.50    +2%  2026-10-13 08:18:47  yes
```

`mark_used` answered `"linked": true`; the made-up name added nothing.

**3. With feedback.** Three uses each on the expected results of 7 questions (`FlaskClient`, `BasicAuth`,
`Config.from_pyfile`, `node.getValue`, `LoggerWithConfig`, `CustomRecoveryWithWriter`, `send_from_directory`):
`--with-feedback` gives `0.90 (18/20)`, and without it still `0.90 (18/20)`. Recall held. The two misses stay missed:
their expected symbols are not among those questions' top candidates, and the boost (+12% at three uses) never adds a
result.

**4. The cap.** After `feedback add url_for ... --count 1000`, `feedback list` shows `1000  1000.00  +20%`. `ccctx
search "database connection pooling"` lists docs chunks and `get_db`, not `url_for`, and no FEEDBACK value. `ccctx
search "url_for"` still puts both definitions first: `url_for` (+20%, 26.18) then `Flask.url_for` (24.38).

**5. Decay.** `url_for` now, `redirect` 30 days back, `abort` 60 days back:

```text
KIND      NAME      PATH                  USES  WEIGHT  BOOST  LAST USED            INDEXED
function  url_for   src/flask/helpers.py     1    1.00    +4%  2026-10-13 08:20:01  yes
function  redirect  src/flask/helpers.py     1    0.50    +2%  2026-09-13 08:20:02  yes
function  abort     src/flask/helpers.py     1    0.25    +1%  2026-08-14 08:20:03  yes
```

**6. Reset.** `deleted 3 uses in flask`, then `no feedback recorded for flask`, and `ccctx search "how are sessions
saved?" --repo flask` printed exactly what `--no-feedback` printed.

**Found on the way.**
- **The stdio server hung on its first fact search or `recall`**, a bug from 010. On Windows, loading numpy's
  extension module (under the AI Agent Memory package) while the stdio reader thread was blocked on stdin hung the
  process. `server.main` now loads the package before serving. `test_mcp_child_process_serves_the_tools_from_any_directory`
  calls `recall` over stdio and fails without the fix.
- **`ORA-03050`**: `SESSION` is a reserved word, so the column is `session_id`.
- **Leaked test feedback**: a timing test's flask reads became uses, through results that earlier tests' searches had
  returned. The `recorded` fixture now starts each test with no returned results.

**7. Regression.** `uv run pytest`: 567 passed in 8 minutes, including the gold floor, SC-002, SC-003, the identifier
top-1 10/10 (SC-006) and the latency check (SC-007). `uvx ruff@0.14.0 check src tests --exclude tests/fixtures`: all
checks passed. The suite left no uses in flask. Finished with `ccctx feedback reset --all`.
