"""ccctx output: plain-text tables, and the summary an ingest prints."""

from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.memory import consolidate
from golestan_code_mcp.wiki import build

SKIP_ORDER = ["ignored", "vendored", "binary", "too large"]


def format_table(header: tuple[str, ...], rows: list[tuple], numeric: frozenset[int] = frozenset()) -> str:
    """Two-space separated columns; columns in `numeric` are right-aligned."""
    table = [header] + [tuple(str(v) for v in row) for row in rows]
    widths = [max(len(row[i]) for row in table) for i in range(len(header))]
    return "\n".join(
        "  ".join(v.rjust(w) if i in numeric else v.ljust(w) for i, (v, w) in enumerate(zip(row, widths))).rstrip()
        for row in table
    )


def format_summary(s: indexing_ingest.Summary) -> str:
    if s.mode == "current":
        text = f"{s.repo} is already up to date at {s.commit[:12]}; run with --full to re-index anyway"
    else:
        text = _format_incremental(s) if s.mode == "incremental" else _format_full(s)
        text = text if s.wiki is None else "\n".join([text, *_format_wiki(s.wiki)])
    return "\n".join([text, *_format_memory(s.memory)])


def _format_memory(m: consolidate.Consolidation | str | None) -> list[str]:
    """The Memory line: only when consolidation read a run or changed a fact, or failed."""
    if isinstance(m, str):
        return [f"{'Memory':<9} not consolidated: {m}"]
    if m is None or not (m.runs or m.created or m.merged or m.weakened or m.stale or m.reasked):
        return []
    return [f"{'Memory':<9} {m.runs} runs read, {m.created} created, {m.merged} merged, {m.weakened} weakened,"
            f" {m.stale} stale, {m.reasked} re-asked"]


def _format_wiki(w: build.Refresh) -> list[str]:
    done = "not recompiled" if w.error else "recompiled"
    return [f"{'Wiki':<9} {page} stale: {reason}, {done}" for page, reason in w.stale] + [
        (f"{'Wiki':<9} {len(w.stale)} stale, {0 if w.error else w.recompiled} recompiled, {w.added} added,"
         f" {w.removed} removed")]


def _format_full(s: indexing_ingest.Summary) -> str:
    skipped = sum(s.skipped.values())
    width = max(len(f"{n:,}") for n in (s.scanned, skipped, s.symbols))
    reasons = ", ".join(f"{s.skipped[r]} {r}" for r in SKIP_ORDER if s.skipped[r])
    lines = [
        f"Scanned {s.scanned:>{width},} files",
        f"Skipped {skipped:>{width},} files" + (f" ({reasons})" if reasons else ""),
        f"Indexed {s.symbols:>{width},} symbols in {s.seconds:.1f}s",
    ]
    if s.no_grammar or s.parse_errors:
        lines.append(
            f"Fallback {s.no_grammar + s.parse_errors:>{width - 1},} files as line windows"
            f" ({s.no_grammar} no grammar, {s.parse_errors} parse errors)"
        )
    return "\n".join(lines)


def _format_incremental(s: indexing_ingest.Summary) -> str:
    reasons = ", ".join(f"{s.skipped[r]} {r}" for r in SKIP_ORDER if s.skipped[r])
    rows = [
        ("Changed", s.added + s.changed + s.removed,
         f" files ({s.added} added, {s.changed} changed, {s.removed} removed)"),
        ("Unchanged", s.unchanged, " files"),
        ("Skipped", sum(s.skipped.values()), " files" + (f" ({reasons})" if reasons else "")),
        ("Indexed", s.symbols, f" symbols in {s.seconds:.1f}s"),
    ]
    if s.reparsed:  # files read again only because their language gained rules (012 contracts/cli.md)
        by = ", ".join(f"{n} {lang}" for lang, n in sorted(s.reparsed.items(), key=lambda kv: (-kv[1], kv[0])))
        rows.append(("Reparsed", s.reparsed.total(), f" files whose language is now understood ({by})"))
    if s.no_grammar or s.parse_errors:
        rows.append(("Fallback", s.no_grammar + s.parse_errors,
                     f" files as line windows ({s.no_grammar} no grammar, {s.parse_errors} parse errors)"))
    width = max(len(f"{n:,}") for _, n, _ in rows)
    return "\n".join(f"{label:<9} {n:>{width},}{rest}" for label, n, rest in rows)
