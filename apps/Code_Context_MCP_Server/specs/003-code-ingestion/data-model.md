# Data Model: Code Ingestion and Chunking

This step reshapes two stored entities from step 2 (`ccctx_files`, `ccctx_symbols`) and introduces three in-memory ones (`Chunk`, `Skip reason`, `Ingest summary`). `ccctx_repos` is unchanged and is only read and locked. Stored tables are in Oracle; in-memory entities live in `chunker` and `ingest` and are never persisted.

## Relationships

```text
Repository (ccctx_repos, unchanged)
  1 ──< File (ccctx_files)              on delete cascade
          1 ──< Symbol (ccctx_symbols)  on delete cascade

chunker.chunk(language, text) ──> Chunk[]  ──stored as──> Symbol
ingest run ──> Ingest summary  (printed + logged, not stored)
```

A symbol reaches its repository only through its file. Re-ingesting deletes a repository's files, and the cascade removes their symbols.

## File (`ccctx_files`, extended in meaning, no column change)

One indexed file of a repository's working tree. Only files that passed every skip rule are stored, including empty files.

| Field | Type | Null | Rule |
|---|---|---|---|
| `id` | `number` identity | no | Primary key. |
| `repo_id` | `number` | no | FK to `ccctx_repos.id`, cascade delete. |
| `path` | `varchar2(1024)` | no | Relative to the repository root, `/`-separated, as `git ls-files` prints it. Never under `.git` or a vendored directory, never a gitignored untracked path (SC-008). Unique per repository (`ccctx_files_path_uk`). |
| `language` | `varchar2(32)` | no | `python`, `go`, `javascript` for parsed languages; otherwise from the extension map (`markdown`, `rst`, `yaml`, `toml`, `html`, `json`, `shell`, …), else `text`. |
| `content_hash` | `varchar2(64)` | no | Hex SHA-256 of the file bytes (FR-010). |

Validation before insert (FR-002, research "Skip rules"): the file is listed by `git ls-files --cached --others --exclude-standard`; no path component is in `CCCTX_VENDOR_DIRS`; it is not a symlink; `lstat` size ≤ `CCCTX_MAX_FILE_BYTES` (default 1048576); its content has no NUL byte and decodes as strict UTF-8.

## Symbol (`ccctx_symbols`, extended by migration 2)

One chunk: either a parsed definition or a fallback line window.

| Field | Type | Null | Rule |
|---|---|---|---|
| `id` | `number` identity | no | Primary key. |
| `file_id` | `number` | no | FK to `ccctx_files.id`, cascade delete. |
| `name` | `varchar2(512)` | no | Parsed: the definition name; methods as `<Type>.<method>` (FR-006), nested classes as `Outer.Inner`, Go receivers with `*` and type parameters stripped (`Engine.Use`). Fallback: `<file name>:<start>-<end>`. |
| `kind` | `varchar2(16)` | no | `function`, `method`, `class`, `type`, `interface`, or `chunk` for fallback windows (FR-008). `module` stays allowed by the check but is not produced. |
| `start_line` | `number` | no | 1-based, `start_point.row + 1`. Includes decorators and an enclosing `export` (FR-005). |
| `end_line` | `number` | no | 1-based, `end_point.row + 1`; `end_line >= start_line` (`ccctx_symbols_lines_ck`). |
| `source` | `clob` | no | Exactly lines `start_line..end_line` of the file. |
| `content_hash` | `varchar2(64)` | no | Hex SHA-256 of `source` (FR-010). |
| `commit_sha` | `varchar2(64)` | no | **New.** Full `git rev-parse HEAD` at ingest; same value on every symbol of a run (FR-009, SC-006). Check `ccctx_symbols_commit_ck`: `^[0-9a-f]{40}([0-9a-f]{24})?$` (SHA-1 or SHA-256). |

What becomes a symbol (FR-004, research "Chunking with tree-sitter"):

| Language | Produced |
|---|---|
| Python | Module-level functions → `function`; classes → `class`; functions in a class body → `method`; nested classes recursed. |
| Go | `function_declaration` → `function`; `method_declaration` → `method`; each `type_spec` (grouped `type (…)` included) → `type` for struct/other, `interface` for interface. |
| JavaScript | Function and generator declarations, and `const`/`let`/`var` bound to an arrow or function expression → `function`; classes → `class`; their `method_definition`s → `method`. |

