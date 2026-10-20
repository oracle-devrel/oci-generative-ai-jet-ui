"""Go's rules: definitions, receivers, imports and doc comments."""

from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Import


def _go_receiver(node: Node) -> str:
    receiver = node.child_by_field_name("receiver").named_children[0].child_by_field_name("type")
    return receiver.text.decode().lstrip("*").split("[")[0].strip()


def _go_public(name: str) -> bool:
    return name[:1].isupper()


def _go(root: Node) -> Iterator[Found]:
    for node in root.named_children:
        if node.type == "function_declaration":
            yield common._name(node), "function", node, _go_public(common._name(node))
        elif node.type == "method_declaration":
            yield f"{_go_receiver(node)}.{common._name(node)}", "method", node, _go_public(common._name(node))
        elif node.type == "type_declaration":
            grouped = any(child.type == "(" for child in node.children)
            for spec in node.named_children:
                if spec.type in ("type_spec", "type_alias"):
                    kind = "interface" if spec.child_by_field_name("type").type == "interface_type" else "type"
                    yield common._name(spec), kind, spec if grouped else node, _go_public(common._name(spec))


def _go_imports(root: Node) -> Iterator[Import]:
    for node in root.named_children:
        if node.type != "import_declaration":
            continue
        for child in node.named_children:
            for spec in [child] if child.type == "import_spec" else child.named_children:
                path = spec.child_by_field_name("path").text.decode().strip('"`')
                yield Import(path, 0, common._text(spec.child_by_field_name("name")) or path.rsplit("/", 1)[-1])


def _go_doc(node: Node, data: bytes) -> str | None:
    """The comments just above, without directives such as //go:build."""
    return "\n".join(common._uncomment(c.text.decode()) for c in common._comments_above(node, data)
                     if not c.text.startswith(b"//go:"))


def _go_file_doc(root: Node, data: bytes) -> str | None:
    package = next((c for c in root.named_children if c.type == "package_clause"), None)
    return _go_doc(package, data) if package else None


tables.register("go", (".go",), ("tree_sitter_go", "language"), _go,
                ({"call_expression": "function"}, "selector_expression", ("operand", "field")), _go_imports, _go_doc,
                file_doc=_go_file_doc)
