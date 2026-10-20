# Contract: CLI changes (`ccctx wiki`, `ccctx ingest`, `ccctx search`)

Extends `specs/008-mcp-tools/contracts/cli.md`. Every other command is unchanged. Exit codes are the existing ones: `0` ok, `1` refused input, `2` database down. Every refusal is one `error: <reason>` line on standard error.

## Names

- A page is one directory of a repository whose own files hold at least 10 named definitions (`kind <> 'chunk'`). Subdirectories count separately. Line windows never count and are never cited.
- Its name is the directory path with one leading `src/` removed: `src/flask/json` is `flask/json`, `binding` stays `binding`. The root directory (`.`) is named after the repository.
- When two qualifying directories of one repository would get the same name (`src/x` and `x`), both are named by their full path.
- `PAGE` arguments match a page name exactly, case-sensitive. Without `--repo` a name found in more than one repository is refused (see Failures).

## `ccctx wiki build`

```text
ccctx wiki build [--repo NAME]
```

- Compiles one page per qualifying directory of `NAME`, or of every indexed repository (at least one file) when `--repo` is absent, in repository-name order.
- Idempotent (research R11): upserts by `(repo, directory)`, rewrites text only when it changed, replaces the citations, deletes pages of directories that no longer qualify, sets every page `fresh`, and sets the repository's `wiki_at` if unset. Only `compiled_at` moves between two builds with no change in between.
- Needs no search model. When the model is loaded and the page index is missing, it creates the index. When the model is not loaded, it prints `note: wiki pages are not searchable until you run `ccctx model load`` to standard error and still succeeds.

Standard output, one line per repository:

```text
flask: 7 pages (7 added, 0 updated, 0 removed) in 2.4s
gin: 7 pages (7 added, 0 updated, 0 removed) in 1.9s
```

`updated` counts pages whose text changed. A repository with no qualifying directory prints `flask: 0 pages (0 added, 0 updated, 0 removed) in 0.1s` and still counts as having a wiki.

## `ccctx wiki list`

```text
ccctx wiki list [--repo NAME]
```

```text
NAME                     REPO   STATE  SYMBOLS  COMPILED             LAST STALE
examples/tutorial/flaskr flask  fresh       24  2026-10-11 14:02:33  -
flask/json               flask  fresh       62  2026-10-11 14:20:05  dumps changed (5f2c1a9e04b7 -> 9e0d3c1b2a47)
```

| Column | Meaning |
|---|---|
| `NAME` | Page name. |
| `REPO` | Repository name. |
| `STATE` | `fresh` or `stale`. |
| `SYMBOLS` | Named definitions in the directory's own files. Right-aligned. |
| `COMPILED` | `compiled_at` in UTC, `YYYY-MM-DD HH:MM:SS`. |
| `LAST STALE` | `stale_reason`: what last made the page stale, `-` if it never was. Kept after a recompile. |

- Ordered by repository name, then page name.
- No pages: prints `no wiki pages`, exit `0`.

## `ccctx wiki show`

```text
ccctx wiki show PAGE [--repo NAME]
```

Prints a header line, the page text exactly as stored, then a `## Sources` section rendered at read time from the citations. The stored text holds no path and no line number; every location below comes from the citation's foreign key.

```text
flask/json (flask, src/flask/json) fresh, compiled 2026-10-11 14:02:33 by ccctx-wiki/1

# flask/json

`flask/json` is a Python package of 3 files and 62 definitions: 47 methods, 9 functions and 6 classes.
...

## Sources
- `JSONProvider` (class, key) src/flask/json/provider.py:17-107
- `jsonify` (function, key) src/flask/json/__init__.py:138-170
- `src/flask/json/tag.py` (file, file)
- `get_root_path` (function, calls) gone
```

- Header: `<name> (<repo>, <directory>) <state>, compiled <compiled_at> by <compiler>`. A stale page adds a second line `stale: <stale_reason>`.
- One Sources line per citation, in citation order (role `key`, `file`, `depends`, `uses`, `calls`, then name): `` `<name>` (<kind>, <role>) <path>:<start>-<end> ``. A file citation has no line range. A citation whose record is gone ends in `gone`.

## `ccctx wiki citations`

```text
ccctx wiki citations PAGE [--repo NAME]
```

