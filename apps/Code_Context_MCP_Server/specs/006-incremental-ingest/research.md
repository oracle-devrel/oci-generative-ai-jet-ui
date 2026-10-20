# Research: Incremental Re-indexing

## Where the last indexed revision lives

- **Decision**: migration 5 adds three nullable columns to `ccctx_repos`:
  - `indexed_commit varchar2(64)`, with the same hex check as `ccctx_symbols.commit_sha`
  - `indexed_dirty boolean`
  - `indexed_at timestamp with time zone`

  `_store` sets them in the transaction that writes the index, just before it commits.
- **Rationale**: the repository row is already the one `_store` locks, so the revision moves only if the index commits (FR-001, FR-007). Repositories ingested before this step read NULL and get one full rebuild (FR-010).
- **Alternatives considered**: deriving the revision from `max(commit_sha)` over symbols does not work once unchanged symbols keep older revisions. A separate runs table is history nobody reads yet.

## Working out the change set

- **Decision**: git names the candidate paths and the content hash decides. Candidates are the union of:
  - `git diff --name-only -z --no-renames <indexed_commit> --`: tracked files whose working tree differs from the last indexed commit, staged or not.
  - `git ls-files -z --others --exclude-standard`: untracked files, which git diff never lists.
  - stored paths that are no longer listed by `git ls-files --cached --others --exclude-standard`. These are deleted, renamed away, or newly ignored.
  - every listed file, when `indexed_dirty` is true.

  Each candidate goes through the existing skip rules. Its sha256 is then compared with `ccctx_files.content_hash`:
  - not stored: added
  - different hash: changed
  - stored, but now gone or skipped: removed
  - same hash: unchanged
- **Rationale**: this is the comparison the request asks for, and it reads only what changed, which matters on a large repository. The hash keeps the result exact:
  - A dirty edit that was already indexed comes out unchanged.
  - A file that changed and changed back also comes out unchanged.
  - A file that now hits a skip rule (grown too large, turned binary) is removed, not kept.

  `indexed_dirty` covers the one case git cannot see. If the last ingest indexed an uncommitted edit that was later reverted, git diff against the commit is empty, yet the stored content is stale. Re-checking every listed file after a dirty ingest is the simple, correct answer.
- **Alternatives considered**:
  - Hashing every file on every run is just as exact, but reads the whole tree each time.
  - git diff alone misses untracked files and that reverted edit, and it re-processes dirty edits already indexed.
  - Rename detection (`-M`) buys nothing, because the path is part of each symbol's search text, so a renamed file is re-embedded anyway. `--no-renames` also pins behavior against a user's `diff.renames` setting.

## Up to date

- **Decision**: a run is up to date when HEAD equals `indexed_commit` and the change set is empty. It writes nothing, rolls back to release its lock, logs one JSON record with `"mode": "current"`, and the CLI prints the up-to-date line.

  When HEAD moved but no indexed file changed, ingest only moves `indexed_commit`.
- **Rationale**: one rule, no separate fast path. With a clean tree at the same revision, git diff and the untracked list are empty, so nothing is read and the run costs a few git calls and two queries (SC-001).

## When to rebuild in full

- **Decision**: full when `--full` is given, when `indexed_commit` is NULL, or when `git rev-parse --verify --quiet <sha>^{commit}` fails.
  - A NULL revision on a repository that already has files stored gets a stderr note.
  - So does a missing commit.
  - A first ingest gets no note.

  Full is today's path: delete the repository's files, which cascades to symbols, then insert everything.
- **Rationale**: without a known base commit there is nothing safe to diff against.

## The write

- **Decision**: one transaction.
  1. Lock the repository row (`for update nowait`, ORA-00054 still means "another ingest").
  2. Read `indexed_commit`, `indexed_dirty` and the stored path→hash map under that lock.
  3. Parse only added and changed files.
  4. `delete from ccctx_files where repo_id = :r and path = :p` for removed paths, using executemany. The `on delete cascade` foreign key removes their symbols.
  5. Insert added files and their symbols. Update each changed file row in place; keep its symbols whose (name, kind, content hash) still occur, updating only their lines and `commit_sha`; delete the rest and insert the new ones.
  6. Update the revision columns, then commit.
- **Rationale**: the stored hashes must be read under the lock, or a concurrent ingest that commits in between makes the change set stale. Measured on flask: the 40 files that differ between `main` and `HEAD~20` hold 658 symbols, but only 140 of them changed. Re-inserting whole files embedded all 658 and took 78% of a full rebuild, so changed files keep their unchanged symbols. The hybrid index syncs on commit, so deleted symbols leave it and only inserted ones are embedded. Search also maps index rowids back to live rows, so a deleted symbol cannot surface even in principle (FR-005).
- **Alternatives considered**: updating changed file rows in place keeps file ids stable, but nothing references file ids outside this table.

## Unchanged symbols keep their revision

- **Decision**: rows of unchanged files are not touched, so their `commit_sha` stays at the revision they were last read at.
- **Rationale**: the request says to leave correct rows alone. Rewriting `commit_sha` would be harmless for the index, but it is still writes the change does not need. FR-006 equality is therefore checked on everything except `commit_sha`.

## Summary and log

- **Decision**: `Summary` gains `mode` (`full`, `incremental` or `current`), the counts `added`, `changed`, `removed` and `unchanged`, and an optional `note`. The fields are defaulted, so existing constructors keep working.
  - An incremental summary prints `Changed` and `Unchanged` lines before `Skipped` and `Indexed`.
  - `Skipped` and `Fallback` count only the files this run read.
  - The JSON record adds `mode` and the four counts.
- **Rationale**: FR-008 and the constitution's logging rule ("chunks added/updated/removed"). Full runs print exactly what they print today, so `--full` counts compare directly with the original ingest (SC-004).

## Git stays read-only

- **Decision**: the only new git calls are `diff --name-only` and `rev-parse --verify`. Both run through `git()` with `GIT_SAFE`, and `test_git_helper_is_read_only` gains them.
- **Rationale**: `git diff` against the working tree can refresh the index stat cache. `--no-optional-locks`, already in `GIT_SAFE`, stops that write.
