# Research: Code Relationship Graph

The property graph facts below were probed on the running 23.26 database with throwaway tables, which were then dropped. The parser facts were checked against the installed tree-sitter 0.25 grammars.

## The property graph

- **Decision**: migration 6 creates `ccctx_graph` with `create or replace property graph`, so a later migration can redefine it:

  ```sql
  create or replace property graph ccctx_graph
    vertex tables (
      ccctx_files   key (id) label code_file properties (id, repo_id, path),
      ccctx_symbols key (id) label symbol    properties (id, file_id, name, kind, start_line, end_line))
    edge tables (
      ccctx_symbols as ccctx_defines key (id)
        source key (file_id) references ccctx_files (id)
        destination key (id) references ccctx_symbols (id) label defines,
      ccctx_imports key (id)
        source key (importer_id) references ccctx_files (id)
        destination key (imported_id) references ccctx_files (id) label imports,
      ccctx_calls key (id)
        source key (caller_id) references ccctx_symbols (id)
        destination key (callee_id) references ccctx_symbols (id) label calls properties (line),
      ccctx_file_calls key (id)
        source key (file_id) references ccctx_files (id)
        destination key (callee_id) references ccctx_symbols (id) label calls properties (line))
  ```
- **Rationale**: the probe showed that one table can be both a vertex table and, under an alias, an edge table. `defines` is therefore the existing `ccctx_symbols.file_id` column, so nothing is copied (FR-004). A plain second `create` raises ORA-00955, which migrations tolerate, so it would silently keep an outdated definition; `create or replace` worked in the probe. `file` is a reserved word in graph DDL (ORA-03050), so the label is `code_file`.
- **Alternatives considered**: a separate `ccctx_defines` table duplicates `file_id`. Views as element tables add an object for no gain.

## The queries

- **Decision**: three `graph_table` queries, with `match` patterns.

  Callers:
  ```sql
  match (c is symbol) -[e is calls]-> (t is symbol) where t.id in (…)
  ```
  Calls:
  ```sql
  match (t is symbol) -[e is calls]-> (c is symbol)
  ```
  Impact:
  ```sql
  match (c is symbol) -[e is calls]->{1,N} (t is symbol)
  columns (c.id, count(e.line) as hops)
  ```
  Impact then takes `min(hops)` per symbol, ordered by hops. N is a validated integer from 1 to 5, written into the SQL text, because a quantifier cannot be a bind variable. The callers, calls and impact columns are joined back to files and repositories for the path, the repository filter and the definition each call reaches.
- **Rationale**: the probe returned the expected callers and the expected 1, 2 and 3 hop distances on a small cycle. A bounded quantifier always terminates, so recursion and cycles are safe (US3 scenario 3).

## Module-level calls

- **Decision**: a call outside every symbol is an edge from the file. `ccctx_file_calls` (`file_id` to `callee_id`, with `line`) is a second edge table with the same `calls` label and `code_file` as its source. `callers` answers with two `graph_table` queries, one per source label, and lists file callers with kind `file`. Impact counts symbols only: a file has no callers, so no path continues through one, and a file is not a symbol that can break.
- **Rationale**: an edge table has exactly one source vertex table. Two `calls` tables keep every pattern labeled and its properties typed. This avoids a file-or-symbol vertex with mismatched properties, and avoids a synthetic "module" symbol that would change symbol counts and search results.

## Extracting calls and imports

