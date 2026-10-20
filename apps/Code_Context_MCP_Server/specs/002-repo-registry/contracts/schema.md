# Contract: database schema

Owner: the application user (`DB_USER`) in FREEPDB1. Created by migration 1, `core tables`. Later steps index into these tables and may only change them through new migrations.

```sql
create table ccctx_migrations (
  version     number primary key,
  name        varchar2(128) not null,
  applied_at  timestamp with time zone default systimestamp not null
);

create table ccctx_repos (
  id             number generated always as identity primary key,
  name           varchar2(64)   not null unique,
  path           varchar2(1024) not null unique,
  registered_at  timestamp with time zone default systimestamp not null,
  constraint ccctx_repos_name_ck check (regexp_like(name, '^[a-z0-9_-]{1,64}$'))
);

create table ccctx_files (
  id            number generated always as identity primary key,
  repo_id       number not null references ccctx_repos (id) on delete cascade,
  path          varchar2(1024) not null,
  language      varchar2(32)   not null,
  content_hash  varchar2(64)   not null,
  constraint ccctx_files_path_uk unique (repo_id, path)
);

create table ccctx_symbols (
  id            number generated always as identity primary key,
  file_id       number not null references ccctx_files (id) on delete cascade,
  name          varchar2(512) not null,
  kind          varchar2(16)  not null,
  start_line    number not null,
  end_line      number not null,
  source        clob not null,
  content_hash  varchar2(64) not null,
  constraint ccctx_symbols_kind_ck check (kind in ('function','method','class','interface','type','module','chunk')),
  constraint ccctx_symbols_lines_ck check (start_line >= 1 and end_line >= start_line)
);

create index ccctx_symbols_file_ix on ccctx_symbols (file_id);
```

- `ccctx_files.path` is relative to the repository root, with `/` separators.
- `content_hash` is a lowercase hex SHA-256 (64 characters).
- A symbol's repository, path and language come from its file.
- `ccctx_smoke` from phase 1 is unrelated and stays as the development smoke table.
