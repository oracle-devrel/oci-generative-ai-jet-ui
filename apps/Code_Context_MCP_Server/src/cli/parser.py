"""ccctx arguments: every subcommand, its options, and the checks argparse applies to them."""

import argparse

from golestan_code_mcp.cli import (
    index_commands,
    memory_commands,
    search_commands,
    wiki_commands,
)
from golestan_code_mcp.graph import queries
from golestan_code_mcp.search import query

KINDS = ["function", "method", "class", "type", "interface", "chunk"]


def _positive(text: str) -> int:
    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return int(text)


def _not_negative(text: str) -> int:
    if not text.isdigit():
        raise argparse.ArgumentTypeError("must be a whole number of days, 0 or more")
    return int(text)


def _count(text: str) -> int:
    if not text.isdigit() or not 1 <= int(text) <= 100000:
        raise argparse.ArgumentTypeError("must be from 1 to 100000")
    return int(text)


def _eval_limit(text: str) -> int:
    if not text.isdigit() or not 1 <= int(text) <= query.MAX_LIMIT:
        raise argparse.ArgumentTypeError(f"must be from 1 to {query.MAX_LIMIT}")
    return int(text)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ccctx", description="Code context: manage indexed codebases.")
    groups = p.add_subparsers(dest="group", required=True)

    repo = groups.add_parser("repo", help="register and list repositories").add_subparsers(dest="cmd", required=True)
    add = repo.add_parser("add", help="register a local directory")
    add.add_argument("path")
    add.add_argument("--name", required=True)
    add.set_defaults(run=index_commands._repo_add)
    repo.add_parser("list", help="list registered repositories").set_defaults(run=index_commands._repo_list)

    ing = groups.add_parser("ingest", help="index a registered repository")
    ing.add_argument("name")
    ing.add_argument("--full", action="store_true", help="discard the index and rebuild it from the working tree")
    ing.set_defaults(run=index_commands._ingest)

    sym = groups.add_parser("symbols", help="list indexed symbols")
    sym.add_argument("--repo", required=True)
    sym.add_argument("--limit", type=_positive, default=20)
    sym.add_argument("--kind", choices=KINDS)
    sym.set_defaults(run=index_commands._symbols)

    st = groups.add_parser("stats", help="index statistics")
    st.add_argument("--by-language", action="store_true", required=True)
    st.add_argument("--repo")
    st.set_defaults(run=index_commands._stats)

    srch = groups.add_parser("search", help="find code by name or meaning (keyword + semantic, fused)")
    srch.add_argument("question")
    srch.add_argument("--mode", default="hybrid", help="vector, text or hybrid (default)")
    srch.add_argument("--repo", action="append", help="limit to these repositories; repeat or comma-separate")
    srch.add_argument("--language", help="limit to files of this language")
    srch.add_argument("--limit", default="10", help=f"hits to return, 1 to {query.MAX_LIMIT} (default 10)")
    srch.add_argument("--no-feedback", action="store_true", help="rank without usage feedback")
    srch.set_defaults(run=search_commands._search)

    for run, cmd, text in [(search_commands._callers, "callers", "list every call to a symbol"),
                           (search_commands._calls, "calls", "list the indexed symbols a symbol calls"),
                           (search_commands._impact, "impact", "list the symbols a change could affect, by call hops")]:
        g = groups.add_parser(cmd, help=text)
        g.add_argument("name")
        g.add_argument("--repo", action="append", help="limit to these repositories; repeat or comma-separate")
        if run is search_commands._impact:
            g.add_argument("--depth", default="3", help=f"call hops to follow, 1 to {queries.MAX_DEPTH} (default 3)")
        g.set_defaults(run=run)

    wk = groups.add_parser("wiki", help="module pages written from the index").add_subparsers(dest="cmd", required=True)
    for cmd, run, text in [("build", wiki_commands._wiki_build,
                            "compile the pages of a repository, or of every indexed one"),
                           ("list", wiki_commands._wiki_list, "list the pages with their state"),
                           ("show", wiki_commands._wiki_show, "print a page and where each cited symbol is now"),
                           ("citations", wiki_commands._wiki_citations, "list a page's citations")]:
        w = wk.add_parser(cmd, help=text)
        if run in (wiki_commands._wiki_show, wiki_commands._wiki_citations):
            w.add_argument("page")
        w.add_argument("--repo")
        w.set_defaults(run=run)
    mem = groups.add_parser("memory", help="what the server remembers of tool calls").add_subparsers(
        dest="cmd", required=True)
    ml = mem.add_parser("list", help="list recorded tool calls, newest first")
    ml.add_argument("--repo")
    ml.add_argument("--limit", type=_positive, default=20)
    ml.set_defaults(run=memory_commands._memory_list)
    mc = mem.add_parser("consolidate", help="distil recorded tool calls into facts")
    mc.add_argument("--repo")
    mc.set_defaults(run=memory_commands._memory_consolidate)
    mf = mem.add_parser("facts", help="list distilled facts, fresh and most confident first")
    mf.add_argument("--repo")
    mf.add_argument("--limit", type=_positive, default=20)
    mf.set_defaults(run=memory_commands._memory_facts)
    fb = groups.add_parser("feedback", help="which results clients used, and the boost it earns").add_subparsers(
        dest="cmd", required=True)
    fl = fb.add_parser("list", help="list results with uses, highest weight first")
    fl.add_argument("--repo", required=True)
    fl.set_defaults(run=memory_commands._feedback_list)
    fa = fb.add_parser("add", help="record cited uses of an indexed symbol or page by hand")
    fa.add_argument("name")
    fa.add_argument("--repo", required=True)
    fa.add_argument("--path", help="the symbol's file or the page's directory; needed when the name is at several")
    fa.add_argument("--days-ago", type=_not_negative, default=0, help="date the uses this many days back (default 0)")
    fa.add_argument("--count", type=_count, default=1, help="how many uses, 1 to 100000 (default 1)")
    fa.set_defaults(run=memory_commands._feedback_add)
    fr = fb.add_parser("reset", help="delete uses")
    scope = fr.add_mutually_exclusive_group(required=True)
    scope.add_argument("--repo")
    scope.add_argument("--all", action="store_true", help="every repository's uses")
    fr.set_defaults(run=memory_commands._feedback_reset)
    ev = groups.add_parser("eval", help="recall of a gold set of questions and expected paths")
    ev.add_argument("--gold", required=True, help="the gold file, for example gold.json")
    ev.add_argument("--with-feedback", action="store_true", help="rank with usage feedback (default: without)")
    ev.add_argument("--limit", type=_eval_limit, default=10, help="hits per question to look at (default 10)")
    ev.set_defaults(run=search_commands._eval)
    model = groups.add_parser("model", help="embedding model").add_subparsers(dest="cmd", required=True)
    model.add_parser("load", help="download once and load the embedding model").set_defaults(
        run=index_commands._model_load)

    groups.add_parser("mcp", help="run the MCP server over standard input and output").set_defaults(run=None)

    dbp = groups.add_parser("db", help="database administration").add_subparsers(dest="cmd", required=True)
    dbp.add_parser("migrate", help="apply missing schema migrations").set_defaults(run=index_commands._db_migrate)
    return p
