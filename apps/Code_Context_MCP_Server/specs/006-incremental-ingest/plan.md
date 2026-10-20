# Implementation Plan: Incremental Re-indexing

**Spec**: [incremental-ingest.spec.md](./incremental-ingest.spec.md) | **Research**: [research.md](./research.md)

## Summary

Each repository records the revision it was last indexed at, plus whether that tree was dirty. On re-ingest, git names the candidate files: what differs from the last indexed commit, the untracked files, and stored paths that are gone. Each candidate's content hash then decides whether it was added, changed, removed or left alone. Only added and changed files are parsed and inserted, and changed and removed file rows are deleted, which cascades to their symbols. The hybrid index syncs on commit, so it embeds only the new rows. An empty change set at the same revision prints "already up to date" and writes nothing. `--full`, an unknown revision, or a revision that no longer exists runs today's full replace.

## Project Structure

```text
src/golestan_code_mcp/
  schema.py     migration 5: indexed_commit, indexed_dirty, indexed_at on ccctx_repos
  ingest.py     change set, incremental _store, full flag, Summary counts, log fields
  cli.py        --full flag, incremental summary lines, up-to-date line, stderr notes
tests/
  test_schema.py   migration 5 columns and the revision check constraint
  test_ingest.py   up to date, add/edit/rename/delete/skip/untracked, equality with --full, failure, fallbacks
  test_cli.py      --full, incremental summary, up-to-date line
README.md          "Ingesting a codebase": incremental runs, --full, when to use it
```

**Structure Decision**: everything stays in the three existing modules. The change set is one function in `ingest.py`, beside `discover`, which it reuses for the skip rules.

## Constitution Check

| Principle | Assessment |
|---|---|
| I. Database-Native Intelligence | PASS. Embedding stays in the database; the hybrid index embeds only inserted rows. |
| II. Structure-Aware Ingestion | PASS. This is the principle's "re-ingestion MUST be incremental and idempotent" rule: same hash, no re-embed, and deleted code removes its chunks. Chunking is unchanged. |
| III. MCP as the Single Interface | PASS. No tool contract changes. Ingest stays a CLI admin command on the core library. |
| IV. Hybrid, Explainable Retrieval | PASS. Ranking is untouched. Deleted symbols can no longer reach results. |
| V. Self-Improvement with Provenance | PASS. No notes yet. Symbols keep the revision they were read at, which notes will later hash against. |
| VI. Measured Quality (Test-First) | PASS. Integration tests against the real database come first. The equality-with-full test covers each change kind (SC-005). |
| VII. Safety & Simplicity | PASS. The only new git calls are `diff --name-only` and `rev-parse --verify`, both read-only through `GIT_SAFE`. There is no new module and no new dependency. |

Re-checked after design: unchanged.

## Verifying the performance targets

- **SC-001**: time `ccctx ingest flask` twice. The second run must print the up-to-date line within 3 seconds.
- **SC-002**: compare a `git checkout HEAD~20` re-ingest against `ccctx ingest flask --full` on the same tree. 40 of flask's 236 files changed over those 20 commits, so expect roughly a sixth of the full time and well under half.
  - The spec's "under 10% of files" may not hold for this pair of revisions: 40 of 236 is 17%. Implement measures it and reports the real ratio. The binding test is "a handful rather than the whole repository, and noticeably faster".
- **SC-003**: run the deletion test exactly as the request states, then restore the file with `git checkout`.
