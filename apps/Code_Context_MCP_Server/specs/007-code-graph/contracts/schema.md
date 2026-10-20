# Contract: schema migration 6, code graph

Extends `specs/006-incremental-ingest/contracts/schema.md`. Migration 6 stores the calls and imports each parse sees, the call and import edges resolved from them, and `ccctx_graph`, a property graph over the existing files and symbols. `CREATE PROPERTY GRAPH`, `GRAPH_TABLE` and `MATCH` are the pinned identifiers.

## Migration 6 "code graph"

Applied by `ccctx db migrate` and the migrate pre-step of every command. Ordered and re-runnable.

```sql
alter table ccctx_repos add (extract_version number);        -- ORA-01430 tolerated

create table ccctx_call_refs (
  id         number generated always as identity primary key,
  file_id    number not null references ccctx_files (id) on delete cascade,
  caller_id  number references ccctx_symbols (id) on delete cascade,
  name       varchar2(512) not null,
  form       varchar2(4) not null,
  receiver   varchar2(512),
  line       number not null,
  constraint ccctx_call_refs_form_ck check (form in ('bare', 'attr')),
  constraint ccctx_call_refs_line_ck check (line >= 1)
);                                                           -- ORA-00955 tolerated
create index ccctx_call_refs_file_ix   on ccctx_call_refs (file_id);
create index ccctx_call_refs_caller_ix on ccctx_call_refs (caller_id);

create table ccctx_import_refs (
  id         number generated always as identity primary key,
  file_id    number not null references ccctx_files (id) on delete cascade,
  module     varchar2(1024) not null,
  rel_level  number default 0 not null,
  bound      varchar2(512)
);
create index ccctx_import_refs_file_ix on ccctx_import_refs (file_id);

create table ccctx_calls (
  id         number generated always as identity primary key,
  caller_id  number not null references ccctx_symbols (id) on delete cascade,
  callee_id  number not null references ccctx_symbols (id) on delete cascade,
  line       number not null
);
create index ccctx_calls_caller_ix on ccctx_calls (caller_id);
create index ccctx_calls_callee_ix on ccctx_calls (callee_id);

create table ccctx_file_calls (
  id         number generated always as identity primary key,
  file_id    number not null references ccctx_files (id) on delete cascade,
  callee_id  number not null references ccctx_symbols (id) on delete cascade,
  line       number not null
);
create index ccctx_file_calls_file_ix   on ccctx_file_calls (file_id);
create index ccctx_file_calls_callee_ix on ccctx_file_calls (callee_id);

create table ccctx_imports (
  id           number generated always as identity primary key,
  importer_id  number not null references ccctx_files (id) on delete cascade,
  imported_id  number not null references ccctx_files (id) on delete cascade,
  constraint ccctx_imports_pair_uk unique (importer_id, imported_id)
);
create index ccctx_imports_imported_ix on ccctx_imports (imported_id);

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

### Re-running

- ORA-00955 (name exists), ORA-01408 (column list already indexed), ORA-01430 (column exists) and ORA-02261 (unique key exists) are in the tolerated set. A second run of the tables, columns and indexes is a no-op.
- The property graph uses `create or replace`, which is idempotent. A plain `create` would raise ORA-00955 on a later run, and the tolerated code would silently keep an outdated definition.
- The `ccctx_imports_pair_uk` unique index also serves lookups by `importer_id`, so that column has no separate index.

## Tables

| Table | One row per | Written |
|---|---|---|
| `ccctx_call_refs` | Call seen in a parsed file. `caller_id` is the innermost enclosing symbol, NULL for a module-level call. `form` is `bare` (`x(...)`) or `attr` (`r.x(...)`, with `receiver` the text of `r`). | Replaced for every file an ingest re-reads. |
| `ccctx_import_refs` | Import seen in a parsed file. `module` is the imported path (a Python from-import appends the member, `from a.b import c` is `a.b.c`), `rel_level` the number of leading dots of a Python relative import (`0` otherwise), `bound` the name the import binds in the file. | Replaced for every file an ingest re-reads. |
| `ccctx_calls` | Resolved call from a symbol to a symbol, with the call line. | Rebuilt for the whole repository from its refs on every ingest. |
| `ccctx_file_calls` | Resolved module-level call from a file to a symbol, with the call line. | Rebuilt with `ccctx_calls`. |
| `ccctx_imports` | File importing another file of the same repository. Each pair once. | Rebuilt with `ccctx_calls`. |

- Files that fall back to line windows have no refs, so they have no edges.
- Every foreign key cascades. Deleting a file removes its refs and every edge touching its symbols.
- Edges are never kept across ingests. An edited symbol gets a new id, so edges are rebuilt from the stored refs in the ingest transaction. An incremental graph therefore equals a full rebuild.

## `ccctx_repos.extract_version`

- NULL for repositories indexed before this step.
- The code defines `EXTRACT_VERSION = 1`. When the stored value differs, ingest re-reads every listed file and stores its refs. Unchanged symbols keep their rows, so nothing is re-embedded.
- Set in the ingest transaction, beside `indexed_commit`. It moves only if the index commits.

## The graph

| Element | Table | Label | Properties |
|---|---|---|---|
| Vertex | `ccctx_files` | `code_file` | `id`, `repo_id`, `path` |
| Vertex | `ccctx_symbols` | `symbol` | `id`, `file_id`, `name`, `kind`, `start_line`, `end_line` |
| Edge | `ccctx_symbols` as `ccctx_defines` | `defines` | |
| Edge | `ccctx_imports` | `imports` | |
| Edge | `ccctx_calls` | `calls` | `line` |
| Edge | `ccctx_file_calls` | `calls` | `line` |

- `defines` is the existing `ccctx_symbols.file_id` column. Nothing is copied.
- The file label is `code_file`, because `file` is a reserved word in graph DDL (ORA-03050).
- The two `calls` tables differ only in their source: a symbol, or a file for a module-level call.

## Query shapes

Each question is a `GRAPH_TABLE` query with a `MATCH` pattern. `(…)` is the ids of the definitions matching the name in the selected repositories. The ids returned are joined back to `ccctx_symbols`, `ccctx_files` and `ccctx_repos` for names, paths and the repository filter.

Callers, one query per source label:

```sql
select caller_id, line, callee_id
  from graph_table (ccctx_graph
    match (c is symbol) -[e is calls]-> (t is symbol)
    where t.id in (…)
    columns (c.id as caller_id, e.line as line, t.id as callee_id))

select file_id, line, callee_id
  from graph_table (ccctx_graph
    match (c is code_file) -[e is calls]-> (t is symbol)
    where t.id in (…)
    columns (c.id as file_id, e.line as line, t.id as callee_id))
```

Calls:

```sql
select caller_id, line, callee_id
  from graph_table (ccctx_graph
    match (t is symbol) -[e is calls]-> (c is symbol)
    where t.id in (…)
    columns (t.id as caller_id, e.line as line, c.id as callee_id))
```

Impact, with `N` the depth:

```sql
select id, min(hops) as hops
  from graph_table (ccctx_graph
    match (c is symbol) -[e is calls]->{1,N} (t is symbol)
    where t.id in (…)
    columns (c.id as id, count(e.line) as hops))
 group by id
 order by hops
```

- `N` is a validated integer from 1 to 5, written into the SQL text, because a quantifier cannot be a bind variable.
- The bounded quantifier always terminates, so recursion and cycles are safe.
- `min(hops)` lists each symbol once, at its shortest distance.
- Only `symbol` vertices are on the path. A file has no callers, so no path continues through one.

## Unchanged

`ccctx_files`, `ccctx_symbols`, the hybrid vector index and the step 5 revision columns are unchanged. Search results and symbol counts are unaffected.
