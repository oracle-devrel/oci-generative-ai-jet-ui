# Contract: `ccctx ingest`, `ccctx symbols`, `ccctx stats`

Extends the step 2 CLI contract (`specs/002-repo-registry/contracts/cli.md`). Exit codes, `error: <reason>` on stderr, the no-password rule and the migrate-first pre-step are unchanged. `repo add`, `repo list` and `db migrate` output is unchanged.

## Settings

Read from `.env` and the environment. Not command-line flags.

| Variable | Default | Meaning |
|---|---|---|
| `CCCTX_MAX_FILE_BYTES` | `1048576` | Files larger than this are skipped as `too large`. |
| `CCCTX_VENDOR_DIRS` | `vendor,node_modules,third_party` | Comma-separated directory names. A file with any path component in this list is skipped as `vendored`. |

## `ccctx ingest <name>`

Examples: `ccctx ingest flask`, `ccctx ingest gin`.

Indexes the working tree of the registered repository `<name>`, replacing its previous files and symbols in one transaction. Reads files only; git runs as `git -c core.fsmonitor=false -c core.hooksPath=/dev/null --no-optional-locks -C <repo> …` with only `rev-parse`, `ls-files` and `status --porcelain`.

Success, exit `0`, stdout. Labels in this order: `Scanned`, `Skipped`, `Indexed`, then `Fallback` only when at least one file fell back:

```text
Scanned   214 files
Skipped    38 files (12 ignored, 24 binary, 2 too large)
Indexed  1,847 symbols in 9.2s
Fallback   17 files as line windows (15 no grammar, 2 parse errors)
```

- Numbers use thousands separators and are right-aligned to the widest number of the lines printed.
- `Skipped` lists only non-zero reasons, in the order `ignored`, `vendored`, `binary`, `too large`. With no skips the line is `Skipped 0 files`.
- `Indexed` time is elapsed seconds with one decimal.
- `Scanned` = indexed files + skipped files. `Indexed` symbol count = the repository's `SYMBOLS` in `ccctx repo list` afterwards (parsed symbols plus fallback chunks).

Skip reasons (first match wins, in this order of checks):

| Reason | Rule |
|---|---|
| `ignored` | Listed by `git ls-files --others --ignored --exclude-standard` (not read), or the path is a symbolic link. |
| `vendored` | A path component is in `CCCTX_VENDOR_DIRS`, even if committed. |
| `too large` | Size (`lstat`) over `CCCTX_MAX_FILE_BYTES`. |
| `binary` | Contains a NUL byte or is not strict UTF-8. |

`.git` is never listed or counted.

Dirty tree (tracked changes per `git status --porcelain --untracked-files=no`): ingest proceeds and stderr gets

```text
warning: <path> has uncommitted changes; indexed the working tree at <commit>
```

Structured log: one JSON line on stderr via logger `golestan_code_mcp.ingest`:

```json
{"event": "ingest", "repo": "flask", "commit": "<40 or 64 hex>", "dirty": false,
 "scanned": 214, "skipped": {"ignored": 12, "vendored": 0, "binary": 24, "too_large": 2},
 "files": 176, "symbols": 1847, "fallback": {"no_grammar": 15, "parse_error": 2},
 "duration_s": 9.2}
```

Refusals, nothing changed in the index:

| Cause | Exit | stderr |
|---|---|---|
| Name not registered | `1` | `error: no repository named '<name>'` |
| Registered directory missing | `1` | `error: <path> does not exist` |
| Not a git repository | `1` | `error: <path> is not a git repository; ingest requires one` |
| HEAD does not resolve (no commits) | `1` | `error: <path> has no commits` |
| Another ingest holds the repository (ORA-00054) | `1` | `error: another ingest of '<name>' is running` |
| Database unreachable or still starting | `2` | as step 2 (`error: database unreachable: …` / `error: database is still starting`), within a few seconds |
| Any failure mid-run | `1` or `2` | the cause; the transaction is rolled back and the previous index is kept |

## `ccctx symbols --repo <name> [--limit <n>] [--kind <kind>]`

Example: `ccctx symbols --repo flask --limit 5`.

- `--repo`: required, a registered name (else exit `1`, `error: no repository named '<name>'`).
- `--limit`: positive integer, default `20`.
- `--kind`: one of `function`, `method`, `class`, `type`, `interface`, `chunk`.

Exit `0`, stdout:

```text
NAME         KIND    LANGUAGE  PATH                          LINES
Flask        class   python    src/flask/app.py              108-1530
Flask.route  method  python    src/flask/sansio/scaffold.py  336-368
```

- Columns `NAME`, `KIND`, `LANGUAGE`, `PATH`, `LINES`, left-aligned, two-space separated. `LINES` is `<start>-<end>`, 1-based, inclusive.
- Order: parsed symbols (kind ≠ `chunk`) first, then fallback chunks; within each, by path then start line.
- No rows: `no symbols for '<name>'`.

## `ccctx stats --by-language [--repo <name>]`

Exit `0`, stdout:

```text
REPO   LANGUAGE  FILES  SYMBOLS  CHUNKS
flask  python       83     1402       0
flask  rst          61        0     312
gin    go          101      980       0
```

- `REPO`, `LANGUAGE` left-aligned; `FILES`, `SYMBOLS`, `CHUNKS` right-aligned. Sorted by repository, then language.
- `SYMBOLS` counts parsed symbols (kind ≠ `chunk`); `CHUNKS` counts fallback windows (kind = `chunk`).
- `--repo` filters to one repository. Nothing indexed: `no files indexed`.

## Chunking rules (observable through `symbols`)

| Language | Kinds stored | Method name |
|---|---|---|
| `python` | `function`, `class`, `method` | `<Class>.<method>`, nested class `Outer.Inner` |
| `go` | `function`, `method`, `type` (struct and other), `interface` | `<Receiver>.<method>`, `*` and type params stripped, e.g. `Engine.Use` |
| `javascript` | `function`, `class`, `method` (function declarations, generators, classes, arrow/function-expression declarators) | `<Class>.<method>` |

- Range covers the whole definition including decorators; `source` is exactly those whole lines.
- A class is stored and so is each of its methods. Nested functions and top-level statements are not stored separately.
- Fallback (no grammar, or any syntax error): kind `chunk`, `60`-line windows starting at lines 1, 51, 101, … (`10` lines of overlap), last window ending at the file's last line. Name `<file name>:<start>-<end>`. A 130-line file gives `1-60`, `51-110`, `101-130`. Language from the extension (`markdown`, `rst`, `yaml`, `toml`, `html`, `json`, `shell`, …), else `text`.
- An empty file is stored with no symbols.
