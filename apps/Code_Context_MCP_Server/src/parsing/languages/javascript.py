"""JavaScript's rules: definitions, calls, imports and JSDoc comments."""

from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Import

JS_FUNCTION_VALUES = {"arrow_function", "function_expression", "function", "generator_function"}


def _javascript(root: Node) -> Iterator[Found]:
    for outer in root.named_children:
        node = outer
        if outer.type == "export_statement":
            node = outer.child_by_field_name("declaration") or next(
                (c for c in outer.named_children if c.type in ("function_declaration", "class_declaration")), None
            )
            if node is None:
                continue
        if node.type in ("function_declaration", "generator_function_declaration"):
            yield common._name(node), "function", outer, common._public(common._name(node))
        elif node.type == "class_declaration":
            name = common._name(node)
            yield name, "class", outer, common._public(name)
            for method in node.child_by_field_name("body").named_children:
                if method.type == "method_definition":
                    yield f"{name}.{common._name(method)}", "method", method, common._public(common._name(method))
        elif node.type in ("lexical_declaration", "variable_declaration"):
            for declarator in node.named_children:
                value = declarator.child_by_field_name("value")
                if declarator.type == "variable_declarator" and value and value.type in JS_FUNCTION_VALUES:
                    yield common._name(declarator), "function", outer, common._public(common._name(declarator))


def _js_bound(clause: Node | None) -> list[str]:
    names = []
    for node in clause.named_children if clause else []:
        if node.type == "identifier":
            names.append(node.text.decode())
        elif node.type == "namespace_import":
            names += [c.text.decode() for c in node.named_children]
        elif node.type == "named_imports":
            names += [common._text(s.child_by_field_name("alias") or s.child_by_field_name("name"))
                      for s in node.named_children]
    return names


def _js_imports(root: Node) -> Iterator[Import]:
    stack = [root]
    while stack:
        node = stack.pop()
        stack.extend(reversed(node.named_children))
        if node.type == "import_statement":
            path = node.child_by_field_name("source").text.decode()[1:-1]
            if path.startswith("."):
                bound = _js_bound(next((c for c in node.named_children if c.type == "import_clause"), None))
                yield from (Import(path, 0, name) for name in bound or [None])
        elif node.type == "call_expression" and common._text(node.child_by_field_name("function")) == "require":
            args = node.child_by_field_name("arguments").named_children
            path = args[0].text.decode()[1:-1] if len(args) == 1 and args[0].type == "string" else ""
            if path.startswith("."):
                name = node.parent.child_by_field_name("name") if node.parent.type == "variable_declarator" else None
                yield Import(path, 0, common._text(name) if name is not None and name.type == "identifier" else None)


def _js_doc(node: Node, data: bytes) -> str | None:
    above = common._comments_above(node, data)[-1:]
    return common._uncomment(above[0].text.decode()) if above and above[0].text.startswith(b"/**") else None


# simplified: no JS file docs, read a leading block comment when a JS repository needs it
tables.register("javascript", (".js", ".mjs", ".cjs", ".jsx"), ("tree_sitter_javascript", "language"), _javascript,
                ({"call_expression": "function", "new_expression": "constructor"}, "member_expression",
                 ("object", "property")),
                _js_imports, _js_doc)
