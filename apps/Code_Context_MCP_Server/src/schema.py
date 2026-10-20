"""Ordered, re-runnable schema migrations (contracts/schema.md).

Oracle commits DDL as it runs, so a migration cannot be rolled back as a whole. Each statement
tolerates "already exists" and the version row is written only after every statement succeeded,
so a half-applied migration is finished by the next run.
"""

import oracledb

ALREADY_EXISTS = {"ORA-00955", "ORA-02260", "ORA-02261", "ORA-01408", "ORA-01430", "ORA-02264"}

# What the hybrid index searches: kind, name and path first, then the code. Ingest writes the same shape.
BACKFILL_SEARCH_TEXT = """update ccctx_symbols s
   set search_text = s.kind || ' ' || s.name || ' in '
                     || (select f.path from ccctx_files f where f.id = s.file_id) || chr(10) || s.source
 where s.search_text is null"""

TRACKING = """create table ccctx_migrations (
  version     number primary key,
  name        varchar2(128) not null,
  applied_at  timestamp with time zone default systimestamp not null
)"""

MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (1, "core tables", [
        """create table ccctx_repos (
          id             number generated always as identity primary key,
          name           varchar2(64)   not null unique,
          path           varchar2(1024) not null unique,
          registered_at  timestamp with time zone default systimestamp not null,
          constraint ccctx_repos_name_ck check (regexp_like(name, '^[a-z0-9_-]{1,64}$'))
        )""",
        """create table ccctx_files (
          id            number generated always as identity primary key,
          repo_id       number not null references ccctx_repos (id) on delete cascade,
          path          varchar2(1024) not null,
          language      varchar2(32)   not null,
          content_hash  varchar2(64)   not null,
          constraint ccctx_files_path_uk unique (repo_id, path)
        )""",
        """create table ccctx_symbols (
          id            number generated always as identity primary key,
          file_id       number not null references ccctx_files (id) on delete cascade,
          name          varchar2(512) not null,
          kind          varchar2(16)  not null,
          start_line    number not null,
          end_line      number not null,
          source        clob not null,
          content_hash  varchar2(64) not null,
          constraint ccctx_symbols_kind_ck
            check (kind in ('function','method','class','interface','type','module','chunk')),
          constraint ccctx_symbols_lines_ck check (start_line >= 1 and end_line >= start_line)
        )""",
        "create index ccctx_symbols_file_ix on ccctx_symbols (file_id)",
    ]),
    (2, "symbol commit", [
        # Only test rows can exist before ingestion, and a NOT NULL column needs an empty table.
        "delete from ccctx_symbols",
        "alter table ccctx_symbols add (commit_sha varchar2(64) not null)",
        """alter table ccctx_symbols add constraint ccctx_symbols_commit_ck
          check (regexp_like(commit_sha, '^[0-9a-f]{40}([0-9a-f]{24})?$'))""",
    ]),
    # Nullable: symbols indexed before this step keep working until they are re-ingested.
    # The HNSW index is built by `ccctx model load`, because it needs the vector memory pool.
    (3, "symbol embedding", [
        "alter table ccctx_symbols add (embedding vector(384, float32))",
        """create table ccctx_embedding_model (
          model_name  varchar2(128) primary key,
          dimension   number not null,
          loaded_at   timestamp with time zone default systimestamp not null
        )""",
    ]),
    # One hybrid vector index over search_text replaces the step 3 column and its HNSW index; it computes
    # its own vectors. The backfill makes symbols stored earlier searchable without re-ingesting.
    # `ccctx model load` builds the index, because it needs the model and the vector memory pool.
    (4, "hybrid search text", [
        ("drop index ccctx_symbols_embedding_ix", {"ORA-01418"}),  # already dropped
        ("alter table ccctx_symbols drop column embedding", {"ORA-00904"}),  # already dropped
        "alter table ccctx_symbols add (search_text clob)",
        BACKFILL_SEARCH_TEXT,
    ]),
    # The revision each repository was last indexed at, set in the ingest transaction. NULL means rebuild in full.
    (5, "repo indexed revision", [
        ("alter table ccctx_repos add (indexed_commit varchar2(64), indexed_dirty boolean,"
         " indexed_at timestamp with time zone)"),
        """alter table ccctx_repos add constraint ccctx_repos_indexed_ck
          check (indexed_commit is null or regexp_like(indexed_commit, '^[0-9a-f]{40}([0-9a-f]{24})?$'))""",
    ]),
    # The calls and imports each parse saw, the edges resolved from them, and a property graph over files and symbols.
    (6, "code graph", [
        "alter table ccctx_repos add (extract_version number)",
        """create table ccctx_call_refs (
          id         number generated always as identity primary key,
          file_id    number not null references ccctx_files (id) on delete cascade,
          caller_id  number references ccctx_symbols (id) on delete cascade,
          name       varchar2(512) not null,
          form       varchar2(4) not null,
          receiver   varchar2(512),
          line       number not null,
          constraint ccctx_call_refs_form_ck check (form in ('bare', 'attr')),
          constraint ccctx_call_refs_line_ck check (line >= 1))""",
        "create index ccctx_call_refs_file_ix on ccctx_call_refs (file_id)",
        "create index ccctx_call_refs_caller_ix on ccctx_call_refs (caller_id)",
        """create table ccctx_import_refs (
          id         number generated always as identity primary key,
          file_id    number not null references ccctx_files (id) on delete cascade,
          module     varchar2(1024) not null,
          rel_level  number default 0 not null,
          bound      varchar2(512))""",
        "create index ccctx_import_refs_file_ix on ccctx_import_refs (file_id)",
        """create table ccctx_calls (
          id         number generated always as identity primary key,
          caller_id  number not null references ccctx_symbols (id) on delete cascade,
          callee_id  number not null references ccctx_symbols (id) on delete cascade,
          line       number not null)""",
        "create index ccctx_calls_caller_ix on ccctx_calls (caller_id)",
        "create index ccctx_calls_callee_ix on ccctx_calls (callee_id)",
        """create table ccctx_file_calls (
          id         number generated always as identity primary key,
          file_id    number not null references ccctx_files (id) on delete cascade,
          callee_id  number not null references ccctx_symbols (id) on delete cascade,
          line       number not null)""",
        "create index ccctx_file_calls_file_ix on ccctx_file_calls (file_id)",
        "create index ccctx_file_calls_callee_ix on ccctx_file_calls (callee_id)",
        """create table ccctx_imports (
          id           number generated always as identity primary key,
          importer_id  number not null references ccctx_files (id) on delete cascade,
          imported_id  number not null references ccctx_files (id) on delete cascade,
          constraint ccctx_imports_pair_uk unique (importer_id, imported_id))""",
        "create index ccctx_imports_imported_ix on ccctx_imports (imported_id)",
        # create or replace: a tolerated ORA-00955 would silently keep an outdated definition.
        """create or replace property graph ccctx_graph
          vertex tables (
            ccctx_files   key (id) label code_file properties (id, repo_id, path),
            ccctx_symbols key (id) label symbol    properties (id, file_id, name, kind, start_line, end_line))
          edge tables (
            ccctx_symbols as ccctx_defines key (id)
              source key (file_id) references ccctx_files (id)
              destination key (id) references ccctx_symbols (id) label defines,
            ccctx_imports key (id)
              source key (importer_id) references ccctx_files (id)
              destination key (imported_id) references ccctx_files (id) label imports,
            ccctx_calls key (id)
              source key (caller_id) references ccctx_symbols (id)
              destination key (callee_id) references ccctx_symbols (id) label calls properties (line),
            ccctx_file_calls key (id)
              source key (file_id) references ccctx_files (id)
              destination key (callee_id) references ccctx_symbols (id) label calls properties (line))""",
    ]),
    # Docs on files and symbols, and one compiled page per qualifying directory with the records it cites.
    # The page index is built outside the migration, because it needs the loaded model (research R8).
    (7, "module wiki", [
        "alter table ccctx_files add (doc varchar2(1000 char))",
        "alter table ccctx_symbols add (doc varchar2(1000 char))",
        "alter table ccctx_repos add (wiki_at timestamp with time zone)",
        """create table ccctx_wiki_pages (
          id            number generated always as identity primary key,
          repo_id       number not null references ccctx_repos (id) on delete cascade,
          directory     varchar2(1024) not null,
          name          varchar2(1024) not null,
          language      varchar2(32)   not null,
          symbols       number not null,
          text          clob not null,
          search_text   clob not null,
          state         varchar2(8)    not null,
          compiled_at   timestamp with time zone not null,
          compiler      varchar2(64)   not null,
          stale_reason  varchar2(512),
          constraint ccctx_wiki_pages_dir_uk unique (repo_id, directory),
          constraint ccctx_wiki_pages_name_uk unique (repo_id, name),
          constraint ccctx_wiki_pages_symbols_ck check (symbols >= 10),
          constraint ccctx_wiki_pages_state_ck check (state in ('fresh', 'stale')))""",
        """create table ccctx_wiki_citations (
          id            number generated always as identity primary key,
          page_id       number not null references ccctx_wiki_pages (id) on delete cascade,
          symbol_id     number references ccctx_symbols (id) on delete set null,
          file_id       number references ccctx_files (id) on delete set null,
          role          varchar2(8)    not null,
          name          varchar2(1024) not null,
          kind          varchar2(16)   not null,
          commit_sha    varchar2(64)   not null,
          content_hash  varchar2(64)   not null,
          constraint ccctx_wiki_citations_role_ck check (role in ('key', 'calls', 'file', 'depends', 'uses')),
          constraint ccctx_wiki_citations_target_ck
            check ((role in ('key', 'calls') and file_id is null)
                   or (role in ('file', 'depends', 'uses') and symbol_id is null)),
          constraint ccctx_wiki_citations_commit_ck
            check (regexp_like(commit_sha, '^[0-9a-f]{40}([0-9a-f]{24})?$')))""",
        "create index ccctx_wiki_citations_page_ix on ccctx_wiki_citations (page_id)",
        "create index ccctx_wiki_citations_symbol_ix on ccctx_wiki_citations (symbol_id)",
        "create index ccctx_wiki_citations_file_ix on ccctx_wiki_citations (file_id)",
    ]),
    # One row per MCP tool call and the repositories it belongs to; facts live in the memory package's tables,
    # which its own setup creates here so no table appears outside a migration (specs/010 data-model.md).
    (8, "agent memory", [
        """create table ccctx_memory_runs (
          id            number generated always as identity primary key,
          called_at     timestamp with time zone default systimestamp not null,
          tool          varchar2(64)  not null,
          arguments     json not null,
          question      varchar2(1000 char),
          client        varchar2(256),
          status        varchar2(16)  not null,
          reason        varchar2(1000 char),
          ms            number,
          result_count  number default 0 not null,
          results       json not null,
          scoped        boolean default false not null,
          constraint ccctx_memory_runs_status_ck check (status in ('ok', 'unavailable', 'error')))""",
        "create index ccctx_memory_runs_called_ix on ccctx_memory_runs (called_at)",
        """create table ccctx_memory_run_repos (
          run_id        number not null references ccctx_memory_runs (id) on delete cascade,
          repo_id       number not null references ccctx_repos (id) on delete cascade,
          consolidated  boolean default false not null,
          constraint ccctx_memory_run_repos_pk primary key (run_id, repo_id))""",
        "create index ccctx_memory_run_repos_repo_ix on ccctx_memory_run_repos (repo_id, consolidated)",
        lambda cur: _package_schema(cur.connection),
    ]),
    # One row per result per session (011 FR-005), kept by the writer's MERGE: a unique key on two 1024-character
    # columns would pass Oracle's index key limit. Keyed by identity, not symbol id, so a re-ingest keeps it.
    (9, "usage feedback", [
        """create table ccctx_feedback (
          id       number generated always as identity primary key,
          repo_id  number not null references ccctx_repos (id) on delete cascade,
          path     varchar2(1024 char) not null,
          name     varchar2(1024 char) not null,
          kind     varchar2(32) not null,
          how      varchar2(8)  not null,
          client   varchar2(256),
          session_id varchar2(64) not null,
          run_id   number references ccctx_memory_runs (id) on delete set null,
          used_at  timestamp with time zone default systimestamp not null,
          constraint ccctx_feedback_how_ck check (how in ('cited', 'opened')))""",
        "create index ccctx_feedback_result_ix on ccctx_feedback (repo_id, name)",
    ]),
    # The namespaces a C# file declares, which its `using`s resolve through, and each definition's visibility,
    # which the wiki ranks by (012). Rows written before get today's name rule.
    (10, "language coverage", [
        "alter table ccctx_files add (namespaces json)",
        "alter table ccctx_symbols add (exported boolean)",
        """update ccctx_symbols s
              set exported = case
                    when (select f.language from ccctx_files f where f.id = s.file_id) = 'go'
                      then regexp_like(regexp_substr(s.name, '[^.]+$'), '^[A-Z]')
                    else not regexp_like(regexp_substr(s.name, '[^.]+$'), '^_') end
            where s.kind <> 'chunk' and s.exported is null""",
    ]),
]


