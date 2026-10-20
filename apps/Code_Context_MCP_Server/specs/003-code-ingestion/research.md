# Research: Code Ingestion and Chunking

## Listing files: let git apply `.gitignore`

- **Decision**: list the files to index with `git ls-files -z --cached --others --exclude-standard`. Count gitignored files with `git ls-files -z --others --ignored --exclude-standard`. "Scanned" is the size of both lists together.
- **Rationale**: git already applies root and nested `.gitignore` files, `.git/info/exclude` and the global excludes, with git's exact semantics. `.git` itself is never listed. A tracked file that matches an ignore pattern is still indexed, as git treats it.
- **Alternatives considered**: a Python gitignore matcher such as `pathspec` is a new dependency that re-implements git's rules imperfectly, nested files especially. Walking with `os.walk` and no ignore support breaks FR-002.

## Running git without letting the repository run anything

- **Decision**: every git call is `git -c core.fsmonitor=false -c core.hooksPath=/dev/null --no-optional-locks -C <repo> …`, run with a fixed argument list (no shell). Only `rev-parse HEAD`, `ls-files` and `status --porcelain` are used.
- **Rationale**: these commands only read. `--no-optional-locks` stops `status` refreshing `.git/index`. A repository's own `.git/config` can name an fsmonitor program that git would run, and disabling it keeps FR-017 and constitution VII intact.
- **Alternatives considered**: reading `.git` directly (index format, packed refs) is fragile and much more code.

## Skip rules and their order

- **Decision**: each listed file goes through these checks, and the first match is its skip reason:
  1. **vendored**: any path component is in the vendored list.
  2. **ignored**: the path is a symbolic link.
  3. **too large**: bigger than `CCCTX_MAX_FILE_BYTES`, default 1048576.
  4. **binary**: the content contains a NUL byte or fails strict UTF-8 decoding.

  Files reported by the ignored listing are counted as ignored without being read. `CCCTX_VENDOR_DIRS` is a comma-separated list, default `vendor,node_modules,third_party`.
- **Rationale**: the cheap path checks come first, then the size from `lstat`, and only then is the file read. The checks themselves never follow a symlink.
- **Alternatives considered**: guessing binary from the extension misses files with no extension and wrongly skips text files with an unexpected extension.

## The commit and a dirty working tree

- **Decision**: the commit is `git rev-parse HEAD`, a 40-character SHA-1 or 64-character SHA-256, stored in full. Any output from `git status --porcelain --untracked-files=no` means the summary prints a warning. Two cases are refused with an error: `rev-parse --is-inside-work-tree` failing (not a git repository) and HEAD not resolving (no commits yet).
- **Rationale**: this matches US4. Untracked files are indexed but do not count as "dirty" for the warning, because they would make every scratch file noisy.

## Chunking with tree-sitter

- **Decision**: `chunker.chunk(language, text) -> list[Chunk] | None`. It returns `None` when there is no grammar for the language or `root_node.has_error` is true, and the caller then falls back to windows. The rules per language:

  | Language | Stored as symbols | Naming |
  |---|---|---|
  | Python | module-level `function_definition` and `class_definition`. Inside a class body, `function_definition` becomes a method and a nested class is recursed into. `decorated_definition` is unwrapped but its outer range is kept. | `Class.method`, `Outer.Inner` |
  | Go | `function_declaration`, `method_declaration`, and each `type_spec` inside a `type_declaration` (`struct_type` → `type`, `interface_type` → `interface`, anything else → `type`). | method: receiver type with `*` and type parameters stripped, `Engine.Use` |
  | JavaScript | `function_declaration`, `generator_function_declaration`, `class_declaration` and its `method_definition`s, plus `const`/`let`/`var` declarators whose value is an arrow function or function expression. `export_statement` is unwrapped but its range is kept. | `Class.method`, declarator name |

  Ranges come from whole lines. Start is `start_point.row + 1`, end is `end_point.row + 1`. `source` is exactly those lines of the file.
- **Rationale**: whole lines make the stored source match what an editor shows for the range. A grouped Go `type ( … )` yields one symbol per spec, so `named_children[0]` alone is not enough. Nested functions are not visited, which keeps them inside their parent (spec edge case).
- **Alternatives considered**: treating partial errors as success hides broken code behind missing symbols. The spec chose whole-file fallback.

## Fallback windows

- **Decision**: windows of 60 lines starting at lines 1, 51, 101 and so on, stopping once a window reaches the last line. Each is stored with kind `chunk` and named `<file name>:<start>-<end>`. Language comes from an extension map (`markdown`, `rst`, `yaml`, `toml`, `html`, `json`, `shell` and others), else `text`. An empty file produces no chunk.
- **Rationale**: this follows FR-007 and SC-004 exactly. `name` is required, and a file-and-range name reads well in `ccctx symbols`.

## Storing a run atomically

- **Decision**: one transaction per ingest:
  1. Lock the repository row with `select … for update nowait`. ORA-00054 means another ingest is running and is reported as such, exit 1.
  2. Delete the repository's files, which cascades to their symbols.
  3. Insert each file with `returning id`.
  4. Insert all symbols with one `executemany`, with `source` bound as `DB_TYPE_CLOB`.
  5. Commit.

  Any exception rolls back.
- **Rationale**: FR-011 and FR-012 come from Oracle's transaction, with no staging tables. Migration DDL runs in the CLI's pre-step, before the transaction opens, so no implicit commit can land inside it.

## Migration 2

- **Decision**: three statements:
  1. `delete from ccctx_symbols`. Before this step only test rows can exist.
  2. Add the column: `alter table ccctx_symbols add (commit_sha varchar2(64) not null)`.
  3. Add the check: `alter table ccctx_symbols add constraint ccctx_symbols_commit_ck check (regexp_like(commit_sha, '^[0-9a-f]{40}([0-9a-f]{24})?$'))`.

  Add `ORA-01430` (column exists) and `ORA-02264` (constraint name used) to the tolerated codes.
- **Rationale**: `commit` is an Oracle reserved word. A NOT NULL column cannot be added to a table with rows unless they are cleared first. The added codes keep a half-applied migration re-runnable.

## Summary output and the structured log

- **Decision**: these lines go to stdout:
  - `Scanned`, `Skipped` (reasons in parentheses, only those that are non-zero, in the order ignored, vendored, binary, too large) and `Indexed` (`<n> symbols in <s>s`, one decimal). The numbers use thousands separators and are right-aligned to the widest of the three.
  - A `Fallback` line, only when some files fell back, as `<n> files as line windows (<a> no grammar, <b> parse errors)`.

  The dirty-tree warning goes to stderr. One JSON log line, `{"event": "ingest", …}`, goes to stderr through the `golestan_code_mcp.ingest` logger, which `cli.main` configures.
- **Rationale**: stdout stays the readable summary. The log record is machine-readable for constitution VII without a logging library.

## `symbols` and `stats`

- **Decision**: `format_table(header, rows, numeric)` is generalised and reused by `repo list`. `symbols` shows `NAME KIND LANGUAGE PATH LINES`, sorted as FR-015 requires, default limit 20, with optional `--kind`. `stats --by-language` shows `REPO LANGUAGE FILES SYMBOLS CHUNKS`, where `SYMBOLS` counts parsed symbols and `CHUNKS` counts fallback windows, sorted by repository then language. `--repo` filters it to one repository.
- **Rationale**: one table formatter, and `repo list` output is unchanged. `repo list` keeps counting every stored chunk as a symbol, so its total matches the ingest summary's `Indexed` count.
