# Agent memory

The server remembers what it has been asked, so a new session does not work the same things out again. Memory has
three layers:

- **Runs.** Every MCP tool call is recorded with its arguments, the client that asked, the status, and the identity
  and location of each result. A run never holds source code or snippets. Recording happens on a background thread:
  it never delays or changes an answer, and a failure to record is only logged. CLI commands are not recorded.
- **Facts.** `ccctx memory consolidate` distils the runs into facts, one per piece of code (a symbol or a wiki page)
  per repository. Each fact has a subject, its text, a confidence, the IDs of the runs it came from, and references to
  the code it describes. Facts are stored with Oracle's AI Agent Memory package, in the `ccctx_mem_*` tables that
  `ccctx db migrate` creates.
- **Recall.** The `recall` tool hands the facts and the latest runs back. The server tells clients to call it at the
  start of a session, and fresh facts also show up in `search_code` as hits of kind `fact`.

```sh
uv run ccctx memory list --repo flask --limit 10   # one row per tool call, newest first
uv run ccctx memory consolidate --repo flask       # distil the runs not yet consolidated
uv run ccctx memory facts --repo flask             # fresh first, then by confidence
```

```text
flask: 20 runs read, 4 created, 15 merged, 1 weakened, 0 stale, 0 re-asked in 0.4s (template/1)
```

**Merging.** A run is about the code its first result points at, so two runs merge when they led to the same code,
however the question was worded: "where is url_for defined" and "where's url_for defined?" give one `url_for` fact
holding both wordings. A wording that later leads to other code moves to that code's fact, and the two facts are
linked as contradicting each other.

**Confidence** is `(1 - 0.5^agree) * 0.5^contradict`. One agreeing run gives 0.5, two give 0.75 and three give 0.875,
and each contradiction halves it. A contradiction is a wording that moved, a finding that changed (for example a
different caller count), a re-ask answered by other code, or the code being removed.

**Keeping pace with the code.** Every `ccctx ingest` consolidates afterwards and prints a `Memory` line when anything
happened. Before distilling new runs, each fresh fact is checked against the index:

| The fact's code | What happens |
|---|---|
| unchanged | nothing |
| moved, same content | the fact points at the new place |
| edited | it is re-asked: the calls it came from run again against the new index (not recorded as runs). If the same code still answers, the fact stays fresh. If other code answers, it goes stale and its confidence halves. |
| removed | the fact goes stale with `` `X` was removed `` and its confidence halves |

A stale fact is shown as stale everywhere, is left out of search, and becomes fresh again only when a new run
confirms it. A consolidation failure never undoes an ingestion: the summary says `Memory    not consolidated: <why>`.

**The model that writes fact text (optional).** By default a template writes each fact from what the runs found,
and nothing leaves the database. To have a language model write the text instead, set `CCCTX_MEMORY_MODEL` to a
LiteLLM model string, plus its key in `CCCTX_MEMORY_MODEL_KEY` or the provider's usual variable:

```sh
CCCTX_MEMORY_MODEL=anthropic/claude-sonnet-5-5
ANTHROPIC_API_KEY=...
```

For each fact it writes, the model is sent exactly this: the subject's name, kind and path; its source, at most 200
lines; the findings (where it is defined, its caller, callee and reach counts and names); the names and locations of
the related symbols; and the question wordings. Nothing else is sent, and search, chunking and embedding never send
anything. The model only writes the text. Which code a fact is about, merging, confidence and staleness are decided the
same way with or without it. Its text may name only code that appears in what it was sent; otherwise, and whenever
the call fails, the template writes the fact. Each fact records which one wrote it (`template/1` or
`llm:<model>`).

**Removing a repository.** There is no `repo remove` command yet. When one is added, it must call `memory.forget`,
which deletes the repository's facts. Runs that belonged only to it are deleted by the next consolidation.
