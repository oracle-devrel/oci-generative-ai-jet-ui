"""Ruby's rules: classes, modules, methods, calls, require and comments."""

from collections.abc import Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing import common, tables
from golestan_code_mcp.parsing.common import Found, Hit, Import

RUBY_REQUIRES = {"require": 0, "require_relative": 1}  # imports, not calls; require_relative is relative (level 1)


def _ruby_private_names(body: Node) -> set[str]:
    """Methods named by `private :a, :b` (or `private def ...`) in this body."""
    named = set()
    for node in body.named_children:
        method = node.child_by_field_name("method") if node.type == "call" else None
        if method is not None and method.text in (b"private", b"protected"):
            arguments = node.child_by_field_name("arguments")
            for argument in arguments.named_children if arguments is not None else ():
                if argument.type in ("simple_symbol", "symbol"):
                    named.add(argument.text.decode().lstrip(":"))
                elif argument.type == "method":
                    named.add(common._name(argument))
    return named


def _ruby(body: Node, prefix: str = "") -> Iterator[Found]:
    private, hidden = False, _ruby_private_names(body)
    for node in body.named_children:
        if node.type == "identifier" and node.text in (b"private", b"protected", b"public"):
            private = node.text != b"public"  # a bare `private` hides the methods after it
        elif node.type in ("module", "class") and node.child_by_field_name("name") is not None:
            name = prefix + node.child_by_field_name("name").text.decode().replace("::", ".")
            yield name, "class", node, True
            if (members := node.child_by_field_name("body")) is not None:
                yield from _ruby(members, name + ".")
        elif node.type == "singleton_class" and (members := node.child_by_field_name("body")) is not None:
            yield from _ruby(members, prefix)  # class << self: class methods
        elif node.type in ("method", "singleton_method"):
            short = common._name(node)
            exported = not (private and node.type == "method") and short not in hidden
            yield prefix + short, "method" if prefix else "function", node, exported
        elif node.type == "call" and (method := node.child_by_field_name("method")) is not None \
                and method.text in (b"private", b"protected"):
            for argument in (node.child_by_field_name("arguments") or node).named_children:
                if argument.type == "method":  # private def x ... end
                    yield prefix + common._name(argument), "method" if prefix else "function", argument, False


def _ruby_call(node: Node) -> Hit:
    if node.type != "call" or (method := node.child_by_field_name("method")) is None:
        return None
    receiver = node.child_by_field_name("receiver")
    if receiver is None:
        if method.text.decode() in RUBY_REQUIRES or method.text in (b"private", b"protected", b"public"):
            return None
        return method, "bare", None
    return (method, "attr",
            common._dotted(receiver).replace("::", ".") if common._dotted(receiver) else common._c_receiver(receiver))


def _ruby_imports(root: Node) -> Iterator[Import]:
    stack = [root]
    while stack:
        node = stack.pop()
        stack.extend(reversed(node.named_children))
        method = node.child_by_field_name("method") if node.type == "call" else None
        if method is not None and node.child_by_field_name("receiver") is None \
                and (level := RUBY_REQUIRES.get(method.text.decode())) is not None:
            arguments = node.child_by_field_name("arguments")
            first = arguments.named_children[0] if arguments is not None and arguments.named_child_count else None
            if first is not None and first.type == "string" and (content := common._child(first, "string_content")):
                yield Import(content.text.decode(), level, None)


def _ruby_doc(node: Node, data: bytes) -> str | None:
    """The `#` lines directly above, read from the source: the grammar may attach them to the enclosing body."""
    lines = data.decode("utf-8", "replace").splitlines()[:node.start_point.row]
    comments = []
    while lines and lines[-1].strip().startswith("#") and not lines[-1].strip().startswith("#!"):
        comments.append(lines.pop().strip()[1:])
    return "\n".join(reversed(comments)) or None


tables.register("ruby", (".rb", ".rake"), ("tree_sitter_ruby", "language"), _ruby, common._walk_calls(_ruby_call),
                _ruby_imports, _ruby_doc)
tables.NAMES.update({"Rakefile": "ruby", "Gemfile": "ruby"})
