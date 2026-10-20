"""The chunker: definition chunks, line windows, language detection, and what a parse returns."""

import subprocess
import sys

import pytest

from golestan_code_mcp.parsing import chunks as parsing_chunks

from parsing.helpers import FIXTURES, GO_DOCS, PY_DOCS, PY_SOURCE, docs, numbered, spans


def test_crlf_text_matches_lf():
    text = (FIXTURES / "sample.py").read_text(encoding="utf-8")
    assert parsing_chunks.chunk("python", text.replace("\n", "\r\n")) == parsing_chunks.chunk("python", text)


def test_parse_error_returns_none():
    assert parsing_chunks.chunk("python", (FIXTURES / "broken.py").read_text(encoding="utf-8")) is None


def test_unknown_language_returns_none():
    assert parsing_chunks.chunk("cobol", "IDENTIFICATION DIVISION.\n") is None


def test_windows_overlap_and_stop_at_last_line():
    assert spans(numbered(130)) == [
        ("notes.md:1-60", "chunk", 1, 60),
        ("notes.md:51-110", "chunk", 51, 110),
        ("notes.md:101-130", "chunk", 101, 130),
    ]


def test_windows_source_is_the_lines():
    last = parsing_chunks.windows("notes.md", numbered(130))[-1]
    assert last.source == "\n".join(f"line {i}" for i in range(101, 131))


def test_sixty_lines_is_one_window():
    assert spans(numbered(60)) == [("notes.md:1-60", "chunk", 1, 60)]


def test_empty_text_has_no_windows():
    assert parsing_chunks.windows("notes.md", "") == []


@pytest.mark.parametrize(
    ("path", "language"),
    [
        ("pkg/app.py", "python"),
        ("main.go", "go"),
        ("index.js", "javascript"),
        ("lib/mod.MJS", "javascript"),
        ("README.md", "markdown"),
        ("docs/index.rst", "rst"),
        ("data.xyz", "text"),
        ("Makefile", "text"),
    ],
)
def test_detect_language(path, language):
    assert parsing_chunks.detect_language(path) == language


def test_parse_chunks_match_chunk():
    assert parsing_chunks.parse("python", PY_SOURCE)[0] == parsing_chunks.chunk("python", PY_SOURCE)


def test_syntax_error_yields_no_calls_or_imports():
    assert parsing_chunks.parse("python", (FIXTURES / "broken.py").read_text(encoding="utf-8")) is None


def test_doc_is_cut_at_1000_characters():
    symbols, _ = docs("python", f'def f():\n    """{"word " * 400}"""\n')
    assert len(symbols["f"]) <= 1000 and symbols["f"].startswith("word word")


def test_docs_leave_chunks_unchanged():
    lines = GO_DOCS.splitlines()
    for c in parsing_chunks.parse("go", GO_DOCS)[0]:
        assert c.source == "\n".join(lines[c.start_line - 1 : c.end_line])
    assert {(c.name, c.start_line) for c in parsing_chunks.parse("go", GO_DOCS)[0]} >= {("Server", 12), ("Server.Start", 19)}
    assert parsing_chunks.chunk("python", PY_DOCS)[0].source.startswith("def documented")


def test_an_rst_heading_is_skipped_for_the_paragraph_after_it():
    module = '"""\nTagged JSON\n~~~~~~~~~~~\n\nA compact representation for\nnon-standard JSON types.\n"""\n'
    assert parsing_chunks.parse("python", module + "def f():\n    pass\n")[3] == "A compact representation for non-standard JSON types."
    assert parsing_chunks.parse("python", '"""\nOnly a heading\n==============\n"""\n')[3] == "Only a heading =============="


@pytest.mark.parametrize(("language", "text"), [
    ("python", PY_SOURCE), ("go", GO_DOCS), ("javascript", "function f() {}\n")])
def test_parse_returns_namespaces_last(language, text):
    parsed = parsing_chunks.parse(language, text)
    assert len(parsed) == 5 and parsed[4] == []


@pytest.mark.parametrize(("language", "text", "expected"), [
    ("python", "def run():\n    pass\n\n\ndef _hidden():\n    pass\n\n\nclass A:\n    def _m(self):\n        pass\n",
     {"run": True, "_hidden": False, "A": True, "A._m": False}),
    ("go", "package p\n\nfunc Serve() {}\n\nfunc helper() {}\n\ntype T struct{}\n\nfunc (t T) close() {}\n",
     {"Serve": True, "helper": False, "T": True, "T.close": False}),
    ("javascript", "function run() {}\nfunction _hidden() {}\nclass A {\n  _m() {}\n  b() {}\n}\n",
     {"run": True, "_hidden": False, "A": True, "A._m": False, "A.b": True}),
])
def test_exported_follows_the_name_rule(language, text, expected):
    assert {c.name: c.exported for c in parsing_chunks.chunk(language, text)} == expected


def test_windows_have_no_exported():
    assert {c.exported for c in parsing_chunks.windows("x", numbered(70))} == {None}


def test_new_grammars_load_only_when_used():
    code = ("import sys, golestan_code_mcp.parsing.chunks, golestan_code_mcp.indexing.ingest, golestan_code_mcp.server;"
            "print(sorted({m.split('.')[0] for m in sys.modules if m.startswith('tree_sitter_')}))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
    assert out == "[]"  # every grammar loads on the first file of its language


@pytest.mark.parametrize(("language", "source"), [
    ("csharp", "class A\n{\n}\n#pragma warning restore 3016"),  # a generated NSwag client ends like this
    ("cpp", "#ifndef A_H\n#define A_H\nstruct A {\n    int x;\n};\n#endif"),
])
def test_a_directive_on_the_last_line_without_a_newline_parses(language, source):
    chunks = parsing_chunks.parse(language, source)[0]
    assert [(c.name, c.end_line) for c in chunks] == [("A", {"csharp": 3, "cpp": 5}[language])]
