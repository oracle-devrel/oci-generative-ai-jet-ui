"""PHP's rules: declarations, calls, use and require, and PHPDoc."""

from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Hit, Import

PHP_TYPES = {"class_declaration": "class", "interface_declaration": "interface", "trait_declaration": "interface",
             "enum_declaration": "type"}
PHP_REQUIRES = {"require_expression", "require_once_expression", "include_expression", "include_once_expression"}


def _php_public(node: Node) -> bool:
    visibility = common._child(node, "visibility_modifier")
    return visibility is None or visibility.text == b"public"  # a method without one is public


def _php(body: Node, prefix: str = "") -> Iterator[Found]:
    for node in body.named_children:
        if node.type == "namespace_definition" and (inner := node.child_by_field_name("body")) is not None:
            yield from _php(inner, prefix)  # namespace X { }; a statement namespace's declarations are siblings
        elif node.type in PHP_TYPES and (name := common._named(node)):
            yield prefix + name, PHP_TYPES[node.type], node, True
            if (members := node.child_by_field_name("body")) is not None:
                yield from _php(members, prefix + name + ".")
        elif node.type == "method_declaration" and node.child_by_field_name("body") is not None:
            yield prefix + common._name(node), "method", node, _php_public(node)
        elif node.type == "function_definition":
            yield prefix + common._name(node), "method" if prefix else "function", node, True


def _php_receiver(node: Node | None) -> str | None:
    """`$this` is this, `$a->b` is a.b, `A\\B` is A.B."""
    if node is None:
        return None
    text = node.text.decode().replace("->", ".").replace("::", ".").replace("\\", ".").replace("$", "").strip(".")
    return text if common.DOTTED.fullmatch(text) else None


def _php_last(node: Node) -> Node:
    """The last name of a possibly qualified name."""
    return common._child(node, "name") or node if node.type == "qualified_name" else node


def _php_call(node: Node) -> Hit:
    if node.type == "function_call_expression":
        return _php_last(node.child_by_field_name("function")), "bare", None
    if node.type in ("member_call_expression", "nullsafe_member_call_expression"):
        return node.child_by_field_name("name"), "attr", _php_receiver(node.child_by_field_name("object"))
    if node.type == "scoped_call_expression":  # Helper::get(), self::x(), parent::x()
        return node.child_by_field_name("name"), "attr", _php_receiver(node.child_by_field_name("scope"))
    if node.type == "object_creation_expression" and (
            kind := common._child(node, "name", "qualified_name")) is not None:
        return _php_last(kind), "bare", None
    return None


def _php_string(node: Node | None) -> str | None:
    if node is not None and node.type in ("string", "encapsed_string") and (
            content := common._child(node, "string_content")):
        return content.text.decode()
    return None


def _php_path(argument: Node) -> str | None:
    """A literal path, or `__DIR__ . '/x'` / `dirname(__FILE__) . '/x'`: relative to the file either way."""
    if (literal := _php_string(argument)) is not None:
        return literal
    if argument.type == "binary_expression":
        right = _php_string(argument.child_by_field_name("right"))
        return right.lstrip("/") if right else None
    return None


def _php_imports(root: Node) -> Iterator[Import]:
    stack = [root]
    while stack:
        node = stack.pop()
        stack.extend(reversed(node.named_children))
        if node.type == "namespace_use_declaration":
            for clause in node.named_children:
                if clause.type == "namespace_use_clause" and (name := common._child(clause, "qualified_name", "name")):
                    yield Import(name.text.decode().lstrip("\\"), 0, None)
        elif node.type in PHP_REQUIRES and node.named_child_count and (path := _php_path(node.named_children[0])):
            yield Import(path, 1, None)  # level 1: relative to the requiring file


def _php_file_doc(root: Node, data: bytes) -> str | None:
    """A `/** */` docblock right after `<?php`, before the first declaration."""
    first = next((c for c in root.named_children if c.type != "php_tag"), None)
    if first is None or first.type != "comment" or not first.text.startswith(b"/**"):
        return None
    following = first.next_named_sibling
    if following is not None and following.type in (*PHP_TYPES, "function_definition"):
        return None  # it documents that declaration, not the file
    return common._until_tag(common._uncomment(first.text.decode()))


tables.register("php", (".php",), ("tree_sitter_php", "language_php"), _php, common._walk_calls(_php_call),
                _php_imports, common._block_doc, file_doc=_php_file_doc)
