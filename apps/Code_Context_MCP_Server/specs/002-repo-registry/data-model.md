# Data Model: Database Schema and Repository Registry

**Feature**: `002-repo-registry` | **Spec**: [repo-registry.spec.md](./repo-registry.spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

All tables live in the application user's schema in FREEPDB1 and carry the `ccctx_` prefix (research: Table names and keys). Every rule below is enforced in the database; the name and path rules are also checked in `registry` before connecting, so bad input fails without a database round trip (research: Validation).

## Relationships

```text
ccctx_repos 1 ──< ccctx_files 1 ──< ccctx_symbols
     (on delete cascade)    (on delete cascade)

ccctx_migrations   (standalone, no foreign keys)
```

- A repository owns zero or more files. A file owns zero or more symbols.
- A symbol reaches its repository, path and language only through its file. No `repo_id` is copied onto symbols (spec Assumptions; research: Table names and keys).
- Deleting a repository deletes its files, which deletes their symbols. Deleting a file deletes its symbols (FR-009).

## Repository (`ccctx_repos`)

A registered codebase (FR-005).

| Field | Type | Null | Rule |
|---|---|---|---|
| `id` | `number generated always as identity` | no | Primary key. |
| `name` | `varchar2(64)` | no | Unique. `check (regexp_like(name, '^[a-z0-9_-]{1,64}$'))`. Compared exactly; `Flask` is rejected, not folded to `flask`. |
| `path` | `varchar2(1024)` | no | Unique. The resolved absolute path, `str(Path(p).expanduser().resolve())`. |
| `registered_at` | `timestamp with time zone` | no | `default systimestamp`. |

**Validation (from requirements)**

- Name: 1 to 64 characters, lowercase letters, digits, `-`, `_` only (Edge Cases, FR-011).
- Path: must exist and be a directory at registration time; `~`, relative paths, trailing slashes, `..` and symlinks resolve to one canonical string (US2 #2, Edge Cases). On Windows `resolve()` returns the real casing, so case variants map to one row (research: Paths).
- Duplicate name or duplicate path is refused with the existing registration named (US2 #4, #5). Under a race, the unique constraint makes exactly one insert succeed; the loser's ORA-00001 is mapped to the same duplicate error (Edge Cases).
- Registration touches nothing inside the directory beyond `is_dir()` (FR-013).

**Derived (not stored)**: `files` = count of its `ccctx_files` rows; `symbols` = count of `ccctx_symbols` rows reached through those files. Both are computed per listing (FR-012, US3 #2).

## File (`ccctx_files`)

One source file inside a repository (FR-006). Written by the indexing step; this feature only creates the table.

| Field | Type | Null | Rule |
|---|---|---|---|
| `id` | `number generated always as identity` | no | Primary key. |
| `repo_id` | `number` | no | FK → `ccctx_repos(id) on delete cascade`. |
| `path` | `varchar2(1024)` | no | Relative to the repository root, `/` separators (research: Paths). Unique together with `repo_id`. |
| `language` | `varchar2(32)` | no | e.g. `python`, `go`. |
| `content_hash` | `varchar2(64)` | no | Hash of the file contents (hex). |

**Validation**: `unique (repo_id, path)`. The same relative path may repeat across repositories (Edge Cases).

## Symbol (`ccctx_symbols`)

One indexed chunk of code (FR-007). Written by the indexing step; this feature only creates the table.

| Field | Type | Null | Rule |
|---|---|---|---|
| `id` | `number generated always as identity` | no | Primary key. |
| `file_id` | `number` | no | FK → `ccctx_files(id) on delete cascade`. |
| `name` | `varchar2(512)` | no | Not unique; may repeat within a file and across repositories (Edge Cases). |
| `kind` | `varchar2(16)` | no | `check (kind in ('function','method','class','interface','type','module','chunk'))` (FR-008; research: Symbol kinds). `chunk` flags fallback windowing (constitution II). |
| `start_line` | `number(10)` | no | `check (start_line >= 1)`. |
| `end_line` | `number(10)` | no | `check (end_line >= start_line)`. |
| `source` | `clob` | no | The symbol's source code. |
| `content_hash` | `varchar2(64)` | no | Hash of `source` (hex). |

## Migration (`ccctx_migrations`)

One applied schema change (FR-004).

| Field | Type | Null | Rule |
|---|---|---|---|
| `version` | `number(10)` | no | Primary key. Matches the version in `schema.MIGRATIONS`. |
| `name` | `varchar2(128)` | no | Short label from `schema.MIGRATIONS`. |
| `applied_at` | `timestamp with time zone` | no | `default systimestamp`. |

**Source of truth**: `schema.MIGRATIONS` is an ordered list of `(version, name, [statements])`. Migration 1 creates the three tables above.

## State transitions

### Migration

```text
pending ──(all statements run; ORA-00955 ignored)──> applied (row inserted)
pending ──(a statement fails)──> pending (no row; re-run is safe)
```

- `migrate(conn)` creates `ccctx_migrations` if missing, reads applied versions, runs each missing one in order, and inserts its row only after all its statements succeed. Oracle commits DDL implicitly, so a half-applied migration stays `pending` and its idempotent statements re-run cleanly (research: Migrations).
- Re-running with nothing pending changes nothing (FR-003, SC-002).
- Triggered by `ccctx db migrate`, and first thing in `ccctx repo add`, `ccctx repo list` and `list_repositories` (research: When migrations run).

### Repository

```text
(absent) ──repo add, valid & unique──> registered
(absent) ──repo add, refused──> (absent)       # nothing recorded (FR-011)
registered ──delete row──> (absent)            # cascades files and symbols; no CLI command yet
```

- A registered repository whose directory is later deleted stays `registered`; detecting that belongs to indexing (Edge Cases).
- Registration persists across container stop/start and remove/recreate while the `oradata` volume is kept (FR-002, SC-004).

## Interface shapes over this model

Both interfaces read through `registry.list_repos`, sorted by `name` (FR-012, FR-015):

- CLI row: `NAME  PATH  FILES  SYMBOLS`.
- MCP `list_repositories`: `{database, reason, repositories: [{name, path, files, symbols}]}`; `database: "unreachable"` with `repositories: []` when the database is down (research: MCP tool shape).
