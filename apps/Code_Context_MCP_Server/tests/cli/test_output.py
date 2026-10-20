"""ccctx output: tables, and the summaries of a full, incremental or current ingest."""

from collections import Counter
from dataclasses import replace

from golestan_code_mcp.cli import output
from golestan_code_mcp.memory import consolidate

from cli.helpers import summary


def test_format_table():
    rows = [("flask", "/r/flask", 0, 0), ("gin", "/r/gin", 12, 3456)]
    assert output.format_table(("NAME", "PATH", "FILES", "SYMBOLS"), rows, frozenset({2, 3})).splitlines() == [
        "NAME   PATH      FILES  SYMBOLS",
        "flask  /r/flask      0        0",
        "gin    /r/gin       12     3456",
    ]


def test_format_summary_matches_request():
    s = summary({"ignored": 12, "binary": 24, "too large": 2})
    assert output.format_summary(s).splitlines() == [
        "Scanned   214 files",
        "Skipped    38 files (12 ignored, 24 binary, 2 too large)",
        "Indexed 1,847 symbols in 9.2s",
    ]


def test_format_summary_fallback_and_reason_order():
    s = summary({"too large": 1, "vendored": 3}, no_grammar=15, parse_errors=2, files=20, symbols=40)
    assert output.format_summary(s).splitlines() == [
        "Scanned 24 files",
        "Skipped  4 files (3 vendored, 1 too large)",
        "Indexed 40 symbols in 9.2s",
        "Fallback 17 files as line windows (15 no grammar, 2 parse errors)",
    ]


def test_format_summary_nothing_skipped():
    assert output.format_summary(summary(files=3, symbols=5)).splitlines()[1] == "Skipped 0 files"


# --- incremental ingest (006) -------------------------------------------------------------------------------


def test_format_incremental_summary():
    s = replace(summary(no_grammar=3, files=8, symbols=84), mode="incremental",
                added=2, changed=6, removed=1, unchanged=227)
    assert output.format_summary(s).splitlines() == [
        "Changed     9 files (2 added, 6 changed, 1 removed)",
        "Unchanged 227 files",
        "Skipped     0 files",
        "Indexed    84 symbols in 9.2s",
        "Fallback    3 files as line windows (3 no grammar, 0 parse errors)",
    ]


def test_format_up_to_date():
    s = replace(summary(files=0, symbols=0), commit="0123456789ab" + "c" * 28, mode="current", unchanged=176)
    assert output.format_summary(s) == "flask is already up to date at 0123456789ab; run with --full to re-index anyway"


def test_ingest_summary_wiki_lines():
    from golestan_code_mcp.wiki.build import Refresh

    s = replace(summary(), mode="incremental", added=0, changed=1, removed=0, unchanged=3,
                wiki=Refresh([("flask/json", "dumps changed (5f2c1a9e04b7 -> 9e0d3c1b2a47)")], 1))
    assert output.format_summary(s).splitlines()[-2:] == [
        "Wiki      flask/json stale: dumps changed (5f2c1a9e04b7 -> 9e0d3c1b2a47), recompiled",
        "Wiki      1 stale, 1 recompiled, 0 added, 0 removed",
    ]
    failed = replace(s, wiki=Refresh([("flask/json", "dumps is gone")], error="boom"))
    assert output.format_summary(failed).splitlines()[-2] == "Wiki      flask/json stale: dumps is gone, not recompiled"
    assert output.format_summary(replace(s, wiki=Refresh([]))).splitlines()[-1] == \
        "Wiki      0 stale, 0 recompiled, 0 added, 0 removed"
    assert "Wiki" not in output.format_summary(replace(s, wiki=None))


def test_ingest_summary_memory_line():
    quiet = consolidate.Consolidation("r")
    busy = consolidate.Consolidation("r", runs=3, created=1, merged=2, stale=1, reasked=2)
    assert "Memory" not in output.format_summary(replace(summary(), memory=quiet))
    assert output.format_summary(replace(summary(), memory=None)) == output.format_summary(summary())
    assert output.format_summary(replace(summary(), memory=busy)).splitlines()[-1] == (
        "Memory    3 runs read, 1 created, 2 merged, 0 weakened, 1 stale, 2 re-asked")
    assert output.format_summary(replace(summary(), memory="memory down")).splitlines()[-1] == (
        "Memory    not consolidated: memory down")
    current = replace(summary(), mode="current", commit="a" * 40, memory=busy)
    assert output.format_summary(current).splitlines()[1].startswith("Memory    3 runs read")


# --- language coverage (012, US3): the Reparsed line ---


def test_incremental_summary_reports_reparsed_files():
    s = replace(summary(parse_errors=1, files=48, symbols=412), mode="incremental", added=0, changed=48, removed=0,
                unchanged=51, reparsed=Counter(typescript=2, csharp=46))
    assert output.format_summary(s).splitlines() == [
        "Changed    48 files (0 added, 48 changed, 0 removed)",
        "Unchanged  51 files",
        "Skipped     0 files",
        "Indexed   412 symbols in 9.2s",
        "Reparsed   48 files whose language is now understood (46 csharp, 2 typescript)",
        "Fallback    1 files as line windows (0 no grammar, 1 parse errors)",
    ]
    tie = replace(s, reparsed=Counter(rust=1, java=1))
    assert "(1 java, 1 rust)" in output.format_summary(tie)


def test_no_reparsed_line_without_reparsed_files():
    s = replace(summary(files=8, symbols=84), mode="incremental", added=2, changed=6, removed=0, unchanged=227)
    assert not any(line.startswith("Reparsed") for line in output.format_summary(s).splitlines())
