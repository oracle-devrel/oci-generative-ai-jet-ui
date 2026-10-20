# Contract: schema migration 2 (`commit_sha`)

Extends `specs/002-repo-registry/contracts/schema.md`. Applied by `ccctx db migrate` and by the migrate pre-step of every other command, before any ingest transaction opens.

## Migration 2

```sql
delete from ccctx_symbols;
alter table ccctx_symbols add (commit_sha varchar2(64) not null);
alter table ccctx_symbols add constraint ccctx_symbols_commit_ck
  check (regexp_like(commit_sha, '^[0-9a-f]{40}([0-9a-f]{24})?$'));
```

Re-runnable: `ORA-01430` (column exists) and `ORA-02264` (constraint name used) are tolerated, alongside the step 2 codes.

## Stored values per ingest

| Table.column | Value |
|---|---|
| `ccctx_files.path` | Path relative to the repository root, `/`-separated. |
| `ccctx_files.language` | `python`, `go`, `javascript`, or the fallback extension language, else `text`. |
| `ccctx_files.content_hash` | Hex SHA-256 of the file bytes. |
| `ccctx_symbols.name` | Symbol name (`Type.method` for methods) or `<file name>:<start>-<end>` for fallback chunks. |
| `ccctx_symbols.kind` | `function`, `method`, `class`, `type`, `interface`, or `chunk` (fallback). |
| `ccctx_symbols.start_line`, `end_line` | 1-based, inclusive. |
| `ccctx_symbols.source` | Exactly lines `start_line`..`end_line` of the file (CLOB). |
| `ccctx_symbols.content_hash` | Hex SHA-256 of `source`. |
| `ccctx_symbols.commit_sha` | Full `git rev-parse HEAD` at ingest (40 or 64 lowercase hex). |

## Replace semantics

One transaction per ingest: `select … from ccctx_repos where id = :id for update nowait` → `delete from ccctx_files where repo_id = :id` (cascades to symbols) → insert files (`returning id`) → `executemany` symbols → commit. Any error rolls back, leaving the previous index.
