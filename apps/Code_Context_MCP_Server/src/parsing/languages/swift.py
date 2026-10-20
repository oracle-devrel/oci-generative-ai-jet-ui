"""Swift's rules: declarations, calls, imports and doc comments."""

from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Hit, Import

SWIFT_KINDS = {"class": "class", "actor": "class", "struct": "type", "enum": "type"}


def _swift_public(node: Node) -> bool:
    modifiers = common._child(node, "modifiers")
    visibility = common._child(modifiers, "visibility_modifier") if modifiers is not None else None
    return visibility is None or visibility.text.decode().split("(")[0] not in ("private", "fileprivate", "internal")


def _swift(body: Node, prefix: str = "") -> Iterator[Found]:
    for node in body.named_children:
        if node.type == "class_declaration":
            kind = node.child_by_field_name("declaration_kind").text.decode()
            name = node.child_by_field_name("name").text.decode().split("<")[0]
            if kind != "extension":  # an extension is not a definition; its members are the type's
                yield prefix + name, SWIFT_KINDS.get(kind, "class"), node, _swift_public(node)
            if (members := node.child_by_field_name("body")) is not None:
                yield from _swift(members, (prefix if kind != "extension" else "") + name + ".")
        elif node.type == "protocol_declaration":
            yield prefix + common._name(node), "interface", node, _swift_public(node)
        elif node.type == "function_declaration" and node.child_by_field_name("body") is not None:
            yield prefix + common._name(node), "method" if prefix else "function", node, _swift_public(node)
        elif node.type == "init_declaration" and prefix:
            yield prefix + "init", "method", node, _swift_public(node)


def _swift_call(node: Node) -> Hit:
    if node.type != "call_expression" or not node.named_child_count:
        return None
    callee = node.named_children[0]
    if callee.type == "simple_identifier":
        return callee, "bare", None
    if callee.type == "navigation_expression":
        suffix = callee.child_by_field_name("suffix")
        name = suffix.child_by_field_name("suffix") if suffix is not None else None
        if name is not None and name.type == "simple_identifier":
            return name, "attr", common._dotted(callee.child_by_field_name("target"))
    return None


def _swift_imports(root: Node) -> Iterator[Import]:
    for node in root.named_children:
        if node.type == "import_declaration" and (module := common._child(node, "identifier")) is not None:
            yield Import(module.text.decode(), 0, None)  # a module, never a file (FR-014)


def _swift_doc(node: Node, data: bytes) -> str | None:
    lines = [c.text.decode()[3:] for c in common._above(node, data) if c.text.startswith(b"///")]
    return "\n".join(lines) if lines else common._block_doc(node, data)


tables.register("swift", (".swift",), ("tree_sitter_swift", "language"), _swift, common._walk_calls(_swift_call),
                _swift_imports, _swift_doc)