- **Decision**: `chunker.parse(language, text)` returns the chunks plus the calls and imports, from one parse. `chunk` stays as a wrapper for its tests. The `root.has_error` gate still returns nothing, so fallback files contribute no relationships.
  - **Call forms.** Each call is recorded as `(caller, name, form, receiver, line)`:
    - Python `call`, Go `call_expression` and JavaScript `call_expression`/`new_expression`, with the `function` field being an identifier (`bare`), or an attribute, selector or member (`attr`, keeping the receiver text).
    - Calls through subscripts, calls of calls and function literals are skipped.
  - **The caller** is the innermost enclosing function or method, found by byte range against each definition node itself, not its decorated wrapper.
    - Decorator calls therefore belong to the enclosing scope, because they run at definition time.
    - Calls in a class body outside methods belong to the class.
    - Nested functions, lambdas and literals are not symbols, so their calls go to the enclosing symbol.
  - **Imports**:
    - Python `import a.b`, `from a.b import c` and relative `from . import x`, with the level taken from the prefix length.
    - Go `import_spec` paths, with the alias or last segment as the bound name.
    - JavaScript `import … from` and `require("…")` with a relative path.

    Each import keeps the name it binds in the file.
- **Rationale**: comments, docstrings and strings are separate node types, so they never produce a call (FR-003).

## Resolving a call to a symbol

- **Decision**: resolution is by name within the repository, in this order:
  1. A `bare` call to `x` matches functions and classes named `x`, plus Go types for Go.
  2. An `attr` call whose receiver is a module or package the file imports (`flask.url_for`, `gin.New`) is treated like a bare call.
  3. An `attr` call on `self`, `cls` or `this` matches methods `*.x`, preferring the enclosing class.
  4. Any other `attr` call matches methods named `*.x`.

  Among the matches, the definitions in the same file win. Failing that, those in a file the caller's file imports. Failing that, every match in the repository. A call with no match is dropped.
- **Rationale**: 42 of flask's 56 `url_for(` lines are `flask.url_for(...)`, a module-qualified call. Without rule 2 they would resolve to the `Flask.url_for` method. `flask` re-exports `url_for` from `helpers.py`, and the only function named `url_for` is there, so the repository-wide fallback reaches it without following re-exports. This is a name heuristic, not type inference (spec Assumptions).

## Keeping the graph current

- **Decision**: store what the parse saw, and derive the edges from it.
  - `ccctx_call_refs` holds one row per call: file, caller symbol (nullable), name, form, receiver, line.
  - `ccctx_import_refs` holds one row per import: file, module path, level, bound name.
  - Both cascade from their file. The refs of every file an ingest re-reads are replaced.
  - After writing, the same transaction rebuilds the repository's `ccctx_imports`, `ccctx_calls` and `ccctx_file_calls` from all of its refs and symbols. This runs in Python over rows already in memory, then one delete and one bulk insert per edge table.
- **Rationale**: an edited callee gets a new symbol id, and a renamed or deleted file loses its rows. Edges stored only once would lose calls from unchanged callers. Rebuilding the edges from stored refs makes an incremental graph identical to a full rebuild by construction (FR-012). The work is a few thousand rows of Python and SQL, with no embedding.
  - simplified: edges are rebuilt for the whole repository on every ingest. Rebuild only the affected names when that cost shows up.

## Repositories indexed before this step

- **Decision**: migration 6 adds `ccctx_repos.extract_version` (NULL). The code defines `EXTRACT_VERSION = 1`. When the stored value differs, ingest re-reads every listed file and treats each as changed. `_keep_unchanged` keeps every symbol whose code is unchanged, so this re-parses without re-embedding. The run then sets the version.
- **Rationale**: FR-013, without the 11-minute re-embed a full rebuild would cost on flask. The same switch covers a future change to extraction rules.

## CLI and MCP

- **Decision**:
  - The commands are `ccctx callers <name>`, `ccctx calls <name>` and `ccctx impact <name> [--depth N]`, plus MCP tools `callers`, `calls` and `impact`. All of them call `graph.callers`, `graph.calls` and `graph.impact`.
  - Depth is checked in the core and before connecting, so a bad value exits 1, not argparse's exit 2.
  - Name matching is case-sensitive. A qualified name must match exactly. A bare name matches every function, method, class or type whose name is `x` or ends in `.x`.
  - The graph commands do not need the embedding model.
- **Rationale**: code names are case-sensitive, unlike search questions. The repository filter, the exit codes and the `{status, reason, results}` envelope follow `search`.
