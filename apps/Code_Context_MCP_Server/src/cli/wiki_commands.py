"""ccctx wiki commands: build, list, show and citations."""

import posixpath
import sys
from datetime import UTC

from golestan_code_mcp.cli import output
from golestan_code_mcp.memory import runs
from golestan_code_mcp.wiki import build, read, store


def _when(at) -> str:
    """A compile time in UTC, YYYY-MM-DD HH:MM:SS."""
    return (at.astimezone(UTC) if at.tzinfo else at).strftime("%Y-%m-%d %H:%M:%S")


def _wiki_build(conn, args) -> str:
    built = build.build(conn, args.repo)
    with conn.cursor() as cur:
        if not store.ensure_index(cur):
            print("note: wiki pages are not searchable until you run `ccctx model load`", file=sys.stderr)
    return "\n".join(f"{b.repo}: {b.pages} pages ({b.added} added, {b.updated} updated, {b.removed} removed)"
                     f" in {b.seconds:.1f}s" for b in built)


def _wiki_list(conn, args) -> str:
    pages = read.pages(conn, args.repo)
    if not pages:
        return "no wiki pages"
    rows = [(p.name, p.repo, p.state, p.symbols, _when(p.compiled_at), p.stale_reason or "-") for p in pages]
    return output.format_table(("NAME", "REPO", "STATE", "SYMBOLS", "COMPILED", "LAST STALE"), rows, frozenset({3}))


def _source(c: read.CitationView) -> str:
    """One Sources line: the citation located through its key, or `gone`."""
    if c.path is None:
        where = "gone"
    elif c.kind == "file":
        where = ""
    else:
        where = f"{c.path}:{c.start_line}-{c.end_line}"
    return f"- `{c.name}` ({c.kind}, {c.role}) {where}".rstrip()


def _wiki_show(conn, args) -> str:
    p = read.read(conn, args.page, args.repo)
    lines = [f"{p.name} ({p.repo}, {p.directory}) {p.state}, compiled {_when(p.compiled_at)} by {p.compiler}"]
    if p.state == "stale":
        lines.append(f"stale: {p.stale_reason}")
    return "\n".join([*lines, "", p.text.rstrip("\n"), "", "## Sources", *map(_source, p.citations)])


def _wiki_citations(conn, args) -> str:
    p = read.read(conn, args.page, args.repo)
    rows = [(posixpath.basename(c.name) if c.kind == "file" else c.name, c.kind, c.role, c.repo or "-", c.path or "-",
             "-" if c.start_line is None else f"{c.start_line}-{c.end_line}", c.recorded_commit[:12],
             (c.current_commit or "gone")[:12] if c.path else "gone") for c in p.citations]
    return output.format_table(("NAME", "KIND", "ROLE", "REPO", "PATH", "LINES", "COMPILED", "CURRENT"), rows)


def _top(r: runs.RunView) -> str:
    """A run's first result as `name location`, or the reason it was not answered."""
    if r.status != "ok":
        return r.reason or "-"
    t = r.top
    if not t:
        return "-"
    if t.get("start_line"):
        where = f"{t['path']}:{t['start_line']}-{t['end_line']}"
    elif t.get("line"):
        where = f"{t['path']}:{t['line']}"
    else:
        where = t.get("path", "")
    return f"{t['name']} {where}".rstrip()