```text
NAME          KIND      ROLE  REPO   PATH                          LINES    COMPILED      CURRENT
JSONProvider  class     key   flask  src/flask/json/provider.py   17-107   5f2c1a9e04b7  5f2c1a9e04b7
tag.py        file      file  flask  src/flask/json/tag.py         -        5f2c1a9e04b7  5f2c1a9e04b7
dumps         function  key   flask  -                             -        5f2c1a9e04b7  gone
```

| Column | Meaning |
|---|---|
| `NAME` | The cited symbol's qualified name, or the file's base name. |
| `KIND` | The symbol's kind, or `file`. |
| `ROLE` | `key`, `file`, `depends`, `uses` or `calls` (research R6). |
| `REPO`, `PATH` | Read through the citation's key. `-` when the record is gone. |
| `LINES` | `<start>-<end>` of a symbol, read through the key. `-` for a file or a gone record. |
| `COMPILED` | First 12 characters of the commit recorded at compile time. |
| `CURRENT` | First 12 characters of the record's current commit, or `gone`. |

Same order as the Sources section of `wiki show`. A page always has at least one citation (its files).

## Failures (all wiki commands)

| Cause | stderr | Exit |
|---|---|---|
| Unknown repository | `error: no repository named '<repo>'` | 1 |
| Repository registered but not indexed | `error: repository '<repo>' is not indexed yet; run `ccctx ingest <repo>`` | 1 |
| `wiki build` with no `--repo` and nothing indexed | `error: no indexed repositories` | 1 |
| Unknown page | `error: no wiki page named '<page>'` (with `--repo`: `... in '<repo>'`) | 1 |
| Name in more than one repository, no `--repo` | `error: wiki page '<page>' is in more than one repository: <repo>, <repo>; pass --repo` | 1 |
| Database down | the existing `error: database unreachable: ...` | 2 |

Repositories in the ambiguity message are in name order.

## `ccctx ingest` summary

When the repository has a wiki (`wiki_at` set) and the ingestion was not `current`, the summary gains wiki lines after the existing ones, in the same `{label:<9}` layout as the incremental summary:

```text
Changed           1 files (0 added, 1 changed, 0 removed)
Unchanged        23 files
Skipped           4 files (4 ignored)
Indexed          62 symbols in 1.8s
Wiki      flask/json stale: dumps changed (5f2c1a9e04b7 -> 9e0d3c1b2a47), recompiled
Wiki      1 stale, 1 recompiled, 0 added, 0 removed
```

- One `Wiki` line per page that went stale, in page-name order: `<page> stale: <stale_reason>, recompiled` or `, not recompiled`.
- `stale_reason` is `<name> changed (<old commit 12> -> <new commit 12>)`, `<name> was re-indexed` or `<name> is gone`, naming the first stale citation. A rewritten symbol (ingestion deletes an edited one and inserts it again) is matched by its name: `changed` with its new commit, or `was re-indexed` when the commit is the same, as after a full re-ingestion.
- Then one counts line. It is printed even when every count is 0.
- If the recompile fails, the pages stay stale, the per-page lines end in `not recompiled`, standard error gets `warning: wiki not recompiled: <reason>`, and the exit code is still `0` (FR-012).
- A repository without a wiki prints no `Wiki` lines and gets no pages.

## `ccctx search`

Output columns are unchanged: `RANK SCORE KEYWORD SEMANTIC REPO KIND NAME PATH LINES`. A page hit has:

| Column | Value |
|---|---|
| `KIND` | `page`, or `page (stale)` for a stale page |
| `NAME` | Page name |
| `PATH` | The page's directory |
| `LINES` | `-` |

- `--repo` and `--language` apply to pages with the rules used for symbols. A page's language is the most common language of its symbols.
- Page hits are placed by semantic similarity (research R8) and always after the definitions block of an exact identifier.
- When the page index does not exist, search returns symbols only, without a note.

## Logging

`wiki build` and the ingest recompile each write one record to standard error per repository, never page text or source:

```json
{"event": "wiki", "repo": "flask", "built": 7, "stale": 0, "recompiled": 0, "removed": 0, "ms": 2410}
```

`built` counts pages compiled (added or recompiled), `stale` pages marked stale by the ingestion (0 for `wiki build`).

## Version

`pyproject.toml` `version` and `golestan_code_mcp.__version__` are `1.1.0`.
