"""Helpers for the chunker's tests: the fixtures folder, and a parse's outline, calls and imports, and docs."""

from pathlib import Path

from golestan_code_mcp.parsing import chunks as parsing_chunks

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def outline(language: str, name: str) -> set[tuple[str, str, int, int]]:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    chunks = parsing_chunks.chunk(language, text)
    assert chunks is not None
    lines = text.splitlines()
    for c in chunks:
        assert c.source == "\n".join(lines[c.start_line - 1 : c.end_line])
    return {(c.name, c.kind, c.start_line, c.end_line) for c in chunks}


def spans(text: str) -> list[tuple[str, str, int, int]]:
    return [(c.name, c.kind, c.start_line, c.end_line) for c in parsing_chunks.windows("notes.md", text)]


def numbered(n: int) -> str:
    return "".join(f"line {i}\n" for i in range(1, n + 1))


PY_SOURCE = """\
import a.b
from a.b import c
from . import x
from ..m import y as z
from q import *

def helper():
    return 1


@register("k")
def handler():
    # helper() in a comment
    \"\"\"helper() in a docstring\"\"\"
    s = "helper() in a string"
    def inner():
        return a.b.join("p")
    return helper()


class Box:
    size = compute()

    def grow(self):
        self.shrink()
        f = lambda: tally()
"""


def refs(language: str, text: str) -> tuple[set[tuple], set[tuple]]:
    _, calls, imports, _, _ = parsing_chunks.parse(language, text)
    return {tuple(c) for c in calls}, {tuple(i) for i in imports}


# --- docs (009 research R2) ----------------------------------------------------------------------------------


def docs(language: str, text: str) -> tuple[dict[str, str | None], str | None]:
    chunks, _, _, file_doc, _ = parsing_chunks.parse(language, text)
    return {c.name: c.doc for c in chunks}, file_doc


PY_DOCS = '''\
"""Tools for widgets.

Second paragraph, never stored.
"""
import os


def documented():
    """Make   a widget
    from parts.

    More detail.
    """
    return 1


def bare():
    return """not a docstring"""


class Box:
    r\'\'\'A box.\'\'\'

    def open(self):
        # a comment first
        "Open it."
'''

GO_DOCS = """\
// Copyright 2026 someone. Not attached: a blank line follows.

//go:build linux
// Package server serves widgets.
//
// Second paragraph.
package server

// Server holds the state.
// It is
//   shared.
type Server struct{}

// Not attached: a blank line follows.

func Bare() {}

/* Block doc for Start. */
func (s *Server) Start() {}

type (
	// Point is a point.
	Point struct{}
	Shape interface{}
)

var x = 1 // trailing, not a doc
func After() {}
"""
