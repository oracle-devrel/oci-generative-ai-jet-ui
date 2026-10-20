# Contract: `ccctx search` (modes, repositories), `ccctx model load` (hybrid index)

Extends `specs/004-semantic-search/contracts/cli.md`. Exit codes (`0` ok, `1` refused, `2` database unreachable or starting), `error: <reason>` on stderr, the no-password rule and the migrate-first pre-step are unchanged.

## Settings

Read from `.env` and the environment. Not command-line flags. Documented in the README.

| Variable | Default | Meaning |
|---|---|---|
| `CCCTX_TEXT_WEIGHT` | `1` | Positive number. Keyword side's `score_weight` in the fusion. |
| `CCCTX_VECTOR_WEIGHT` | `1` | Positive number. Semantic side's `score_weight` in the fusion. |
| `CCCTX_SEARCH_CANDIDATES` | `100` | Positive integer. `return.topN` asked of `DBMS_HYBRID_VECTOR.SEARCH` before repository filtering, the definition boost and the cap of `10`. |

A non-positive or non-numeric value is refused at startup, exit `1`: `error: <VARIABLE> must be a positive number`.

## `ccctx model load` (changed)

As in step 4, then creates the hybrid index `ccctx_symbols_hybrid_ix` instead of `ccctx_symbols_embedding_ix` (see `schema.md`). Each part is skipped when already done. Output and refusals unchanged. Re-run once after upgrading to this step.

## `ccctx ingest <name>` (changed)

Output unchanged. The model check now also requires `ccctx_symbols_hybrid_ix`; when it is missing the command exits `1`, changing nothing, with the step 4 message:

```text
error: embedding model ALL_MINILM_L12_V2 is not set up; run `ccctx model load`
```

## `ccctx search "<query>" [--mode vector|text|hybrid] [--repo <name>[,<name>...]]...`

Examples (verbatim):

```text
ccctx search "url_for"
ccctx search "url_for" --mode vector
ccctx search "url_for" --mode text
ccctx search "url_for" --mode hybrid
ccctx search "middleware chain" --repo gin
ccctx search "how are incoming requests routed to handlers" --repo flask --repo gin
ccctx search "how are incoming requests routed to handlers" --repo flask,gin
```

### Options

| Option | Values | Default | Meaning |
|---|---|---|---|
| `--mode` | `vector`, `text`, `hybrid` | `hybrid` | `hybrid`: keyword and semantic sides fused by `DBMS_HYBRID_VECTOR.SEARCH` with `search_scorer` `RRF` and `search_fusion` `UNION`. `vector`: semantic side only, similarity floor `0.3`. `text`: keyword side only, every whole word of the query must appear (case-insensitive). |
| `--repo` | registered repository name | all repositories | Repeatable and comma-separated; the union is used, duplicates searched once. |

### Behaviour

- The query is literal: every word is sent to the keyword side wrapped in `{…}` (with `{`, `}`, `\` removed) and joined with ` AND `. Quotes, `-`, `&`, `|`, parentheses, `%` and `_` never act as operators and never cause an error.
- **Definition boost** (`hybrid` and `text` only): when the query is a single identifier (`^[A-Za-z_][\w.]*$`), symbols in scope whose name, or its last dotted part, equals it case-insensitively (not `chunk`) come first, in fused order when they were candidates and by path otherwise. All other results follow in fused order.
- A result found only by the semantic side is dropped when its similarity (`vector_score / 50 - 1`, the index's cosine similarity) is below `0.3`, in `vector` and `hybrid` mode. Keyword matches always count.
- Of a file's fallback windows (kind `chunk`), only the best-ranked one is shown.
- At most `10` results.

### Success, exit `0`, stdout

A `format_table` table, in final rank order:

```text
RANK  SCORE  KEYWORD  SEMANTIC  REPO   KIND      NAME           PATH               LINES
   1  48.30        1         3  flask  function  url_for        src/flask/helpers.py 188-240
   2  47.10        2         5  flask  method    Flask.url_for  src/flask/app.py     1003-1121
   3  31.20        4         -  flask  method    Flask.redirect src/flask/app.py     1123-1145
```

| Column | Value |
|---|---|
| `RANK` | 1-based final rank (after the definition boost). |
| `SCORE` | Fused score from `DBMS_HYBRID_VECTOR.SEARCH` (`score`, 0-100), two decimals. In `vector` and `text` mode, that side's score. |
| `KEYWORD` | Keyword rank (`text_rank` when `text_score > 0`), else `-`. Always `-` in `vector` mode. |
| `SEMANTIC` | Semantic rank (`vector_rank`), else `-`. Always `-` in `text` mode. |
| `REPO`, `KIND`, `NAME`, `PATH` | As in step 4. `KIND` includes `chunk`. |
| `LINES` | `start-end`, 1-based inclusive. |

Empty outcomes, exit `0`:

| Case | stdout |
|---|---|
| `vector` mode, nothing at or above the floor | `no symbols similar enough (similarity >= 0.30)` |
| `hybrid` or `text` mode, no match | `no matching symbols` |

### Refusals

All checked before any search runs; the database is never changed.

| Cause | Exit | stderr |
|---|---|---|
| Empty or whitespace-only query (checked before connecting) | `1` | `error: the question is empty` |
| `--mode` not one of the three (checked before connecting) | `1` | `error: unknown mode '<mode>'; valid modes: vector, text, hybrid` |
| A `--repo` name not registered (first unknown, in given order) | `1` | `error: no repository named '<name>'` |
| Model or hybrid index not set up | `1` | `error: embedding model ALL_MINILM_L12_V2 is not set up; run `ccctx model load`` |
| Database unreachable | `2` | `error: database unreachable: <reason>` (no password) |