Not produced: nested functions (they stay inside their parent's range), top-level statements, imports, constants. A class and each of its methods are both stored, so method ranges nest inside the class range.

### Fallback windows

Used when the language has no grammar or the parse tree has any error (`has_error`); the whole file is windowed (FR-007). Window *k* (0-based) covers `50k+1 .. min(50k+60, last line)`; generation stops at the first window that reaches the last line. A file of ≤ 60 lines is one window; a 130-line file gives 1-60, 51-110, 101-130 (SC-004). An empty file gives no windows.

### Migration 2

1. `delete from ccctx_symbols` (only test rows can exist before this step).
2. `alter table ccctx_symbols add (commit_sha varchar2(64) not null)`.
3. Add `ccctx_symbols_commit_ck`.

`ORA-01430` and `ORA-02264` join the tolerated codes so a half-applied run finishes on retry. The column is `commit_sha` because `commit` is reserved.

## Chunk (in memory, `chunker`)

The pure chunker's output, one per future symbol row: `name`, `kind`, `start_line`, `end_line`, `source`. `chunker.chunk(language, text)` returns `list[Chunk]`, or `None` meaning "fall back to windows". `ingest` adds `content_hash` and `commit_sha` when storing.

## Skip reason (in memory)

The first matching rule decides a file's reason; every skipped file has exactly one.

| Reason | Summary label | Cause |
|---|---|---|
| `ignored` | ignored | Listed by `git ls-files --others --ignored --exclude-standard` (not read), or a symbolic link (not followed). |
| `vendored` | vendored | A path component is in `CCCTX_VENDOR_DIRS` (default `vendor,node_modules,third_party`), even if tracked. |
| `too_large` | too large | Size above `CCCTX_MAX_FILE_BYTES`. |
| `binary` | binary | Contains a NUL byte or is not valid UTF-8. |

Check order for listed files: vendored, symlink, too large, binary. Display order in the summary: ignored, vendored, binary, too large, non-zero only.

## Ingest summary (in memory, printed and logged)

The result of one run (FR-013, FR-014). Not stored.

| Field | Meaning |
|---|---|
| `repo` | Repository name. |
| `commit_sha` | HEAD at ingest. |
| `dirty` | `git status --porcelain --untracked-files=no` printed anything; triggers a stderr warning. |
| `scanned` | Files in both git listings together (`.git` never included). |
| `skipped` | Count per skip reason. |
| `files_indexed` | Files stored. |
| `fallback` | Files windowed, split into `no_grammar` and `parse_error`. |
| `symbols` | Symbol rows stored, parsed and fallback together. |
| `duration_s` | Elapsed wall time. |

Invariants: `scanned = files_indexed + sum(skipped)`; `symbols` = the repository's symbol row count after commit (SC-007). Printed as `Scanned` / `Skipped` / `Indexed` (+ `Fallback` when non-zero) on stdout; logged once as `{"event": "ingest", …}` JSON on stderr via `golestan_code_mcp.ingest`.

## Ingest run: state transitions

```text
start
  ├─ name not registered ──────────────────────────> refused (exit 1, index unchanged)
  ├─ path missing / not a work tree / no HEAD ─────> refused (exit 1, index unchanged)
  ├─ database unreachable ─────────────────────────> refused (exit 1, no password shown)
  ▼
migrated (migration DDL runs before the transaction)
  ▼
discovered (git listings, skip rules, chunking: no writes yet)
  ▼
locked (select … for update nowait on the repo row)
  ├─ ORA-00054 ────────────────────────────────────> refused: ingest already running
  ▼
replacing (delete repo's files → cascade symbols; insert files; executemany symbols)
  ├─ any error ──> rolled back ────────────────────> failed (previous index intact, FR-012)
  ▼
committed (index = exactly the current tree, FR-011) ──> summary printed + logged
```

A repository's index has only two observable states: the previous complete index, or the new complete index. No partial state is ever committed.
