# Feature Specification: Incremental Re-indexing

**Feature directory**: `specs/006-incremental-ingest`
**Created**: 2026-10-11
**Status**: Draft

Today every ingest throws the repository's index away and rebuilds it. On a large repository that is slow enough that people stop re-indexing, and a stale index is worse than none because nothing tells the reader when to trust it. This step makes a re-ingest do only the work the changes require, removes everything that belongs to deleted code, and keeps a full rebuild as an escape hatch.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nothing changed, nothing done (Priority: P1)

A developer re-runs ingest on a repository that has not changed since it was last indexed. The tool says the repository is already up to date, names the revision it was indexed at, and does no parsing, embedding or storing.

**Why this priority**: it is the cheapest win and the base the other stories build on: the tool has to remember which revision it indexed before it can compare anything.

**Independent Test**: ingest a repository, ingest it again without touching it, and confirm the second run reports "already up to date", finishes in about the time a database round trip takes, and leaves every stored file and symbol exactly as it was.

**Acceptance Scenarios**:

1. **Given** a repository indexed at its current revision with no edits since, **When** the developer runs `ccctx ingest flask`, **Then** the tool reports the repository is already up to date at that revision and changes nothing.
2. **Given** a repository that has never been indexed, **When** the developer runs ingest, **Then** it is indexed in full and its revision is recorded.
3. **Given** a repository whose revision is unchanged but whose working tree has uncommitted edits that were not indexed, **When** the developer runs ingest, **Then** it is not reported as up to date and those edits are indexed.

---

### User Story 2 - Only changed files are re-indexed (Priority: P1)

The developer moves the repository to another revision, or edits files, and re-runs ingest. The tool works out which files were added, changed, renamed or removed since the last indexed revision. It re-parses and re-embeds only the added, changed and renamed files, removes what belongs to removed ones, and leaves everything else untouched. The summary says how many files were added, changed, removed and left alone.

**Why this priority**: this is the point of the step. Re-indexing a handful of files instead of thousands is what keeps the index current.

**Independent Test**: ingest flask, check out `HEAD~20`, ingest again, and confirm the summary reports a handful of changed files, the run is noticeably faster than the first ingest, and the stored index matches what a full ingest at `HEAD~20` would produce.

**Acceptance Scenarios**:

1. **Given** flask indexed at its latest revision, **When** the developer checks out `HEAD~20` and runs `ccctx ingest flask`, **Then** the summary lists the counts of added, changed, removed and unchanged files, the changed count is a small fraction of the repository, and only those files are re-processed.
2. **Given** a file renamed since the last ingest, **When** the developer re-ingests, **Then** its symbols are found under the new path and none remain under the old path.
3. **Given** a re-ingest that fails part way, **When** the developer searches, **Then** the index is exactly as it was before the failed run and the recorded revision has not moved.

---

### User Story 3 - Deleted code leaves the index (Priority: P1)

The developer deletes a file and re-ingests. Every symbol and chunk that came from the file is removed, so no search result can point at code that no longer exists.

**Why this priority**: an orphaned chunk is poison. It points at code that is gone, and nothing in the result warns the reader.

**Independent Test**: delete `src/flask/json/tag.py`, re-ingest, search for "json tag serialisation" in flask, and confirm no result points at the deleted file. Restore the file with git afterwards.

**Acceptance Scenarios**:

1. **Given** flask is indexed and `src/flask/json/tag.py` is then deleted from the working tree, **When** the developer runs `ccctx ingest flask` and then `ccctx search "json tag serialisation" --repo flask`, **Then** no result points at `src/flask/json/tag.py`.
2. **Given** the deleted file is restored with git, **When** the developer re-ingests, **Then** its symbols are back and searchable.
3. **Given** a file that newly matches a skip rule (it became too large, binary, ignored or vendored), **When** the developer re-ingests, **Then** its old symbols are removed as if it had been deleted.

---

### User Story 4 - Full rebuild on demand (Priority: P2)

The developer runs ingest with `--full`. The tool discards the repository's whole index and rebuilds it from the working tree, as the first ingest did. This is the escape hatch after changing chunking rules or skip settings, and it is also how the developer insists on re-indexing a repository that is already up to date.

**Why this priority**: incremental indexing assumes the rules that produced the stored index have not changed. When they have, only a rebuild is correct.

**Independent Test**: run `ccctx ingest flask --full` on an up-to-date repository and confirm it re-indexes every file, with file and symbol counts equal to the original full ingest at the same revision.

