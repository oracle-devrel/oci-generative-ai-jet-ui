"""Java's rules: types, members, calls, imports and Javadoc."""

from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Hit, Import

JAVA_TYPES = {"class_declaration": "class", "record_declaration": "class", "interface_declaration": "interface",
              "annotation_type_declaration": "interface", "enum_declaration": "type"}
JAVA_MEMBERS = {"method_declaration", "constructor_declaration"}


def _java_public(node: Node) -> bool:
    modifiers = common._child(node, "modifiers")
    return modifiers is not None and any(c.type == "public" for c in modifiers.children)


def _java(body: Node, prefix: str = "") -> Iterator[Found]:
    for node in body.named_children:
        if node.type in JAVA_TYPES:
            name = prefix + common._name(node)
            yield name, JAVA_TYPES[node.type], node, _java_public(node)
            members = node.child_by_field_name("body")
            if members is not None:  # an enum's methods sit in its enum_body_declarations
                inner = common._child(members, "enum_body_declarations") if node.type == "enum_declaration" else members
                yield from _java(inner or members, name + ".")
        elif node.type in JAVA_MEMBERS and prefix and node.child_by_field_name("body") is not None:
            yield prefix + common._name(node), "method", node, _java_public(node)


def _java_call(node: Node) -> Hit:
    if node.type == "method_invocation":
        receiver = node.child_by_field_name("object")
        if receiver is None:
            return node.child_by_field_name("name"), "bare", None
        return node.child_by_field_name("name"), "attr", common._dotted(receiver)
    if node.type == "object_creation_expression":
        kind = node.child_by_field_name("type")
        while kind.type in ("generic_type", "scoped_type_identifier"):  # List<String>, a.B
            kind = kind.named_children[-1] if kind.type == "scoped_type_identifier" else kind.named_children[0]
        return kind, "bare", None
    return None


def _java_imports(root: Node) -> Iterator[Import]:
    for node in root.named_children:
        if node.type == "import_declaration" and (name := common._child(node, "scoped_identifier", "identifier")):
            wildcard = any(c.type == "asterisk" for c in node.children)
            yield Import(name.text.decode() + (".*" if wildcard else ""), 0, None)  # types: never bound (R6)


tables.register("java", (".java",), ("tree_sitter_java", "language"), _java, common._walk_calls(_java_call),
                _java_imports, common._block_doc)