def _package_schema(conn) -> None:
    from golestan_code_mcp.memory import (
        store,  # late: loading schema must not load memory or the package
    )

    store.create_package_schema(conn)


def _run(cur, statement) -> None:
    """Run one migration statement: SQL, a (sql, codes) pair that also tolerates those codes, or a Python step."""
    if callable(statement):
        statement(cur)
        return
    sql, tolerated = statement if isinstance(statement, tuple) else (statement, set())
    try:
        cur.execute(sql)
    except oracledb.DatabaseError as e:
        if getattr(e.args[0], "full_code", "") not in ALREADY_EXISTS | tolerated:
            raise


def migrate(conn) -> list[int]:
    """Apply every missing migration in order. Returns the versions applied by this call."""
    with conn.cursor() as cur:
        _run(cur, TRACKING)
        applied = {row[0] for row in cur.execute("select version from ccctx_migrations")}
        done = []
        for version, name, statements in MIGRATIONS:
            if version in applied:
                continue
            for sql in statements:
                _run(cur, sql)
            cur.execute("insert into ccctx_migrations (version, name) values (:v, :n)", v=version, n=name)
            conn.commit()
            done.append(version)
        return done


def version(conn) -> int:
    with conn.cursor() as cur:
        return cur.execute("select nvl(max(version), 0) from ccctx_migrations").fetchone()[0]
