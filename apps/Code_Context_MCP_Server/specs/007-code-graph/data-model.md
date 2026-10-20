# Data Model: Code Relationship Graph

Migration 6 "code graph" adds two reference tables, three edge tables and one column on `ccctx_repos`. It creates the property graph `ccctx_graph` over them and the existing tables. `ccctx_files` and `ccctx_symbols` keep their columns and constraints. `graph.py` returns three in-memory result shapes.

Every new table has `id number generated always as identity primary key`. Every new foreign key is `on delete cascade`.

## Relationships

```text
Repository (ccctx_repos, reshaped)
  ├─ extract_version                             which extraction rules its refs came from
  1 ──< File (ccctx_files, unchanged)            on delete cascade
          ├──< Symbol (ccctx_symbols, unchanged)  on delete cascade
          ├──< Call ref (ccctx_call_refs)         on delete cascade; caller_id ──> Symbol, nullable
          ├──< Import ref (ccctx_import_refs)     on delete cascade
          ├──< Import edge (ccctx_imports)        as importer and as imported, both cascade
          └──< File call edge (ccctx_file_calls)  as caller; callee_id ──> Symbol, cascade

Symbol ──< Call edge (ccctx_calls) as caller and as callee, both cascade
```

Refs are what the parse saw. Edges are derived from refs and symbols. Deleting a file removes its symbols, its refs and every edge that touches either.

## Call ref (`ccctx_call_refs`, new)

One row per call found in a parsed file.

| Field | Type | Rule |
|---|---|---|
| `file_id` | `number not null` | References `ccctx_files (id)`. The file the call is written in. |
| `caller_id` | `number`, nullable | References `ccctx_symbols (id)`. The innermost enclosing function, method or class. NULL means the call is at module level. |
| `name` | `varchar2(512) not null` | The called name, last component only. |
| `form` | `varchar2(4) not null` | `check (form in ('bare','attr'))`. `bare` is `x(...)`. `attr` is `obj.x(...)`. |
| `receiver` | `varchar2(512)`, nullable | The text before the dot for an `attr` call. NULL for a `bare` call. |
| `line` | `number not null` | The line of the call. |

Index `ccctx_call_refs_file_ix` on `file_id`.

## Import ref (`ccctx_import_refs`, new)

One row per import found in a parsed file.

| Field | Type | Rule |
|---|---|---|
| `file_id` | `number not null` | References `ccctx_files (id)`. The importing file. |
| `module` | `varchar2(1024) not null` | A dotted Python module, a Go import path, or a JavaScript relative path. Leading dots are stripped. A Python from-import names the member (`from a.b import c` is `a.b.c`), because the member may be a submodule; resolution falls back to the parent package. |
| `rel_level` | `number default 0 not null` | The Python relative import level, from the count of leading dots. 0 is absolute. |
| `bound` | `varchar2(512)`, nullable | The name the import binds in the file. |

Index `ccctx_import_refs_file_ix` on `file_id`.

## Call edge (`ccctx_calls`, new)

A symbol calling a symbol.

| Field | Type | Rule |
|---|---|---|
| `caller_id` | `number not null` | References `ccctx_symbols (id)`. |
| `callee_id` | `number not null` | References `ccctx_symbols (id)`. |
| `line` | `number not null` | The line of the call. |

Indexes on `caller_id` and on `callee_id`.

## File call edge (`ccctx_file_calls`, new)

A module-level call, from the file to a symbol.

| Field | Type | Rule |
|---|---|---|
| `file_id` | `number not null` | References `ccctx_files (id)`. |
| `callee_id` | `number not null` | References `ccctx_symbols (id)`. |
| `line` | `number not null` | The line of the call. |

Index on `callee_id`.

## Import edge (`ccctx_imports`, new)

A file importing a file in the same repository.

| Field | Type | Rule |
|---|---|---|
| `importer_id` | `number not null` | References `ccctx_files (id)`. |
| `imported_id` | `number not null` | References `ccctx_files (id)`. |

