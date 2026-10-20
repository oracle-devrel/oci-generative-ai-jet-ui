"""ccctx memory and feedback commands: memory list, consolidate and facts; feedback list, add and reset."""

from golestan_code_mcp.cli import output, search_commands, wiki_commands
from golestan_code_mcp.memory import consolidate, distill, recall, runs
from golestan_code_mcp.memory import store as memory_store
from golestan_code_mcp.search import feedback as search_feedback


def _memory_list(conn, args) -> str:
    found = runs.runs(conn, args.repo, args.limit)
    if not found:
        return "no runs recorded"
    rows = [(r.id, wiki_commands._when(r.called_at), r.tool, (r.question or "").strip() or "-", r.client or "-",
             r.status, f"{len(r.used)}/{r.result_count}" if r.used else r.result_count, wiki_commands._top(r))
            for r in found]
    return output.format_table(("RUN", "WHEN", "TOOL", "QUESTION", "CLIENT", "STATUS", "RESULTS", "TOP"), rows,
                               frozenset({0, 6}))


def _distillers(c: consolidate.Consolidation) -> str:
    """`template/1` without a model; with one, how many facts each distiller wrote."""
    if memory_store.model() is None:
        return distill.TEMPLATE
    return ", ".join(f"{k}: {v}" for k, v in sorted(c.distillers.items())) or distill.TEMPLATE


def _memory_consolidate(conn, args) -> str:
    done = consolidate.consolidate(conn, args.repo)
    if not done:
        return "nothing to consolidate"
    return "\n".join(f"{c.repo}: {c.runs} runs read, {c.created} created, {c.merged} merged, {c.weakened} weakened,"
                     f" {c.stale} stale, {c.reasked} re-asked in {c.seconds:.1f}s ({_distillers(c)})" for c in done)


def _fact_text(f: recall.FactView) -> str:
    text = f.text if len(f.text) <= 120 else f.text[:119] + "…"
    return f"{text} (stale: {f.stale_reason})" if f.state == "stale" else text


def _memory_facts(conn, args) -> str:
    found = recall.facts(conn, args.repo, args.limit)
    if not found:
        return "no facts"
    rows = [(f.id[:8], f.repo, f.subject, f"{f.confidence:.3f}", f.state, f.distiller, ",".join(map(str, f.runs)),
             _fact_text(f)) for f in found]
    return output.format_table(("FACT", "REPO", "SUBJECT", "CONFIDENCE", "STATE", "DISTILLER", "RUNS", "TEXT"), rows)


def _feedback_list(conn, args) -> str:
    rows = search_feedback.listing(conn, args.repo)
    if not rows:
        return f"no feedback recorded for {args.repo}"
    return output.format_table(("KIND", "NAME", "PATH", "USES", "WEIGHT", "BOOST", "LAST USED", "INDEXED"), [
        (r.kind, r.name, r.path, r.uses, f"{r.weight:.2f}", search_commands._percent(r.boost),
         wiki_commands._when(r.last_used), "yes" if r.indexed else "no") for r in rows], frozenset({3, 4, 5}))


def _feedback_add(conn, args) -> str:
    path, _ = search_feedback.add(conn, args.repo, args.name, args.path, args.days_ago, args.count)
    uses = "use" if args.count == 1 else "uses"
    return f"recorded {args.count} {uses} of {args.name} ({path}) in {args.repo}, dated {args.days_ago} days ago"


def _feedback_reset(conn, args) -> str:
    deleted = search_feedback.reset(conn, None if args.all else args.repo)
    return f"deleted {deleted} uses in {'all repositories' if args.all else args.repo}"
