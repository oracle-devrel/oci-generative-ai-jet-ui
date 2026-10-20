# Contract: schema migration 5, repo indexed revision

Extends `specs/005-hybrid-search/contracts/schema.md`. Migration 5 records, on each repository row, the revision it was last indexed at.

## Migration 5 "repo indexed revision"

Applied by `ccctx db migrate` and the migrate pre-step of every command. Ordered and re-runnable.

```sql
alter table ccctx_repos add (
  indexed_commit  varchar2(64),
  indexed_dirty   boolean,
  indexed_at      timestamp with time zone
);                                                           -- ORA-01430 tolerated
alter table ccctx_repos add constraint ccctx_repos_indexed_ck
  check (indexed_commit is null
         or regexp_like(indexed_commit, '^[0-9a-f]{40}([0-9a-f]{24})?$'));   -- ORA-02264 tolerated
```

All three columns are nullable. There is no backfill. ORA-01430 (column exists) and ORA-02264 (constraint name exists) are already in the tolerated set, so a second run is a no-op.

## Columns

| Column | Value |
|---|---|
| `indexed_commit` | The HEAD commit of the last successful ingest, 40 or 64 lowercase hex. The check matches `ccctx_symbols_commit_ck`. |
| `indexed_dirty` | Whether tracked files had uncommitted changes at that ingest (`git status --porcelain --untracked-files=no`). When true, the next ingest re-checks every listed file. |
| `indexed_at` | When that ingest committed. |

## When they are written

- In the ingest transaction, after the repository row is locked with `for update nowait` and after the files and symbols are written.
- Just before that transaction commits. They move only if the index commits.
- By full and incremental runs, including an incremental run with zero file changes after HEAD moved.
- Never by an up-to-date run or a failed run. Both roll back and leave the previous values.

## Reading them

- `indexed_commit` NULL means rebuild in full. This covers repositories ingested before this step and repositories never ingested.
- An `indexed_commit` that `git rev-parse --verify --quiet <sha>^{commit}` rejects also means rebuild in full.
- They are read under the same row lock as the stored path to hash map, so a concurrent ingest cannot make the change set stale.

## Unchanged

`ccctx_files`, `ccctx_symbols`, the hybrid vector index and `ccctx_embedding_model` are unchanged. Rows of unchanged files keep their `commit_sha`. Deleting a `ccctx_files` row still cascades to its symbols, and the hybrid index syncs on commit.
