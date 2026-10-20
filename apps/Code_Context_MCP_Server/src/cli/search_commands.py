"""ccctx commands that query the index: search, callers, calls, impact and eval."""

from golestan_code_mcp.cli import output
from golestan_code_mcp.config import environment
from golestan_code_mcp.graph import queries
from golestan_code_mcp.search import evaluation, query, ranking


def _repos(values: list[str] | None) -> list[str] | None:
    """--repo given any number of times, each possibly comma-separated; duplicates dropped, order kept."""
    names = [n.strip() for v in values or [] for n in v.split(",") if n.strip()]
    return list(dict.fromkeys(names)) or None


def _dash(rank: int | None):
    return "-" if rank is None else rank


def _search(conn, args) -> str:
    results = query.search(conn, args.question, _repos(args.repo), args.mode, environment(), args.language,
                           args.limit, feedback=not args.no_feedback)
    if not results:
        if args.mode == "vector":
            return f"no symbols similar enough (similarity >= {ranking.FLOOR:.2f})"
        return "no matching symbols"
    rows = [(r.rank, f"{r.score:.2f}", _percent(r.feedback) if r.feedback else "", _dash(r.keyword_rank),
             _dash(r.semantic_rank), r.repo,
             f"{r.kind} (stale)" if r.state == "stale" else r.kind, r.name, r.path,
             "-" if r.start_line is None else f"{r.start_line}-{r.end_line}") for r in results]
    header = ("RANK", "SCORE", "FEEDBACK", "KEYWORD", "SEMANTIC", "REPO", "KIND", "NAME", "PATH", "LINES")
    return output.format_table(header, rows, frozenset({0, 1, 2, 3, 4}))


def _percent(boost: float) -> str:
    return f"+{round(boost * 100)}%"


def _callers(conn, args) -> str:
    results = queries.callers(conn, args.name, _repos(args.repo))
    if not results:
        return f"no callers of '{args.name.strip()}'"
    rows = [(r.name, r.kind, r.repo, r.path, r.line, r.callee) for r in results]
    return output.format_table(("CALLER", "KIND", "REPO", "PATH", "LINE", "CALLS"), rows, frozenset({4}))


def _calls(conn, args) -> str:
    results = queries.calls(conn, args.name, _repos(args.repo))
    if not results:
        return f"'{args.name.strip()}' calls no indexed symbols"
    rows = [(r.caller, r.line, r.name, r.kind, r.repo, r.path, f"{r.start_line}-{r.end_line}") for r in results]
    return output.format_table(("FROM", "LINE", "CALLEE", "KIND", "REPO", "PATH", "LINES"), rows, frozenset({1}))


def _impact(conn, args) -> str:
    results = queries.impact(conn, args.name, args.depth, _repos(args.repo))
    if not results:
        return f"nothing calls '{args.name.strip()}'"
    rows = [(r.hops, r.name, r.kind, r.repo, r.path, f"{r.start_line}-{r.end_line}") for r in results]
    return output.format_table(("HOPS", "NAME", "KIND", "REPO", "PATH", "LINES"), rows, frozenset({0}))


GRAPH = (_callers, _calls, _impact)


def _eval(conn, args) -> str:
    gold = evaluation.load_gold(args.gold, conn)
    e = evaluation.evaluate(conn, gold, args.with_feedback, args.limit)
    return "\n".join([f"Questions: {e.questions}", f"recall@{args.limit}: {e.recall:.2f} ({e.hits}/{e.questions})",
                      *(f"missed: {q}" for q in e.missed)])
