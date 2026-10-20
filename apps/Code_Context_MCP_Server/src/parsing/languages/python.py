"""Python's rules: definitions, calls, imports and docstrings."""

from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Import


def _python(body: Node, prefix: str = "") -> Iterator[Found]:
    for outer in body.named_children:
        node = outer.child_by_field_name("definition") if outer.type == "decorated_definition" else outer
        if node.type == "function_definition":
            yield (prefix + common._name(node), "method" if prefix else "function", outer,
                   common._public(common._name(node)))
        elif node.type == "class_definition":
            name = prefix + common._name(node)
            yield name, "class", outer, common._public(common._name(node))
            yield from _python(node.child_by_field_name("body"), name + ".")


def _python_imports(root: Node) -> Iterator[Import]:
    for node in root.named_children:
        if node.type == "import_statement":
            for item in node.children_by_field_name("name"):
                dotted = item.child_by_field_name("name") if item.type == "aliased_import" else item
                module = dotted.text.decode()
                yield Import(module, 0, common._text(item.child_by_field_name("alias")) or module.split(".")[0])
        elif node.type == "import_from_statement":
            source = node.child_by_field_name("module_name")
            level, module = 0, source.text.decode()
            if source.type == "relative_import":
                level = len(source.named_children[0].text)
                module = common._text(next((c for c in source.named_children if c.type == "dotted_name"), None)) or ""
            names = node.children_by_field_name("name")
            if not names and module:  # from m import *
                yield Import(module, level, None)
            for item in names:
                dotted = item.child_by_field_name("name") if item.type == "aliased_import" else item
                member = dotted.text.decode()
                # The member may be a submodule, so the module names it; resolution falls back to its parent.
                full = f"{module}.{member}" if module else member
                yield Import(full, level, common._text(item.child_by_field_name("alias")) or member)


tables.register("python", (".py",), ("tree_sitter_python", "language"), _python,
                ({"call": "function"}, "attribute", ("object", "attribute")), _python_imports,
                lambda node, data: common._docstring(common._definition(node).child_by_field_name("body")),
                file_doc=lambda root, data: common._docstring(root))
