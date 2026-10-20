"""C#'s rules: types, members, namespaces, using directives and XML doc comments."""

import re
from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Hit, Import

CS_TYPES = {"class_declaration": "class", "record_declaration": "class", "interface_declaration": "interface",
            "struct_declaration": "type", "record_struct_declaration": "type", "enum_declaration": "type"}
CS_MEMBERS = {"method_declaration", "constructor_declaration"}
CS_NAMESPACES = {"namespace_declaration", "file_scoped_namespace_declaration"}


def _csharp(body: Node, prefix: str = "") -> Iterator[Found]:
    for node in body.named_children:
        if node.type in CS_NAMESPACES:  # left out of names; a file-scoped one's declarations are its siblings
            yield from _csharp(node.child_by_field_name("body") or node, prefix)
        elif node.type in CS_TYPES:
            name = prefix + common._name(node)
            yield name, CS_TYPES[node.type], node, "public" in common._modifiers(node)
            members = node.child_by_field_name("body")
            if members is not None and node.type != "enum_declaration":
                yield from _csharp(members, name + ".")
        elif node.type in CS_MEMBERS and prefix and common._child(node, "block", "arrow_expression_clause"):
            # bodiless members are not
            yield prefix + common._name(node), "method", node, "public" in common._modifiers(node)


def _identifier(node: Node) -> Node:
    """The name node of a possibly generic (`List<int>`) or qualified (`System.Text.Builder`) name."""
    if node.type == "generic_name":
        return common._child(node, "identifier") or node
    if node.type == "qualified_name":
        return _identifier(node.child_by_field_name("name"))
    return node


def _csharp_call(node: Node) -> Hit:
    if node.type == "object_creation_expression":  # new T(...) reaches the class T
        return _identifier(node.child_by_field_name("type")), "bare", None
    if node.type != "invocation_expression":
        return None
    callee = node.child_by_field_name("function")
    if callee.type in ("identifier", "generic_name"):
        return _identifier(callee), "bare", None
    if callee.type == "member_access_expression":
        return (_identifier(callee.child_by_field_name("name")), "attr",
                common._dotted(callee.child_by_field_name("expression")))
    if callee.type == "conditional_access_expression":  # x?.M()
        binding = common._child(callee, "member_binding_expression")
        if binding is not None:
            return _identifier(binding.child_by_field_name("name")), "attr", common._dotted(
                callee.child_by_field_name("condition"))
    return None


def _csharp_scopes(root: Node) -> Iterator[Node]:
    """The compilation unit's and every namespace body's direct children."""
    for node in root.named_children:
        yield node
        if node.type in CS_NAMESPACES and (body := node.child_by_field_name("body")) is not None:
            yield from _csharp_scopes(body)


def _csharp_imports(root: Node) -> Iterator[Import]:
    for node in _csharp_scopes(root):
        if node.type == "using_directive":
            alias = node.child_by_field_name("name")
            target = next((c for c in node.named_children if (alias is None or c.id != alias.id)
                           and c.type in ("qualified_name", "identifier", "generic_name", "alias_qualified_name")), None)
            if target is not None:
                yield Import(target.text.decode(), 0, None)  # a type, not a module: never bound (research R6)


def _csharp_namespaces(root: Node, prefix: str = "") -> list[str]:
    found = []
    for node in root.named_children:
        if node.type in CS_NAMESPACES:
            name = prefix + node.child_by_field_name("name").text.decode()
            found.append(name)
            if (body := node.child_by_field_name("body")) is not None:
                found += _csharp_namespaces(body, name + ".")
    return found


XML_REF = re.compile(r"""<(?:see|seealso|paramref|typeparamref)\s+\w+\s*=\s*["']([^"']*)["']\s*/>""")
XML_TAG = re.compile(r"<[^>]+>")


def _csharp_doc(node: Node, data: bytes) -> str | None:
    """The text of a `///` XML doc's <summary> (or of the whole comment without one), its references as names."""
    lines = [c.text.decode()[3:] for c in common._comments_above(node, data) if c.text.startswith(b"///")]
    if not lines:
        return None
    xml = "\n".join(lines)
    summary = re.search(r"<summary>(.*?)</summary>", xml, re.S)
    text = XML_REF.sub(lambda m: m.group(1).rpartition(":")[2], summary.group(1) if summary else xml)
    return XML_TAG.sub("", text)


tables.register("csharp", (".cs",), ("tree_sitter_c_sharp", "language"), _csharp, common._walk_calls(_csharp_call),
                _csharp_imports, _csharp_doc, namespaces=_csharp_namespaces)
