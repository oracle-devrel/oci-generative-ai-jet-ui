"""ccctx commands that build the index: repo add and list, ingest, symbols, stats, model load and db migrate."""

import sys

from golestan_code_mcp import registry, schema
from golestan_code_mcp.cli import output
from golestan_code_mcp.config import environment
from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.search import model as search_model


def _repo_add(conn, args) -> str:
    repo = registry.add_repo(conn, args.path, args.name)
    return f"registered {repo.name} {repo.path}"


def _repo_list(conn, args) -> str:
    repos = registry.list_repos(conn)
    if not repos:
        return "no repositories registered"
    rows = [(r.name, r.path, r.files, r.symbols) for r in repos]
    return output.format_table(("NAME", "PATH", "FILES", "SYMBOLS"), rows, frozenset({2, 3}))


def _ingest(conn, args) -> str:
    summary = indexing_ingest.ingest(conn, args.name, full=args.full)
    if summary.note:
        print(f"note: {summary.note}", file=sys.stderr)
    if summary.dirty and summary.mode != "current":
        print("warning: working tree has uncommitted changes; indexed the files as they are on disk", file=sys.stderr)
    if summary.wiki and summary.wiki.error:
        print(f"warning: wiki not recompiled: {summary.wiki.error}", file=sys.stderr)
    if isinstance(summary.memory, str):
        print(f"warning: memory not consolidated: {summary.memory}", file=sys.stderr)
    return output.format_summary(summary)


def _symbols(conn, args) -> str:
    repo_id = registry.repo_id(conn, args.repo)
    with conn.cursor() as cur:
        cur.execute(
            """select s.name, s.kind, f.language, f.path, s.start_line || '-' || s.end_line
                 from ccctx_symbols s join ccctx_files f on f.id = s.file_id
                where f.repo_id = :r and (:k is null or s.kind = :k)
                order by case when s.kind = 'chunk' then 1 else 0 end, f.path, s.start_line, s.end_line desc
                fetch first :lim rows only""",
            r=repo_id, k=args.kind, lim=args.limit,
        )
        rows = cur.fetchall()
    return output.format_table(("NAME", "KIND", "LANGUAGE", "PATH", "LINES"), rows) if rows else "no symbols"


def _stats(conn, args) -> str:
    repo_id = registry.repo_id(conn, args.repo) if args.repo else None
    with conn.cursor() as cur:
        cur.execute(
            """select r.name, f.language, count(distinct f.id),
                      count(case when s.kind <> 'chunk' then 1 end), count(case when s.kind = 'chunk' then 1 end)
                 from ccctx_repos r join ccctx_files f on f.repo_id = r.id
                 left join ccctx_symbols s on s.file_id = f.id
                where (:r is null or r.id = :r)
                group by r.name, f.language
                order by r.name, f.language""",
            r=repo_id,
        )
        rows = cur.fetchall()
    if not rows:
        return "nothing indexed"
    return output.format_table(("REPO", "LANGUAGE", "FILES", "SYMBOLS", "CHUNKS"), rows, frozenset({2, 3, 4}))


def _model_load(conn, args) -> str:
    return search_model.load_model(conn, environment())


def _db_migrate(conn, args) -> str:
    applied = schema.migrate(conn)
    names = {v: n for v, n, _ in schema.MIGRATIONS}
    if applied:
        return "\n".join(f"applied {v} {names[v]}" for v in applied)
    return f"schema up to date (version {schema.version(conn)})"
