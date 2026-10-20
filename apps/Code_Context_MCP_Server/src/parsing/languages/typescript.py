"""TypeScript's and TSX's rules: the JavaScript rules, plus TypeScript's declarations."""

from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Import
from golestan_code_mcp.parsing.languages import javascript

JS_CALLS = tables.CALLS["javascript"]  # TypeScript calls look like JavaScript's


TS_TYPES = {"interface_declaration": "interface", "type_alias_declaration": "type", "enum_declaration": "type"}
TS_CLASSES = {"class_declaration", "abstract_class_declaration"}
TS_FUNCTIONS = {"function_declaration", "generator_function_declaration"}


def _typescript(root: Node) -> Iterator[Found]:
    for outer in root.named_children:
        node, exported = outer, False
        if outer.type == "export_statement":
            node, exported = (outer.child_by_field_name("declaration")
                              or common._child(outer, *TS_CLASSES, *TS_FUNCTIONS)), True
        if node is None:
            continue
        if node.type in ("lexical_declaration", "variable_declaration"):
            for declarator in node.named_children:
                value = declarator.child_by_field_name("value")
                if declarator.type == "variable_declarator" and value and value.type in javascript.JS_FUNCTION_VALUES:
                    yield common._name(declarator), "function", outer, exported
            continue
        if (name := common._named(node)) is None:
            continue
        if node.type in TS_FUNCTIONS:
            yield name, "function", outer, exported
        elif node.type in TS_TYPES:
            yield name, TS_TYPES[node.type], outer, exported
        elif node.type in TS_CLASSES:
            yield name, "class", outer, exported
            for method in node.child_by_field_name("body").named_children:
                if method.type == "method_definition" and (short := common._named(method)):
                    access = common._child(method, "accessibility_modifier")
                    private = short.startswith("#") or (access is not None and access.text == b"private")
                    yield f"{name}.{short}", "method", method, not private


def _typescript_imports(root: Node) -> Iterator[Import]:
    yield from javascript._js_imports(root)
    for node in root.named_children:  # export ... from "./x" re-exports what it names
        if node.type == "export_statement" and (source := node.child_by_field_name("source")) is not None:
            path = source.text.decode()[1:-1]
            if path.startswith("."):
                yield Import(path, 0, None)


for _language, _grammar, _extensions in (("typescript", "language_typescript", (".ts", ".mts", ".cts")),
                                         ("tsx", "language_tsx", (".tsx",))):
    tables.register(_language, _extensions, ("tree_sitter_typescript", _grammar), _typescript, JS_CALLS,
                    _typescript_imports, lambda node, data: common._until_tag(javascript._js_doc(node, data)))
