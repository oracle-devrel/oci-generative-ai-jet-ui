# Contract: `ccctx ingest <name> [--full]`

Extends the step 3 CLI contract (`specs/003-code-ingestion/contracts/cli.md`). Exit codes, `error: <reason>` on stderr, the settings, the skip rules, the chunking rules, `ccctx symbols` and `ccctx stats` are unchanged. Where step 3's contract and the code disagree, the code is authoritative; the dirty warning and the JSON log keys below are copied from the code.

## Modes

Each run is one of three modes. The mode is the `mode` field of the JSON log record.

| Mode | When | What it writes |
|---|---|---|
| `full` | `--full` is given, the repository has no recorded revision, or the recorded revision is no longer in the repository. | Deletes the repository's files, which cascades to their symbols, then inserts every file. This is the step 3 behavior. |
| `incremental` | A recorded revision exists and something differs from what was indexed. | Deletes the removed files, inserts the added files, updates changed files in place (keeping each symbol whose name, kind and code are unchanged, at its new lines), and leaves unchanged files alone. |
| `current` | HEAD equals the recorded revision and the change set is empty. | Nothing. The transaction is rolled back to release the lock. |

When HEAD moved but no indexed file changed, the run is `incremental` with zero changes and only moves the recorded revision.

## `ccctx ingest <name>`

Examples: `ccctx ingest flask`, `ccctx ingest gin`.

Indexes what changed in the working tree of the registered repository `<name>` since its last successful ingest. Files, symbols and the recorded revision change in one transaction.

### Full run

Exit `0`, stdout. Exactly the step 3 summary: `Scanned`, `Skipped`, `Indexed`, then `Fallback` only when at least one file fell back.

```text
Scanned   214 files
Skipped    38 files (12 ignored, 24 binary, 2 too large)
Indexed  1,847 symbols in 9.2s
Fallback   17 files as line windows (15 no grammar, 2 parse errors)
```

### Incremental run

Exit `0`, stdout. Labels in this order: `Changed`, `Unchanged`, `Skipped`, `Indexed`, then `Fallback` only when at least one file fell back.

```text
Changed     9 files (2 added, 6 changed, 1 removed)
Unchanged 227 files
Skipped     0 files
Indexed    84 symbols in 6.3s
Fallback    3 files as line windows (3 no grammar, 0 parse errors)
```

- Numbers use thousands separators and are right-aligned to the widest number of the lines printed.
- `Changed` = added + changed + removed. The parenthesis always lists all three counts.
- A rename counts as one removed file plus one added file.
- A file that now falls under a skip rule counts as removed.
- `Unchanged` = stored files this run left alone.
- `Skipped` counts only the files this run read. Its reasons are listed as in step 3.
- `Indexed` = symbols inserted this run, which the hybrid index embeds: all symbols of added files, and the new or edited symbols of changed files. Symbols that only moved are kept. The time is elapsed seconds with one decimal.
- `Fallback` counts only the files this run read.

### Up to date

Exit `0`, stdout, one line:

```text
<name> is already up to date at <first 12 hex of the revision>; run with --full to re-index anyway
```

For flask: `flask is already up to date at 0123456789ab; run with --full to re-index anyway`.

Nothing is parsed, embedded or stored.

### stderr notes before a fallback full run

Printed before the summary when a run without `--full` falls back to a full rebuild:

| Cause | stderr |
|---|---|
| No recorded revision, and the repository already has files stored | `note: no recorded revision for '<name>'; indexing in full` |
| The recorded revision is no longer in the repository | `note: last indexed revision <sha12> is no longer in the repository; indexing in full` |

`<sha12>` is the first 12 hex characters of the recorded revision. A first ingest, with nothing stored, gets no note. A `--full` run gets no note.

### Dirty tree

Unchanged from the code. When tracked files have uncommitted changes (`git status --porcelain --untracked-files=no`), ingest proceeds and stderr gets the line below. An up-to-date run does not print it, because it indexed nothing:

```text
warning: working tree has uncommitted changes; indexed the files as they are on disk
```

## `ccctx ingest <name> --full`

Example: `ccctx ingest flask --full`.

Discards the repository's index and rebuilds it from the working tree, whether or not it is up to date. Prints the full-run summary. On an unchanged tree, its file and symbol counts equal the original full ingest at the same revision.

## Git calls

Git still runs as `git -c core.fsmonitor=false -c core.hooksPath=/dev/null --no-optional-locks -C <repo> …`. The subcommands are `rev-parse`, `ls-files`, `status --porcelain`, and two new ones:

| Call | Purpose |
|---|---|
| `diff --name-only -z --no-renames <commit> --` | Tracked files whose working tree differs from the recorded commit, staged or not. |
| `rev-parse --verify --quiet <sha>^{commit}` | Checks that the recorded revision still exists. A failure means a full rebuild. |

Both are read-only. `--no-optional-locks` stops `git diff` from refreshing the index stat cache.

## Structured log

One JSON line on stderr via logger `golestan_code_mcp.ingest`, for every run, including an up-to-date run. The step 3 keys are kept as the code writes them. Five keys are added: `mode`, `added`, `changed`, `removed`, `unchanged`.

```json
{"event": "ingest", "repo": "flask", "commit": "<40 or 64 hex>", "dirty": false,
 "scanned": 6, "skipped": {}, "files": 6, "no_grammar": 3, "parse_errors": 0,
 "symbols": 84, "seconds": 6.3,
 "mode": "incremental", "added": 2, "changed": 6, "removed": 1, "unchanged": 227}
```

- `mode` is `"full"`, `"incremental"` or `"current"`.
- `skipped` holds only non-zero reasons, keyed `ignored`, `vendored`, `binary`, `too large`.
- In an incremental run, `scanned`, `skipped`, `files`, `no_grammar`, `parse_errors` and `symbols` cover only the files this run read.
- In a full run, `added` equals `files`, and `changed`, `removed` and `unchanged` are `0`.
- In a current run, `unchanged` is the number of stored files, and `files`, `symbols`, `added`, `changed` and `removed` are `0`. `scanned` and `skipped` cover any untracked files it read to confirm nothing changed.

## Refusals and failures

The step 3 refusals are unchanged, and each leaves the index untouched. A run that fails part way rolls back. The previous index and the previous recorded revision are kept.

## Deletion example

From the spec. Delete `src/flask/json/tag.py` from the working tree, then run:

```text
ccctx ingest flask
ccctx search "json tag serialisation" --repo flask
```

No search result points at `src/flask/json/tag.py`. Restoring the file with git and running `ccctx ingest flask` again makes its symbols searchable.

## Python surface (`golestan_code_mcp.ingest`)

| Name | Shape |
|---|---|
| `ingest(conn, name, env=None, full=False) -> Summary` | `full=True` is `--full`. |
| `Summary` | Gains `mode` (`"full"`, `"incremental"` or `"current"`), `added`, `changed`, `removed`, `unchanged` and `note` (the stderr note, or `None`). All are defaulted, so existing constructors keep working. |
