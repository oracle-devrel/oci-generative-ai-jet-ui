"""Helpers for the language tests: parse a file of tests/fixtures/languages/ and read its definitions, docs and
calls.
"""

from pathlib import Path

from golestan_code_mcp.parsing import chunks as parsing_chunks
from golestan_code_mcp.parsing.common import Call

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "languages"


def parsed(language: str, rel: str):
    return parsing_chunks.parse(language, (FIXTURES / rel).read_text(encoding="utf-8"))


def definitions(language: str, rel: str) -> dict[str, tuple]:
    """name -> (kind, start, end, exported)"""
    return {c.name: (c.kind, c.start_line, c.end_line, c.exported) for c in parsed(language, rel)[0]}


def docs(language: str, rel: str) -> dict[str, str]:
    return {c.name: c.doc for c in parsed(language, rel)[0] if c.doc}


def calls(language: str, rel: str) -> set[Call]:
    return set(parsed(language, rel)[1])
