"""Rust's rules: items, impl blocks, calls, use declarations and doc comments."""

from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Hit, Import

RUST_TYPES = {"struct_item": "type", "enum_item": "type", "union_item": "type", "type_item": "type",
              "trait_item": "interface"}


def _rust_public(node: Node) -> bool:
    return common._child(node, "visibility_modifier") is not None


def _rust_type_name(node: Node) -> str:
    """`Stack<T>` is Stack, `a::B` is B."""
    return node.text.decode().split("<")[0].rpartition("::")[2].strip()


def _rust(body: Node) -> Iterator[Found]:
    for node in body.named_children:
        if node.type in RUST_TYPES:
            yield common._name(node), RUST_TYPES[node.type], node, _rust_public(node)
        elif node.type == "function_item":
            yield common._name(node), "function", node, _rust_public(node)
        elif node.type == "impl_item" and (members := node.child_by_field_name("body")) is not None:
            owner = _rust_type_name(node.child_by_field_name("type"))
            of_trait = node.child_by_field_name("trait") is not None  # a trait's methods are as public as it is
            for member in members.named_children:
                if member.type == "function_item":
                    yield f"{owner}.{common._name(member)}", "method", member, of_trait or _rust_public(member)
        elif node.type == "mod_item" and (members := node.child_by_field_name("body")) is not None:
            yield from _rust(members)  # an inline module only groups: left out of names


def _rust_call(node: Node) -> Hit:
    if node.type != "call_expression":  # macro_invocation is not a call (research R7)
        return None
    callee = node.child_by_field_name("function")
    if callee.type == "generic_function":  # f::<T>()
        callee = callee.child_by_field_name("function")
    if callee.type == "identifier":
        return callee, "bare", None
    if callee.type == "field_expression":
        return callee.child_by_field_name("field"), "attr", common._dotted(callee.child_by_field_name("value"))
    if callee.type == "scoped_identifier":  # Circle::new, std::mem::take
        path = callee.child_by_field_name("path")
        return callee.child_by_field_name("name"), "attr", common._c_receiver(path)
    return None


def _rust_imports(root: Node) -> Iterator[Import]:
    for node in root.named_children:
        if node.type == "mod_item" and node.child_by_field_name("body") is None:
            yield Import(common._name(node), 1, None)  # mod x;: a file relative to this module (level 1)
        elif node.type == "use_declaration" and (argument := node.child_by_field_name("argument")) is not None:
            if argument.type == "scoped_use_list":  # use a::b::{C, d}: the module a::b
                argument = argument.child_by_field_name("path") or argument
            path = argument.text.decode().split(" as ")[0].removesuffix("::*")
            last = path.rpartition("::")[2]
            yield Import(path, 0, last if last[:1].islower() and last not in ("self", "super", "crate") else None)


def _rust_docs(comments: list[Node], marker: str) -> str | None:
    lines = [c.child_by_field_name("doc").text.decode() for c in comments
             if common._child(c, marker) is not None and c.child_by_field_name("doc") is not None]
    return "\n".join(lines) if lines else None


def _rust_doc(node: Node, data: bytes) -> str | None:
    """`///` comments above the definition, above its attributes."""
    start = node
    while (prev := start.prev_named_sibling) is not None and prev.type == "attribute_item":
        start = prev
    return _rust_docs(common._above(start, data), "outer_doc_comment_marker")


def _rust_file_doc(root: Node, data: bytes) -> str | None:
    """The `//!` comments opening the file."""
    opening = []
    for node in root.named_children:
        if node.type not in ("line_comment", "block_comment"):
            break
        opening.append(node)
    return _rust_docs(opening, "inner_doc_comment_marker")


tables.register("rust", (".rs",), ("tree_sitter_rust", "language"), _rust, common._walk_calls(_rust_call),
                _rust_imports, _rust_doc, file_doc=_rust_file_doc, leading={"attribute_item"})