Unique `(importer_id, imported_id)`. A Go package import yields one row per file in that package directory.

## Repository (`ccctx_repos`, reshaped)

| Field | Type | Rule |
|---|---|---|
| `extract_version` | `number`, nullable | The extraction rules the stored refs came from. The code constant is `EXTRACT_VERSION = 1`. NULL means indexed before this step. |

## Property graph (`ccctx_graph`, new)

Created with `create or replace property graph`, exactly as in research.md.

| Element | Table | Label | Ends |
|---|---|---|---|
| Vertex | `ccctx_files` | `code_file` | |
| Vertex | `ccctx_symbols` | `symbol` | |
| Edge | `ccctx_symbols` as `ccctx_defines` | `defines` | `code_file` to `symbol`, through `file_id` |
| Edge | `ccctx_imports` | `imports` | `code_file` to `code_file` |
| Edge | `ccctx_calls` | `calls` | `symbol` to `symbol`, property `line` |
| Edge | `ccctx_file_calls` | `calls` | `code_file` to `symbol`, property `line` |

The graph holds no rows of its own. It reads the tables above (FR-004).

## Validation rules

- Refs and edges never cross repositories. When edges are built, both ends must be in the same repository.
- A ref's `caller_id`, when set, is a symbol of the same file.
- Files that fall back to line windows (symbols of kind `chunk`) have no refs, so they have no call or import edges.
- Calls in comments, docstrings and string literals are never refs (FR-003).
- A call that resolves to no indexed symbol is a ref with no edge.
- A call inside a method is attributed to the method, not to its class.
- Refs are replaced for every file an ingest re-reads. Refs of unchanged files are kept.
- Edges are derived data. After every ingest write, the same transaction deletes and rebuilds all of the repository's `ccctx_imports`, `ccctx_calls` and `ccctx_file_calls` from its refs and symbols. Nothing edits an edge directly.
- So the edges after an incremental ingest equal the edges after a full rebuild (FR-012). Equality is checked by names and paths, not ids, because symbol ids change on edit.

## Extract version (state transitions)

Checked once per ingest, after the repository row is locked.

```text
extract_version = EXTRACT_VERSION             ──> normal ingest (full, incremental or current)
extract_version NULL or < EXTRACT_VERSION     ──> every listed file re-read as changed
```

On the second path:

- Every listed file is re-parsed for refs.
- Symbols whose code is unchanged keep their rows, so nothing is re-embedded.
- The run sets `extract_version = EXTRACT_VERSION` in the same transaction (FR-013).
- A failed run rolls back and leaves `extract_version` as it was.

## Query results (in memory, `graph.py`)

### Caller

One row of `callers`.

| Field | Rule |
|---|---|
| `repo` | The repository name. |
| `kind` | The calling symbol's kind. `file` for a module-level call. |
| `name` | The calling symbol's qualified name. `(module)` for a module-level call. |
| `path` | The file the call is in. |
| `line` | The line of the call. |
| `callee` | The qualified name of the definition called. |

### Callee

One row of `calls`.

| Field | Rule |
|---|---|
| `caller` | The qualified name of the matched definition making the call. |
| `line` | The line of the call. |
| `repo` | The called symbol's repository. |
| `kind` | The called symbol's kind. |
| `name` | The called symbol's qualified name. |
| `path` | The called symbol's file. |
| `start_line`, `end_line` | The called symbol's lines. |

### Impact

One row of `impact`, one per symbol, ordered by `hops`.

| Field | Rule |
|---|---|
| `hops` | The shortest call distance to the target, from 1 to the requested depth. |
| `repo` | The affected symbol's repository. |
| `kind` | The affected symbol's kind. Never `file`. |
| `name` | The affected symbol's qualified name. |
| `path` | The affected symbol's file. |
| `start_line`, `end_line` | The affected symbol's lines. |
