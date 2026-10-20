# Data Model: Code Context Tools for AI Clients

No migration. The tables from steps 3 to 7 already hold everything the tools return: `ccctx_symbols.source` is each definition's indexed text, `ccctx_files.language` its language, and the graph tables its calls. This step reshapes one in-memory result (`semantic.Result`), adds one (`graph.Definition` with its `Definitions` envelope), and reshapes the server's tool set and envelopes around them.

## Relationships

```text
Repository (ccctx_repos, unchanged)
  1 ──< File (ccctx_files, unchanged)          language: the chunker's language for the path
          1 ──< Symbol (ccctx_symbols, unchanged)  source: clob, the indexed text

Search hit      ──> one Symbol (any kind, line windows included)   snippet read from Symbol.source
Definition      ──> one Symbol (kind <> 'chunk')                   source read from Symbol.source
Caller / Callee / Impact row ──> Symbols through ccctx_graph (step 7, unchanged)

Tool (server.py) ──> one core call ──> one envelope { status, reason, results, ... }
```

Every returned item carries `repo`, `path` and a line range (FR-014). Nothing is written by any tool.

## Search hit (`semantic.Result`, reshaped)

One ranked match for a query. Produced by `semantic.search`, returned by `ccctx search` and by `search_code` as `SearchHit`.

| Field | Type | Rule |
|---|---|---|
| `rank` | `int` | 1-based position in the returned list. |
| `score` | `float` | Fused score (hybrid is the only mode the tool uses). |
| `similarity` | `float \| None` | Semantic similarity 0 to 1. None when the semantic side did not find the symbol. |
| `keyword_rank` | `int \| None` | Rank on the keyword side. None when it missed. |
| `semantic_rank` | `int \| None` | Rank on the semantic side. None when it missed. |
| `repo` | `str` | Repository name. |
| `language` | `str` | **New.** `ccctx_files.language` of the hit's file. |
| `kind` | `str` | One of `function`, `method`, `class`, `interface`, `type`, `module`, `chunk`. |
| `name` | `str` | Qualified symbol name, or `<path>:<start>-<end>` for a line window. |
| `path` | `str` | Path relative to the repository root. |
| `start_line` | `int` | First line, 1-based. |
| `end_line` | `int` | Last line, `>= start_line`. |
| `snippet` | `str` | **New.** The opening of the stored source: `dbms_lob.substr(source, 800, 1)`, then the first 10 lines of that (FR-007). Never more than 10 lines or 800 characters. Loaded in the query that already reads path and lines. |

### Search request (validated in `semantic.search`)

| Parameter | Type | Default | Rule |
|---|---|---|---|
| `query` | `str` | required | Stripped. Empty is refused: `the question is empty`. |
| `repo` | `str \| None` | all | Must be a registered repository. Unknown is refused by the registry, before searching. The CLI's `--repo` may repeat; the tool takes one. |
| `language` | `str \| None` | all | Must be one the chunker assigns: the values of `chunker.EXTENSIONS` plus `text`. Checked before connecting. Unknown is refused with the list of valid languages. |
| `limit` | `int` | 10 | `type(limit) is int` and 1 to 50, checked before connecting. Replaces the fixed `LIMIT = 10`. |

A hit is in scope when both the repository and the language filter match. The pool-widening loop counts in-scope hits against `limit` and stops at `MAX_CANDIDATES` as before. `ccctx search` gains `--language` and `--limit` and calls the same function, so the CLI and the tool return identical hits in identical order (FR-006).

## Definition (`graph.Definition`, new)

One named definition read back in full by `graph.definitions(conn, name, repos)`. Returned by `get_symbol`.

| Field | Type | Rule |
|---|---|---|
| `name` | `str` | Qualified name as stored, e.g. `Flask.dispatch_request`. Lets the client tell matches of a bare name apart. |
| `kind` | `str` | Any kind except `chunk`. Line windows are never returned. |
| `repo` | `str` | Repository name. |
| `path` | `str` | Path relative to the repository root. |
| `start_line` | `int` | First line of the full definition. |
| `end_line` | `int` | Last line of the full definition, even when `source` is cut. |
| `source` | `str` | `ccctx_symbols.source`, the text exactly as indexed. At most 400 lines (FR-009). |
| `cut` | `bool` | True when the stored source had more than 400 lines and `source` holds only the first 400. |

### Definitions (the lookup result)

