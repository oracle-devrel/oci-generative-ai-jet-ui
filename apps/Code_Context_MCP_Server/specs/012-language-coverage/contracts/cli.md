# Contract: CLI changes for language coverage

Extends `specs/006-incremental-ingest/contracts/cli.md` and `specs/005-hybrid-search/contracts/cli.md`. Every rule
there still applies. No command, flag or exit code is added or removed.

## `ccctx ingest NAME` (incremental)

A new `Reparsed` line comes after `Indexed` and before `Fallback`. It is printed only when at least one unchanged file
was read again because its language gained rules (research R10):

```text
Changed    46 files (0 added, 46 changed, 0 removed)
Unchanged  51 files
Skipped    33 files (33 vendored)
Indexed   412 symbols in 7.9s
Reparsed   46 files whose language is now understood (46 csharp)
Fallback    1 files as line windows (0 no grammar, 1 parse errors)
```

- **Counts**: files re-read for this reason count in `Changed` as changed files, and `Reparsed` repeats them.
- **Breakdown**: the parenthesis lists each language with its count, the largest count first, then by name.
- **Not "up to date"**: a run whose only work is such files is still an incremental run, never `already up to date`.
- **Full runs** (`--full`, or a first ingest) never print `Reparsed`: every file is read anyway.
- **The ingest log record** gains `"reparsed": {"csharp": 46}`, which is `{}` when there are none.

## `ccctx search --language` and `ccctx stats --by-language`

`--language` accepts the new values. The error for an unknown value lists every valid one, sorted:

```text
error: unknown language 'cobol'; valid languages: batch, c, cpp, csharp, css, go, html, ini, java, javascript, json, kotlin, markdown, php, proto, python, rst, ruby, rust, shell, sql, swift, text, toml, tsx, typescript, yaml
```

`stats --by-language` shows the new values in its `LANGUAGE` column. Its shape is unchanged.

## `ccctx symbols --kind`

The choices are unchanged (`function`, `method`, `class`, `type`, `interface`, `chunk`). The new languages' constructs
map onto them (research R5).
