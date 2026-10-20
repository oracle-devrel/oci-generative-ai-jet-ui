# Contract: `ccctx feedback`, `ccctx eval`, and changes to `search` and `memory list`

Exit codes, the error format and refusing input before connecting follow `specs/002-repo-registry/contracts/cli.md`.
An unknown `--repo` exits 1 with `error: no repository named '<name>'`. Bad integers exit 2 (argparse). None of these
commands records a run or a use, except `feedback add`, which records the uses it is asked to.

## `ccctx feedback list --repo NAME`

One row per result with uses, highest weight first:

```text
KIND      NAME     PATH                            USES  WEIGHT  BOOST  LAST USED            INDEXED
function  url_for  src/flask/helpers.py               1    1.00   +4%  2026-10-12 14:02:11  yes
function  get_db   examples/tutorial/flaskr/db.py     1    0.50   +2%  2026-09-12 14:02:11  yes
```

- **WEIGHT**: two decimals.
- **BOOST**: a whole percent, `+0%` to `+20%`.
- **INDEXED**: `no` when the symbol or page is gone. Such a row boosts nothing.

No uses: `no feedback recorded for <name>`.

## `ccctx feedback add NAME --repo NAME [--path PATH] [--days-ago N] [--count C]`

Records C (default 1) cited uses of an indexed symbol or page, dated N (default 0) days ago, client `cli`. Each use
is its own session.

```text
recorded 1000 uses of url_for (src/flask/helpers.py) in flask, dated 0 days ago
```

- **Not found**: nothing named NAME at PATH (or anywhere, without `--path`) exits 1 with `error: not found: no
  indexed symbol or page named 'NAME' ...`.
- **Ambiguous**: NAME at several paths, without `--path`, exits 1 with `error: 'NAME' is at several paths; pass
  --path:` and one path per line.
- **Bad numbers**: a negative `--days-ago`, or a `--count` below 1 or above 100000, exits 2.

## `ccctx feedback reset (--repo NAME | --all)`

Exactly one of the two is required (argparse exits 2 otherwise).

```text
deleted 1003 uses in flask
```

`--all` prints `deleted N uses in all repositories`.

## `ccctx eval --gold FILE [--with-feedback] [--limit N]`

```text
Questions: 20
recall@10: 0.65 (13/20)
missed: how does gin bind a JSON request body?
...
```

- **Recall**: two decimals; `@` shows the limit (default 10, 1 to 50).
- **Feedback**: without `--with-feedback`, ranking ignores feedback.
- **Exit status**: 0 when every question ran, whatever the recall.
- **Errors** (exit 1):
  - `error: gold file not found: FILE`
  - `error: gold file is not valid JSON: <reason>`
  - `error: gold file: <what is wrong>`, for example `question 3 has no paths`
  - `error: no repository named '<name>'` (gold question N)

## `ccctx search` changes

- **`--no-feedback`**: ranks without feedback.
- **`FEEDBACK` column**: after `SCORE`, showing `+4%`, blank when 0. `SCORE` is the boosted score.

## `ccctx memory list` changes

`RESULTS` becomes `used/returned` on runs with at least one linked use, for example `2/10`; otherwise it shows the
count as before.
