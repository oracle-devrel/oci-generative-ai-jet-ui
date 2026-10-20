"""C's and C++'s rules: one walker; C has no classes, namespaces or templates, so their branches never run for it."""

import re
from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Hit, Import

C_TYPES = {"struct_specifier": "type", "union_specifier": "type", "enum_specifier": "type",
           "class_specifier": "class"}
C_PASS_THROUGH = {"preproc_ifdef", "preproc_if", "preproc_else", "preproc_elif", "preproc_elifdef"}
C_SCOPED = {"namespace_definition", "linkage_specification"}  # their declarations are in their body


def _declared(definition: Node) -> tuple[str | None, str | None]:
    """(the last qualifier, the name) a function definition declares: `app::Engine::start` gives (Engine, start)."""
    node = definition.child_by_field_name("declarator")
    while node is not None and node.type != "function_declarator":  # through pointer and reference declarators
        node = node.child_by_field_name("declarator")
    node = node.child_by_field_name("declarator") if node is not None else None
    scopes = []
    while node is not None and node.type == "qualified_identifier":
        if (scope := node.child_by_field_name("scope")) is not None:
            scopes.append(scope.text.decode().split("<")[0])
        node = node.child_by_field_name("name")
    if node is not None and node.type == "template_function":
        node = node.child_by_field_name("name")
    return (scopes[-1] if scopes else None), (node.text.decode() if node is not None else None)


def _static(node: Node) -> bool:
    return any(c.type == "storage_class_specifier" and c.text == b"static" for c in node.children)


def _c_family(body: Node) -> Iterator[Found]:
    for outer in body.named_children:
        node = common._child(outer, "function_definition", *C_TYPES) if outer.type == "template_declaration" else outer
        if node is None:
            continue
        if node.type in C_PASS_THROUGH:
            yield from _c_family(node)
        elif node.type in C_SCOPED and (inner := node.child_by_field_name("body")) is not None:
            yield from _c_family(inner)  # namespaces are left out of names
        elif node.type == "function_definition":
            owner, name = _declared(node)
            if name:
                yield ((f"{owner}.{name}", "method", outer, True) if owner
                       else (name, "function", outer, not _static(node)))
        elif node.type == "type_definition" and (declarator := node.child_by_field_name("declarator")) is not None:
            yield declarator.text.decode(), "type", outer, True
        elif node.type in C_TYPES or node.type == "declaration":
            yield from _c_type(outer, node if node.type in C_TYPES else common._child(node, *C_TYPES), "", True)


def _c_type(outer: Node, node: Node | None, prefix: str, exported: bool) -> Iterator[Found]:
    """A struct, union, enum or class with a body, and a class's or struct's members by their access sections."""
    if node is None or node.child_by_field_name("body") is None or (name := common._named(node)) is None:
        return
    name = prefix + name
    yield name, C_TYPES[node.type], outer, exported
    if node.type == "enum_specifier":
        return
    public = node.type != "class_specifier"  # a struct's members are public until a section says otherwise
    for member in node.child_by_field_name("body").named_children:
        inner = (common._child(member, "function_definition", *C_TYPES) if member.type == "template_declaration"
                 else member)
        if member.type == "access_specifier":
            public = member.text.decode().strip().rstrip(":") == "public"
        elif inner is not None and inner.type == "function_definition" and (short := _declared(inner)[1]):
            yield f"{name}.{short}", "method", member, public
        elif inner is not None and inner.type in C_TYPES:
            yield from _c_type(member, inner, name + ".", public)
        elif member.type == "field_declaration":
            yield from _c_type(member, common._child(member, *C_TYPES), name + ".", public)


def _c_call(node: Node) -> Hit:
    if node.type == "new_expression" and (kind := node.child_by_field_name("type")) is not None:
        return _c_name(kind), "bare", None
    if node.type != "call_expression":
        return None
    callee = node.child_by_field_name("function")
    if callee.type == "identifier":
        return callee, "bare", None
    if callee.type == "template_function":
        return callee.child_by_field_name("name"), "bare", None
    if callee.type == "field_expression":  # e.start(), this->speed()
        return callee.child_by_field_name("field"), "attr", common._c_receiver(callee.child_by_field_name("argument"))
    if callee.type == "qualified_identifier":  # Helper::run(), std::max(...)
        name = _c_name(callee)
        receiver = callee.text.decode()[: name.start_byte - callee.start_byte].rstrip(":")
        return name, "attr", _c_receiver_text(receiver)
    return None


def _c_name(node: Node) -> Node:
    """The last name of a possibly qualified or templated name."""
    while node.type in ("qualified_identifier", "template_function", "template_type"):
        node = node.child_by_field_name("name")
    return node


def _c_receiver_text(text: str) -> str | None:
    text = text.replace("::", ".")
    return text if common.DOTTED.fullmatch(text) else None


def _c_includes(root: Node) -> Iterator[Import]:
    stack = [root]
    while stack:  # includes may sit in include guards and other preprocessor blocks
        node = stack.pop()
        stack.extend(reversed(node.named_children))
        if node.type == "preproc_include" and (path := node.child_by_field_name("path")) is not None:
            if path.type == "system_lib_string":
                yield Import(path.text.decode(), 0, None)  # <vector>: brackets kept, so it never resolves to a file
            elif (content := common._child(path, "string_content")) is not None:
                yield Import(content.text.decode(), 0, None)


DOXYGEN = (b"///", b"//!", b"/**", b"/*!")


def _doxygen(node: Node, data: bytes) -> str | None:
    """`///`, `//!`, `/** */` and `/*! */` comments directly above, without their markers and tags."""
    comments = [c for c in common._comments_above(node, data) if c.text.startswith(DOXYGEN)]
    if not comments:
        return None
    text = "\n".join(c.text.decode()[3:] if c.text.startswith((b"///", b"//!"))
                     else common._uncomment(c.text.decode()[1:]) if c.text.startswith(b"/*!")
                     else common._uncomment(c.text.decode()) for c in comments)
    return common._until_tag(text)


LICENSE = re.compile(r"^\W*(copyright|spdx-license-identifier|license)", re.IGNORECASE)


def _c_file_doc(root: Node, data: bytes) -> str | None:
    """A block comment opening the file, unless it is a license header."""
    first = root.named_children[0] if root.named_child_count else None
    if first is None or first.type != "comment" or not first.text.startswith(b"/*"):
        return None
    text = common._uncomment(first.text.decode())
    return None if LICENSE.match(text) else text


for _language, _module, _extensions in (("c", "tree_sitter_c", (".c",)),
                                        ("cpp", "tree_sitter_cpp", (".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hh",
                                                                    ".hxx", ".h"))):
    tables.register(_language, _extensions, (_module, "language"), _c_family, common._walk_calls(_c_call), _c_includes,
                    _doxygen, file_doc=_c_file_doc)
