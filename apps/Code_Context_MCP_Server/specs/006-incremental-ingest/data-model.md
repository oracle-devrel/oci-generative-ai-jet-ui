# Data Model: Incremental Re-indexing

This step reshapes one stored entity. `ccctx_repos` gains three nullable columns in migration 5. It introduces one in-memory entity, the change set, and extends the in-memory `Summary`. `ccctx_files` and `ccctx_symbols` keep their columns and constraints. Ingest now deletes and inserts their rows per file instead of per repository.

## Relationships

```text
Repository (ccctx_repos, reshaped)
  ├─ indexed_commit, indexed_dirty, indexed_at   the last committed ingest
  1 ──< File (ccctx_files, unchanged)            on delete cascade
          ├─ content_hash                        decides changed or unchanged
          1 ──< Symbol (ccctx_symbols, unchanged) on delete cascade
                  └─ commit_sha                  the revision this file was last read at

Change set (in memory, one per run)
  built from: git candidates + stored path→hash map (read under the repo row lock)
  drives:     which File rows are deleted, which are inserted
  reported:   Summary counts and the JSON log record
```

Deleting a file row removes its symbols through the existing cascade. The hybrid index syncs on commit, so removed symbols leave it and only inserted ones are embedded.

## Repository (`ccctx_repos`, reshaped)

Existing columns (`id`, `name`, `path`, `registered_at`) and `ccctx_repos_name_ck` are unchanged.

| Field | Type | Rule |
|---|---|---|
| `indexed_commit` | `varchar2(64)`, nullable | The HEAD commit of the last successful ingest (FR-001). Constraint `ccctx_repos_indexed_ck`: `check (indexed_commit is null or regexp_like(indexed_commit, '^[0-9a-f]{40}([0-9a-f]{24})?$'))`. This is the same hex rule as `ccctx_symbols.commit_sha`, so SHA-1 and SHA-256 repositories both fit. NULL means never indexed, or indexed before this step. |
| `indexed_dirty` | `boolean`, nullable | True when the last ingest read uncommitted edits to tracked files (the existing `dirty` flag). Untracked files need no flag, because they are candidates on every run. A true value makes the next run treat every listed file as a candidate. NULL when `indexed_commit` is NULL. |
| `indexed_at` | `timestamp with time zone`, nullable | When the last successful ingest committed. NULL when `indexed_commit` is NULL. |

Write rules:

- `_store` sets all three columns in the transaction that writes the index, just before it commits.
- A failed or rolled-back ingest leaves all three at their previous values (FR-007).
- An up-to-date run writes none of them.
- A run where HEAD moved but no indexed file changed updates only these three columns.
- The three columns are set together. One is never written without the others.

## Migration 5 (`repo indexed revision`)

Ordered and re-runnable. Each statement tolerates its "already exists" error.

1. `alter table ccctx_repos add (indexed_commit varchar2(64), indexed_dirty boolean, indexed_at timestamp with time zone)`
2. `alter table ccctx_repos add constraint ccctx_repos_indexed_ck check (indexed_commit is null or regexp_like(indexed_commit, '^[0-9a-f]{40}([0-9a-f]{24})?$'))`

The columns are nullable, so existing rows need no backfill. Every repository ingested before this step reads NULL and gets one full rebuild on its next ingest (FR-010).

## Indexed file (`ccctx_files`, unchanged)

`path`, `language` and `content_hash` are as today. `content_hash` is the sha256 of the file content. It, and never a timestamp, decides whether a file changed. A changed file is updated in place: symbols whose name, kind and content hash still occur keep their row and move to their new lines; the others are deleted and the new ones inserted.

## Symbol (`ccctx_symbols`, unchanged)

Rows of unchanged files are not touched. Their `commit_sha` stays at the revision they were last read at, so it can be older than `ccctx_repos.indexed_commit`. Equality with a full rebuild (FR-006, SC-005) is checked on every symbol field except `commit_sha`.

## Change set (in memory)

One per run, never stored. Built inside the ingest transaction, after the repository row is locked.

Candidates are the union of:

- `git diff --name-only -z --no-renames <indexed_commit> --`, the tracked files that differ from the last indexed commit.
- `git ls-files -z --others --exclude-standard`, the untracked files.
- Stored paths no longer listed by `git ls-files --cached --others --exclude-standard`.
- Every listed file, when `indexed_dirty` is true.

Each candidate passes through the existing skip rules in `discover`, then is classified.

| Class | Condition | Action |
|---|---|---|
| `added` | Not stored, and not skipped. | Parse, insert file and symbols. |
| `changed` | Stored, not skipped, and its sha256 differs from `content_hash`. | Update the file row; keep unchanged symbols at their new lines, delete stale ones, insert new ones. |
| `removed` | Stored, and now gone, ignored, or skipped. | Delete the file row. |
| `unchanged` | Stored, and its sha256 equals `content_hash`. | Nothing. |

Validation rules:

- Every candidate lands in exactly one class.
- A renamed file is `removed` at its old path and `added` at its new path.
- A file that changed and changed back is `unchanged`.
- A dirty edit that the last ingest already indexed is `unchanged`.
- A file that newly matches a skip rule is `removed` (FR-005).
- The stored path→hash map is read under the repository row lock, so the change set cannot go stale mid-run.
- `unchanged` counts every stored file that is not added, changed or removed, not only the candidates.

## Summary (in memory, extended)

Existing fields are unchanged. The new fields have defaults, so existing constructors keep working.

| Field | Type | Rule |
|---|---|---|
| `mode` | `str` | One of `full`, `incremental`, `current`. |
| `added` | `int` | Files in the `added` class. |
| `changed` | `int` | Files in the `changed` class. |
| `removed` | `int` | Files in the `removed` class. |
| `unchanged` | `int` | Stored files left alone. |
| `note` | `str` or `None` | Why a full rebuild ran without `--full`. Printed to stderr. |

`skipped` and the fallback counts cover only the files this run read. The JSON log record adds `mode` and the four counts, and is written for every run, including `current` (FR-012).

## Repository index state (state transitions)

The mode is chosen once per run, after the repository row is locked.

```text
--full given                                   ──> full
indexed_commit NULL, no files stored           ──> full                (first ingest, no note)
indexed_commit NULL, files stored              ──> full + note         (indexed before this step)
indexed_commit not found by git rev-parse      ──> full + note         (history rewritten, clone replaced)
HEAD = indexed_commit and change set empty     ──> current             (no writes, rollback releases the lock)
otherwise                                      ──> incremental
```

The commit check is `git rev-parse --verify --quiet <indexed_commit>^{commit}`.

Outcomes:

- `full` deletes the repository's file rows, which cascades to symbols, inserts everything, sets the revision columns, and commits.
- `incremental` deletes changed and removed file rows, inserts added and changed files, sets the revision columns, and commits.
- `current` writes nothing. The CLI prints the up-to-date line with the revision and says `--full` re-indexes anyway (FR-002, FR-011).
- Any failure rolls back. The index and the revision columns stay as they were (FR-007).
- A concurrent ingest of the same repository hits the row lock and is refused with ORA-00054, as today.
