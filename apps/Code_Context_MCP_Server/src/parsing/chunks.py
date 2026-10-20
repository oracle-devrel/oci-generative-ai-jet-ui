"""Split file text into definition-level chunks with tree-sitter, or into line windows when it does not parse.

The same parse also yields the calls and imports each file makes, for the code graph, and the documentation of
each definition and of the file, for the module wiki.
"""

import importlib
from functools import cache
from pathlib import PurePath

from tree_sitter import Language, Node, Parser

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Call, Chunk, Import


def detect_language(path: str) -> str:
    path = PurePath(path)
    return tables.NAMES.get(path.name) or tables.EXTENSIONS.get(path.suffix.lower(), "text")


@cache
def _parser(language: str) -> Parser:
    module, function = tables.GRAMMARS[language]
    return Parser(Language(getattr(importlib.import_module(module), function)()))


def _start(language: str, node: Node) -> Node:
    """The first of the attribute-like siblings directly above the node, or the node itself."""
    first, kinds = node, tables.LEADING.get(language, ())
    while (prev := first.prev_named_sibling) is not None and prev.type in kinds:
        first = prev
    return first


def parse(language: str, text: str) -> tuple[list[Chunk], list[Call], list[Import], str | None, list[str]] | None:
    """Definition chunks, calls, imports, the file's doc and its declared namespaces, or None when there is no
    grammar or the file does not parse cleanly."""
    if language not in tables.GRAMMARS:
        return None
    data = text.encode("utf-8")
    # a directive on the last line needs its line end (C#'s #pragma, C's #endif); the lines are unchanged by it
    root = _parser(language).parse(data if data.endswith(b"\n") else data + b"\n").root_node
    if root.has_error:
        return None
    lines = text.splitlines()
    chunks, scopes = [], {}
    for name, kind, node, exported in tables.WALKERS[language](root):
        start, end = _start(language, node).start_point.row + 1, node.end_point.row + 1
        doc = common._clean(tables.SYMBOL_DOCS[language](node, data))
        chunks.append(Chunk(name, kind, start, end, "\n".join(lines[start - 1 : end]), doc, exported))
        scopes[common._definition(node).id] = name
    file_doc = tables.FILE_DOCS.get(language)
    calls = tables.CALLS[language](root, scopes) if callable(tables.CALLS[language]) else _calls(language, root, scopes)
    namespaces = tables.NAMESPACES.get(language)
    return (chunks, calls, list(tables.IMPORTS[language](root)),
            common._clean(file_doc(root, data)) if file_doc else None, namespaces(root) if namespaces else [])


def chunk(language: str, text: str) -> list[Chunk] | None:
    """Definition chunks, or None when there is no grammar or the file does not parse cleanly."""
    parsed = parse(language, text)
    return parsed[0] if parsed else None


def windows(name: str, text: str, size: int = 60, step: int = 50) -> list[Chunk]:
    """Overlapping line windows of kind 'chunk', named '<name>:<start>-<end>'."""
    lines = text.splitlines()
    chunks = []
    for start in range(1, len(lines) + 1, step):
        end = min(start + size - 1, len(lines))
        chunks.append(Chunk(f"{name}:{start}-{end}", "chunk", start, end, "\n".join(lines[start - 1 : end])))
        if end == len(lines):
            break
    return chunks


def _calls(language: str, root: Node, scopes: dict[int, str]) -> list[Call]:
    types, attribute, (receiver_field, name_field) = tables.CALLS[language]
    found, stack = [], [(root, None)]
    while stack:
        node, caller = stack.pop()
        caller = scopes.get(node.id, caller)
        callee = node.child_by_field_name(types[node.type]) if node.type in types else None
        if callee is not None and callee.type == "identifier":
            found.append(Call(caller, callee.text.decode(), "bare", None, callee.start_point.row + 1))
        elif callee is not None and callee.type == attribute:
            name, receiver = (callee.child_by_field_name(name_field),
                              common._text(callee.child_by_field_name(receiver_field)))
            dotted = receiver if common.DOTTED.fullmatch(receiver) else None
            found.append(Call(caller, name.text.decode(), "attr", dotted, name.start_point.row + 1))
        stack.extend((child, caller) for child in reversed(node.named_children))
    return sorted(found, key=lambda call: call.line)