**Acceptance Scenarios**:

1. **Given** flask is up to date, **When** the developer runs `ccctx ingest flask --full`, **Then** every file is re-processed and the summary's file and symbol counts match the original ingest at that revision.
2. **Given** an up-to-date repository, **When** ingest reports it is already up to date, **Then** the message tells the developer `--full` re-indexes it anyway.

---

### Edge Cases

- The last indexed revision no longer exists in the repository (history rewritten, or the clone was replaced): the tool says so and rebuilds the repository in full.
- Symbols stored before this step have no recorded revision: the first ingest after upgrading is a full rebuild.
- A file is renamed and also edited: it is treated as removed from its old path and added at its new path.
- A file changes and changes back between ingests: its content is identical to what was indexed, so it is left alone.
- An untracked file is created since the last ingest: it is indexed, as the first ingest would have. A file that became ignored is removed.
- A skip setting (size limit, vendor directories) changes between ingests: files the new setting would include or exclude are only picked up when they change, or by `--full`. The README says to use `--full` after changing a setting.
- Two ingests of the same repository at once: the second is refused, as today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST record, for each repository, the revision it was last successfully indexed at, and only once that ingest has fully committed.
- **FR-002**: When the repository is at the recorded revision and its working tree has nothing that differs from what was indexed, ingest MUST report that the repository is already up to date, name the revision, and change nothing.
- **FR-003**: Otherwise, ingest MUST determine the files added, changed, renamed and removed since the last indexed state, comparing the working tree against the last indexed revision, including uncommitted edits and untracked files.
- **FR-004**: Ingest MUST re-parse and re-embed only added, changed and renamed files, and MUST NOT rewrite the stored symbols of files whose content is unchanged.
- **FR-005**: Ingest MUST remove every stored file, symbol and chunk belonging to a path that was removed, renamed away, or now falls under a skip rule.
- **FR-006**: After an incremental ingest, the stored index MUST contain the same files and symbols a full ingest of the same working tree would produce.
- **FR-007**: An incremental ingest MUST apply all of its changes in one transaction, so a failure leaves the previous index and the previous recorded revision in place.
- **FR-008**: The ingest summary MUST report how many files were added, changed, removed and left unchanged, alongside the existing totals and timing.
- **FR-009**: `ccctx ingest <name> --full` MUST discard the repository's index and rebuild it from the working tree, whether or not the repository is up to date.
- **FR-010**: When the last indexed revision is unknown or no longer exists in the repository, ingest MUST say so and rebuild in full.
- **FR-011**: The "already up to date" message MUST tell the developer that `--full` re-indexes anyway.
- **FR-012**: Ingest MUST keep the existing guarantees: git used read-only, indexed code never executed, concurrent ingests of one repository refused, and the structured log record written for every run, including up-to-date runs.

### Key Entities

- **Repository**: gains the revision it was last indexed at, and when.
- **Indexed file**: path, language and content fingerprint, as today. The fingerprint is what decides whether a file changed.
- **Change set**: the added, changed, removed and unchanged files for one ingest run. Not stored; reported in the summary.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Re-ingesting flask with nothing changed reports "already up to date", stores nothing, and finishes in under 3 seconds.
- **SC-002**: After checking out flask's `HEAD~20`, re-ingest re-processes fewer than 10% of flask's files and takes less than half the time of a full flask ingest.
- **SC-003**: After deleting `src/flask/json/tag.py` and re-ingesting, zero stored symbols and zero search results point at that path.
- **SC-004**: `ccctx ingest flask --full` reports file and symbol counts equal to the original full ingest at the same revision.
- **SC-005**: For every tested change (add, edit, rename, delete, newly skipped file, untracked file), the incremental index equals a full rebuild of the same tree, compared file by file and symbol by symbol.
- **SC-006**: A re-ingest forced to fail part way leaves the index and recorded revision identical to before.

## Assumptions

- "Insisting" on re-indexing an up-to-date repository means `--full`. A second flag would do the same thing.
- A symbol keeps the revision it was last read at. Unchanged files are not rewritten just to stamp the new revision, since their code is identical.
- Content fingerprints, not timestamps, decide whether a file changed, so touching a file without editing it costs nothing.
- Changes to chunking rules or skip settings are not detected automatically. `--full` is the documented answer.

## Verbatim Constraints

- `ccctx ingest flask`
- `ccctx ingest flask --full`
- `--full`
- `ccctx search "json tag serialisation" --repo flask`
- `src/flask/json/tag.py`
