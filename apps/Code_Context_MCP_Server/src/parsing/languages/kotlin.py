"""Kotlin's rules: declarations, calls, imports and KDoc."""

from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Hit, Import


def _kotlin_public(node: Node) -> bool:
    modifiers = common._child(node, "modifiers")
    visibility = common._child(modifiers, "visibility_modifier") if modifiers is not None else None
    return visibility is None or visibility.text.decode() not in ("private", "internal")


def _kotlin_kind(node: Node) -> str:
    if any(c.type == "interface" for c in node.children):
        return "interface"
    return "type" if common._child(node, "enum_class_body") is not None else "class"


def _kotlin(body: Node, prefix: str = "") -> Iterator[Found]:
    for node in body.named_children:
        if node.type in ("class_declaration", "object_declaration"):
            name = prefix + common._name(node)
            yield name, "class" if node.type == "object_declaration" else _kotlin_kind(node), node, _kotlin_public(node)
            if (members := common._child(node, "class_body", "enum_class_body")) is not None:
                yield from _kotlin(members, name + ".")
        elif node.type == "companion_object" and (members := common._child(node, "class_body")) is not None:
            yield from _kotlin(members, prefix)  # transparent: its members are the class's
        elif node.type == "function_declaration" and common._child(node, "function_body") is not None:
            name = node.child_by_field_name("name")
            receiver = next((c for c in node.named_children if c.end_byte <= name.start_byte
                             and c.type in ("user_type", "nullable_type")), None)
            if receiver is not None:  # fun String.slug(): a method of String
                yield f"{receiver.text.decode().rstrip('?').split('<')[0]}.{name.text.decode()}", "method", node, \
                    _kotlin_public(node)
            else:
                yield prefix + name.text.decode(), "method" if prefix else "function", node, _kotlin_public(node)


def _kotlin_call(node: Node) -> Hit:
    if node.type != "call_expression" or not node.named_child_count:
        return None
    callee = node.named_children[0]
    if callee.type == "identifier":
        return callee, "bare", None
    if callee.type == "navigation_expression" and callee.named_children[-1].type == "identifier":
        return callee.named_children[-1], "attr", common._dotted(callee.named_children[0])
    return None


def _kotlin_imports(root: Node) -> Iterator[Import]:
    for node in root.named_children:
        if node.type == "import" and (name := common._child(node, "qualified_identifier", "identifier")):
            wildcard = any(c.type == "*" for c in node.children)
            yield Import(name.text.decode() + (".*" if wildcard else ""), 0, None)


tables.register("kotlin", (".kt", ".kts"), ("tree_sitter_kotlin", "language"), _kotlin,
                common._walk_calls(_kotlin_call), _kotlin_imports, common._block_doc)