| Field | Type | Rule |
|---|---|---|
| `definitions` | `list[Definition]` | At most 5, ordered by repository name, path, start line (FR-008). |
| `total` | `int` | How many definitions matched, before the cap. |
| `truncated` | `bool` | `total > len(definitions)`. |

### Name matching (shared with `_targets`)

- `name` is stripped. Empty is refused: `the name is empty` (`graph.check_name`).
- Case-sensitive. A name containing `.` matches exactly that qualified name. A bare name matches `x` and any `<anything>.x`.
- `kind = 'chunk'` is excluded.
- `repo`, when given, must be registered. Unknown is refused before matching. A registered but unindexed repository has no symbols, so it yields the "no symbol" refusal, not an error.
- No match is refused: `no symbol named '<name>'`.

`get_symbol` serves stored source only. It never reads the repository's working tree.

## Caller, Callee, Impact row (`graph.Caller`, `graph.Callee`, `graph.Impact`, unchanged)

The step 7 rows, returned unchanged by `find_callers`, `find_callees` and `impact_of`. Each tool returns at most 200 rows (`server.LIMIT`) and `truncated` when more existed (FR-004a, FR-010, FR-011). `impact_of` takes `depth`, `type(depth) is int` and 1 to 5 (`graph.check_depth`), default 3, rows ordered nearest first.

## Tool set (`server.py`, reshaped)

The server's public contract. Tool names are part of it, so this step moves the version to 1.0.0 (`pyproject.toml` and `__version__`).

| Tool | Parameters | Core call | Envelope | Was |
|---|---|---|---|---|
| `search_code` | `query`, `repo?`, `language?`, `limit?` | `semantic.search(..., mode="hybrid")` | `SearchResults` | `search` |
| `get_symbol` | `name`, `repo?` | `graph.definitions` | `SymbolResults` | new |
| `find_callers` | `name`, `repo?` | `graph.callers` | `CallerResults` | `callers` |
| `find_callees` | `name`, `repo?` | `graph.calls` | `CalleeResults` | `calls` |
| `impact_of` | `name`, `depth?`, `repo?` | `graph.impact` | `ImpactResults` | `impact` |
| `list_repositories` | none | `registry.list_repos` | `RepoList` | unchanged |

Removed: `health`, `search`, `callers`, `calls`, `impact`. The `repos` list parameter and `mode` are dropped from the tools; the CLI keeps both.

Every tool:
- Carries `ToolAnnotations(readOnlyHint=True)`.
- Declares each parameter as `Annotated[<type>, Field(description=...)]`, so every parameter has a `description` in its input schema (FR-012). Ranges and defaults are stated there and enforced in the core, not as schema `minimum`/`maximum`.
- Has a description that states, in order, the question it answers, when to use it instead of its neighbors, what comes back, and the next step (research R4).

### Envelopes

| Envelope | Fields |
|---|---|
| `SearchResults` | `status`, `reason`, `results: list[SearchHit]` |
| `SymbolResults` | `status`, `reason`, `results: list[SymbolHit]`, `total: int`, `truncated: bool` |
| `CallerResults` / `CalleeResults` / `ImpactResults` | `status`, `reason`, `results`, `truncated` (step 7, unchanged) |
| `RepoList` | `database`, `reason`, `repositories` (unchanged) |

`SearchHit` gains `language` and `snippet`. `SymbolHit` mirrors `Definition`. On a refusal, `results` is empty, `total` is 0 and `truncated` is false.

## Call outcome (state per call)

A call holds no state between invocations; the server keeps no connection open, so a database that comes back is used by the next call without a restart (SC-006).

```text
call ──> parameters type-check (pydantic)
           ├─ wrong type or unknown parameter ──> isError result with the validation reason
           └─ ok ──> core checks (empty text, range, unknown language)   before connecting
                       ├─ refused ──> status "unavailable", reason
                       └─ ok ──> connect, migrate, query
                                   ├─ ConfigError / RegistryError / ModelError / ValueError ──> "unavailable", reason
                                   ├─ oracledb.Error ──> "unavailable", db.describe(e) (no password)
                                   └─ rows ──> status "ok", reason null, capped results
```

A missing search model refuses `search_code` only. The other tools never load the model.

## Call log record (stderr, unchanged shape)

One JSON line per call from `_logged`: `event: "tool"`, `tool`, `ms`, `status` (`ok`, `unavailable`, `error`, or `reachable`/`unreachable` for `list_repositories`), `results` (the count). Never arguments, names or source text (FR-015). Nothing but protocol messages goes to stdout (FR-002).
