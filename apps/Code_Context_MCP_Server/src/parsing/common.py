"""What the chunker and every language share: the chunk, call and import types, tree helpers, and doc cleaning."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import NamedTuple

from tree_sitter import Node

# (name, kind, node whose lines form the chunk, whether its language counts it as public)
Found = tuple[str, str, Node, bool]


@dataclass(frozen=True)
class Chunk:
    name: str
    kind: str
    start_line: int
    end_line: int
    source: str
    doc: str | None = None  # the first paragraph of its documentation, cleaned (see _clean)
    exported: bool | None = None  # public in its language (research R9); None for a line window


class Call(NamedTuple):
    caller: str | None  # qualified name of the innermost enclosing symbol, None at module level
    name: str  # the called name, last component only
    form: str  # 'bare' for x(...), 'attr' for r.x(...)
    receiver: str | None  # the dotted text of r for an attr call, None when r is not a dotted name
    line: int


class Import(NamedTuple):
    module: str  # dotted Python module (a from-import appends the member), Go import path, or JS relative path
    rel_level: int  # leading dots of a Python relative import
    bound: str | None  # the name the import binds in the file


def _name(node: Node) -> str:
    return node.child_by_field_name("name").text.decode()


DOTTED = re.compile(r"[\w.]+")


def _definition(node: Node) -> Node:
    # Decorators run where the function is defined, so their calls belong to the enclosing scope.
    return node.child_by_field_name("definition") if node.type == "decorated_definition" else node


def _text(node: Node | None) -> str | None:
    return node.text.decode() if node is not None else None


DOC_LIMIT = 1000
UNDERLINE = re.compile(r"^\s*([=\-~^\"'#*+])\1{2,}\s*$")  # an RST heading's underline
QUOTES = re.compile(r"""^[A-Za-z]*(\"\"\"|'''|"|')|(\"\"\"|'''|"|')$""")


def _clean(raw: str | None) -> str | None:
    """The first paragraph of a doc that is not an RST heading, with its whitespace collapsed, at most DOC_LIMIT
    characters; None if empty. `Tagged JSON` over `~~~~` names a module; the paragraph after it says what it does."""
    paragraphs, current = [], []
    for line in [*(raw or "").splitlines(), ""]:
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append(current)
            current = []
    body = next((p for p in paragraphs if not UNDERLINE.match(p[-1])), paragraphs[0] if paragraphs else [])
    return " ".join(" ".join(body).split())[:DOC_LIMIT].rstrip() or None


def _docstring(block: Node | None) -> str | None:
    """The string a Python body or module starts with, without its quotes."""
    first = next((c for c in block.named_children if c.type != "comment"), None) if block else None
    if first is None or first.type != "expression_statement" or first.named_child_count != 1:
        return None
    string = first.named_children[0]
    return QUOTES.sub("", string.text.decode()) if string.type == "string" else None


def _alone(data: bytes, node: Node) -> bool:
    """Whether only whitespace comes before the node on its first line."""
    return not data[data.rfind(b"\n", 0, node.start_byte) + 1 : node.start_byte].strip()


def _comments_above(node: Node, data: bytes) -> list[Node]:
    """The run of comments ending on the line just above the node, each on lines of its own, in source order."""
    run, line, prev = [], node.start_point.row, node.prev_named_sibling
    while prev is not None and prev.type == "comment" and prev.end_point.row == line - 1 and _alone(data, prev):
        run.append(prev)
        line, prev = prev.start_point.row, prev.prev_named_sibling
    return run[::-1]


def _uncomment(comment: str) -> str:
    if comment.startswith("//"):
        return comment[2:]
    body = comment.removeprefix("/*").removesuffix("*/").lstrip("*")  # /* */ and /** */
    return "\n".join(re.sub(r"^\s*\*", "", line) for line in body.splitlines())


# What a call visitor returns for a call node: (the node of the called name, 'bare' or 'attr', the dotted receiver)
Hit = tuple[Node, str, str | None] | None


def _walk_calls(visit: Callable[[Node], Hit]) -> Callable[[Node, dict[int, str]], list[Call]]:
    """A language's call extractor from a visitor that recognizes its call nodes. Comments and strings hold no call
    nodes, so they never count (FR-010)."""
    def calls(root: Node, scopes: dict[int, str]) -> list[Call]:
        found, stack = [], [(root, None)]
        while stack:
            node, caller = stack.pop()
            caller = scopes.get(node.id, caller)
            if (hit := visit(node)) is not None:
                name, form, receiver = hit
                found.append(Call(caller, name.text.decode(), form, receiver, name.start_point.row + 1))
            stack.extend((child, caller) for child in reversed(node.named_children))
        return sorted(found, key=lambda call: call.line)
    return calls


def _dotted(node: Node | None) -> str | None:
    """The receiver's text when it is a dotted name (`a.b`, `this`), else None."""
    text = node.text.decode() if node is not None else ""
    return text if DOTTED.fullmatch(text) else None


def _child(node: Node, *types: str) -> Node | None:
    return next((c for c in node.named_children if c.type in types), None)


COMMENTS = {"comment", "block_comment", "line_comment"}  # what the grammars call a comment


def _above(node: Node, data: bytes) -> list[Node]:
    """_comments_above, for every grammar's comment types. A Rust line comment ends at the start of the next
    line, so its last line is the one before when it ends in column 0."""
    run, line, prev = [], node.start_point.row, node.prev_named_sibling
    while prev is not None and prev.type in COMMENTS and _alone(data, prev):
        end = prev.end_point.row - (1 if prev.end_point.column == 0 and prev.end_point.row > prev.start_point.row
                                    else 0)
        if end != line - 1:
            break
        run.append(prev)
        line, prev = prev.start_point.row, prev.prev_named_sibling
    return run[::-1]


def _modifiers(node: Node) -> set[str]:
    return {c.text.decode() for c in node.children if c.type == "modifier"}


def _block_doc(node: Node, data: bytes) -> str | None:
    """The `/** */` comment directly above, without its markers and tags (Javadoc, KDoc, PHPDoc)."""
    above = _above(node, data)[-1:]
    return _until_tag(_uncomment(above[0].text.decode())) if above and above[0].text.startswith(b"/**") else None


def _public(name: str) -> bool:
    """Python's and JavaScript's rule: a leading underscore marks a name private."""
    return not name.startswith("_")


def _named(node: Node | None) -> str | None:
    """A node's name, or None for an anonymous one (`export default function () {}`)."""
    name = node.child_by_field_name("name") if node is not None else None
    return name.text.decode() if name is not None else None


def _until_tag(text: str | None) -> str | None:
    """A doc comment's description: the lines before its first `@param`-style (or `\\param`) tag."""
    if text is None:
        return None
    lines = []
    for line in text.splitlines():
        if line.strip().startswith(("@", "\\")):
            break
        lines.append(line)
    return "\n".join(lines)


def _c_receiver(node: Node | None) -> str | None:
    """A receiver with `->` and `::` written as dots, when it is a dotted name."""
    if node is None:
        return None
    text = node.text.decode().replace("->", ".").replace("::", ".")
    return text if DOTTED.fullmatch(text) else None
