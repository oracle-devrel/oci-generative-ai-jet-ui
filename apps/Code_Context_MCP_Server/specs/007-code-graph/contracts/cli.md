# Contract: `ccctx callers`, `ccctx calls`, `ccctx impact`

Extends `specs/005-hybrid-search/contracts/cli.md`. Exit codes (`0` ok, `1` refused, `2` database unreachable or starting), `error: <reason>` on stderr, the no-password rule and the migrate-first pre-step are unchanged. All three commands call the same core as the MCP tools: `graph.callers`, `graph.calls` and `graph.impact`. They do not need the embedding model, so they work before `ccctx model load`.

Examples (verbatim):

```text
ccctx callers url_for
ccctx calls url_for
ccctx impact url_for --depth 3
ccctx impact url_for --depth 1
ccctx callers Flask.url_for
ccctx callers url_for --repo flask
```

## Shared rules

### Name matching

- Matching is case-sensitive.
- A qualified name (`Flask.url_for`) matches exactly that definition.
- A bare name (`url_for`) matches every function, method, class, type or interface whose name is `url_for` or ends in `.url_for`.
- Chunks (kind `chunk`) never match.
- The name is matched within the selected repositories.

### Options

| Option | Values | Default | Meaning |
|---|---|---|---|
| `--repo` | registered repository name | all repositories | Repeatable and comma-separated, as in `ccctx search`. The union is used, duplicates once. |
| `--depth` | integer `1` to `5` | `3` | `impact` only. The maximum number of call hops followed. |

### Refusals

The database is never changed.

| Cause | Exit | stderr |
|---|---|---|
| Empty or whitespace-only name (checked before connecting) | `1` | `error: the name is empty` |
| `--depth` not an integer from 1 to 5 (`impact`, checked before connecting) | `1` | `error: depth must be between 1 and 5` |
| A `--repo` name not registered (first unknown, in given order) | `1` | `error: no repository named '<name>'` |
| No definition matches the name | `1` | `error: no symbol named '<name>'` |
| Database unreachable | `2` | `error: database unreachable: <reason>` (no password) |
| Database still starting | `2` | `error: database is still starting` |

A bad `--depth` exits `1`, not argparse's `2`.

### Tables

Every success prints a `format_table` table: two-space separated columns, uppercase headers, numeric columns right-aligned. Each table has exactly one header line, so `| wc -l` minus one is the row count.

## `ccctx callers <name> [--repo <name>[,<name>...]]...`

Lists every call to any definition matching the name, sorted by repository, path, then line.

```text
CALLER             KIND      REPO   PATH                              LINE  CALLS
(module)           file      flask  examples/tutorial/flaskr/auth.py    12  url_for
FlaskClient.open   method    flask  src/flask/testing.py               205  url_for
redirect_to_index  function  flask  tests/test_helpers.py               88  Flask.url_for
```

| Column | Value |
|---|---|
| `CALLER` | The qualified name of the calling symbol. `(module)` for a call outside every function and class. |
| `KIND` | The calling symbol's kind. `file` for a module-level call. |
| `REPO`, `PATH` | Where the call is. |
| `LINE` | The 1-based line of the call. Right-aligned. |
| `CALLS` | The qualified name of the definition called, for example `url_for` or `Flask.url_for`. |

Empty outcome, exit `0`: `no callers of '<name>'`.

## `ccctx calls <name> [--repo <name>[,<name>...]]...`

Lists every indexed symbol called from the body of a definition matching the name, sorted by `FROM`, then `LINE`. Calls into code that is not indexed (standard library, third-party code) are not listed.

```text
FROM     LINE  CALLEE                 KIND      REPO   PATH                  LINES
url_for   219  _split_blueprint_path  function  flask  src/flask/helpers.py  172-186
url_for   236  Flask.url_for          method    flask  src/flask/app.py      1003-1121
```

| Column | Value |
|---|---|
| `FROM` | The qualified name of the matched definition that makes the call. |
| `LINE` | The 1-based line of the call. Right-aligned. |
| `CALLEE` | The qualified name of the called symbol. |
| `KIND`, `REPO`, `PATH` | The called symbol's kind, repository and file. |
| `LINES` | Where the called symbol is defined, `start-end`, 1-based inclusive. |

Empty outcome, exit `0`: `'<name>' calls no indexed symbols`.

## `ccctx impact <name> [--depth N] [--repo <name>[,<name>...]]...`

Follows calls backwards from every definition matching the name: its callers, their callers, and so on, up to `--depth` hops. A direct caller is 1 hop. Each affected symbol is listed once, at its shortest distance. Recursion and cycles always finish, because the number of hops is bounded.

```text
HOPS  NAME              KIND      REPO   PATH                  LINES
   1  FlaskClient.open  method    flask  src/flask/testing.py  180-230
   2  FlaskClient.get   method    flask  src/flask/testing.py  240-250
   3  test_redirect     function  flask  tests/test_basic.py   410-425
```

| Column | Value |
|---|---|
| `HOPS` | The shortest number of call hops to a matched definition, from `1` to `--depth`. Right-aligned. |
| `NAME`, `KIND`, `REPO`, `PATH` | The affected symbol. |
| `LINES` | `start-end`, 1-based inclusive. |

Rows are sorted by hops, repository, path, then start line. Only symbols are listed. Module-level callers (`(module)` in `callers`) are not, because a file has no callers to continue through.

Empty outcome, exit `0`: `nothing calls '<name>'`.

Comparing depths (verbatim):

```text
ccctx impact url_for --depth 1 | wc -l
ccctx impact url_for --depth 3 | wc -l
```

The depth 3 count is larger. Every symbol at depth 1 also appears in depth 3 with `HOPS` `1`. The depth 1 rows are the symbol rows of `ccctx callers url_for`, without its `(module)` rows.

## How calls are found

- Ingest finds calls in the parse tree of each Python, Go and JavaScript file. Comments, docstrings, string literals, documentation files and templates never produce a call.
- Files that fall back to line windows contribute no calls.
- A call inside a method belongs to the method. A call in a class body outside every method belongs to the class. A call outside every symbol belongs to the file.
- Each call is resolved by name within its own repository. Calls never cross repositories.
  1. A bare call `x(...)` matches functions and classes named `x`, plus types in Go.
  2. An attribute call on a module or package the file imports (`flask.url_for(...)`, `gin.New(...)`) is treated as a bare call.
  3. An attribute call on `self`, `cls` or `this` matches methods named `*.x`, preferring the enclosing class.
  4. Any other attribute call matches methods named `*.x`.
- Among the matches, definitions in the same file win. Failing that, those in a file the caller's file imports. Failing that, every match in the repository.
- A call with no match is dropped. Nothing is invented for it.
