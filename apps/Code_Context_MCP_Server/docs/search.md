# Search

## Searching code

Search combines keyword matching and semantic matching, both served by one hybrid vector index in the database. The database embeds code itself with Oracle's prebuilt ONNX `all_MiniLM_L12_v2` model, loaded as `ALL_MINILM_L12_V2`. There is no API key and no network call at search time, and source code never leaves the database to be embedded.

**1. Set up the model and the index once.** This step:

- downloads the 133 MB model file into `.cache/models/` (git-ignored)
- loads it with `DBMS_VECTOR.LOAD_ONNX_MODEL` and records its name and dimension
- builds the hybrid vector index over every symbol's kind, name, path and source

Building the index takes several minutes for flask and gin together. Running the command again does nothing. If you already ran it before hybrid search existed, run it once more: that builds the new index, and the symbols you already ingested are searchable without re-ingesting.

```sh
uv run ccctx model load
```

Check it from SQL:

```sql
SELECT model_name FROM user_mining_models;                                   -- ALL_MINILM_L12_V2
SELECT VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING 'hello world' as data) AS v;  -- 384 numbers
```

`CCCTX_MODEL_URL` and `CCCTX_MODEL_CACHE` change where the file comes from and where it is kept.

The index's vector half lives in the database's vector memory pool. The first container start after vector search was added sets the pool to 256 MB and restarts the database once (`db/startup/02_vector_memory.sh`). Later starts leave it alone. The index updates when an ingest commits, so a finished ingest is searchable at once.

**2. Search.**

```sh
uv run ccctx search "url_for"                                       # the definition comes first
uv run ccctx search "url_for" --mode text                           # only symbols containing url_for
uv run ccctx search "how are incoming requests routed to handlers"  # by meaning
uv run ccctx search "middleware chain" --repo gin                   # one repository
uv run ccctx search "routing" --repo flask,gin                      # or several (also: --repo flask --repo gin)
uv run ccctx search "middleware chain" --language go --limit 3      # one language, three results
```

```text
RANK  SCORE  FEEDBACK  KEYWORD  SEMANTIC  REPO   KIND      NAME           PATH                     LINES
   1  24.38                  5         4  flask  method    Flask.url_for  src/flask/app.py         1102-1222
   2  21.82                  6         7  flask  function  url_for        src/flask/helpers.py     200-251
   4  29.69                  1        11  flask  class     TestUrlFor     tests/test_helpers.py    94-161
```

Modes, chosen with `--mode`:

- **`hybrid`** (default): keyword and semantic results fused with reciprocal rank fusion (`DBMS_HYBRID_VECTOR.SEARCH` with `RRF` and `UNION`). A symbol that both rank highly rises to the top. The keyword side matches any word of the query, and plain words also match their stems (`routed` finds `route`).
- **`text`**: keyword matching only. Every word of the query must appear.
- **`vector`**: meaning only.

How results are ranked:

- **Definitions first**: when the query is an identifier, the symbols named exactly that, or ending in `.<identifier>` such as `Flask.url_for`, come before everything else in `hybrid` and `text` mode. Matching ignores case.
- **Similarity floor**: a result found only by meaning must have a cosine similarity of at least 0.3, so an unrelated question returns nothing rather than ten weak matches. Keyword matches always count.
- **One window per file**: of a file's fallback line windows, only the best one is shown.
- **10 results by default**, `--limit` 1 to 50. `--language` keeps one language (`python`, `go`, `javascript`, `markdown` and the other languages the chunker assigns). Query text is always taken literally: `_`, `-`, `&`, quotes and parentheses are never search operators.
- **Usage feedback**: results that clients used get a small boost, at most 20%, that fades over 30 days (see [Usage feedback](#usage-feedback)). `--no-feedback` ranks without it.
- **Why each result ranked**: `SCORE` is the fused score (or the single side's score in `text` and `vector` mode), raised by `FEEDBACK` when the result was used (`+4%`; blank when there is none). `KEYWORD` and `SEMANTIC` are its rank on each side among the repositories searched, with `-` when that side did not find it.

Fusion settings:

| Setting | Default | Meaning |
|---|---|---|
| `CCCTX_TEXT_WEIGHT` | `1` | Weight of the keyword side in the fusion |
| `CCCTX_VECTOR_WEIGHT` | `1` | Weight of the semantic side in the fusion |
| `CCCTX_SEARCH_CANDIDATES` | `100` | Rows asked of the index before scoping and the result cap; widened automatically, up to 4000, when `--repo` filters most of them out |

## Usage feedback

The server learns which results helped, and lets that nudge later searches without ever overruling relevance.

**What counts as a use.** A client calls `mark_used` with a hit's repository, path and name when it cites the hit or
relies on it: a **cited** use. Reading a hit that this session's `search_code` returned, with `get_symbol` or
`read_wiki`, is an **opened** use. A result gets at most one use per session; citing it after opening it leaves one
cited use. Each use is linked to the search that returned it, so `ccctx memory list` shows `RESULTS` as
`used/returned` (`2/10`). A use is keyed by the result's repository, path and name, so it survives a re-ingest, and it
is recorded on the same background thread as runs: it never delays or changes an answer.

**Weight and decay.** A cited use weighs 1 and an opened use 0.5. A use's weight halves every 30 days: 1.00 today,
0.50 after 30 days, 0.25 after 60. A result's weight is the sum over its uses.

**The boost.** `boost = cap * min(1, weight / 5)`: 4% per fresh citation, up to the cap at a weight of 5. A result's
score becomes `relevance * (1 + boost)`. The boost only reorders what the search already found: it never adds a
result, identifier definitions still come first, a page's similarity is raised the same way when it is placed, and
facts are never boosted. A result 20% or more behind another can never pass it, so a heavily used symbol does not
take over unrelated questions.

| Setting | Default | Meaning |
|---|---|---|
| `CCCTX_FEEDBACK_CAP` | `0.2` | The largest boost, 0 to 1. `0` switches feedback off. |
| `CCCTX_FEEDBACK_HALF_LIFE_DAYS` | `30` | Days after which a use counts half as much |

```sh
uv run ccctx feedback list --repo flask                                          # weight and boost per result
uv run ccctx feedback add url_for --repo flask --path src/flask/helpers.py       # record a cited use by hand
uv run ccctx feedback add redirect --repo flask --days-ago 30 --count 3          # backdated, several
uv run ccctx feedback reset --repo flask                                         # or --all
```

```text
KIND      NAME      PATH                  USES  WEIGHT  BOOST  LAST USED            INDEXED
function  url_for   src/flask/helpers.py     1    1.00   +4%  2026-10-13 09:12:40  yes
function  redirect  src/flask/helpers.py     3    1.50   +6%  2026-09-13 09:12:41  yes
```

`INDEXED` is `no` when the symbol or page is gone; such a use boosts nothing. `--path` is needed when the name is at
several paths. Feedback never changes the index.

## Evaluating retrieval

`gold.json` is a versioned set of 20 plain-language questions about flask and gin, each with the files or
directories that answer it. `ccctx eval` runs them and counts a question as a hit when any of its top 10 results is at
an expected path (a directory matches the files under it):

```sh
uv run ccctx eval --gold gold.json                  # ranking without feedback
uv run ccctx eval --gold gold.json --with-feedback  # with it: should hold or improve recall
```

```text
Questions: 20
recall@10: 0.90 (18/20)
missed: how do tests send requests to the app without running a server?
missed: how is HTTP basic authentication checked?
```

`--limit` changes the 10. Evaluating records no run and no use. The format is
`{"version": 1, "questions": [{"question": "...", "repo": "flask", "paths": ["src/flask/app.py"]}]}`; `repo` is
optional. Bump `version` when the questions or paths change. `tests/search/test_evaluation.py` keeps the baseline as a floor.
