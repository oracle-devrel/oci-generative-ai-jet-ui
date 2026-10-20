"""Call resolution: which definition each stored call reaches, by form, receiver and imports."""

import pytest

from golestan_code_mcp.graph import build
from golestan_code_mcp.graph import imports as graph_imports

from graph.helpers import APP, CHAIN, H, OTHER, TEST, edges

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


# --- resolution (T007) --------------------------------------------------------------------------------------


def test_python_call_resolution(conn, repos):
    assert edges(conn, repos[0]) == sorted([
        ("url_for", H, "encode", H),  # print() and the stdlib json.dumps() resolve to nothing, not to dumps
        ("Flask.url_for", APP, "url_for", H),  # rule 2: helpers is an imported module, so a bare call
        ("Flask.open", APP, "Flask.url_for", APP),  # rule 3: self prefers the enclosing class
        ("Other.run", OTHER, "Other.url_for", OTHER),
        ("b", CHAIN, "a", CHAIN),  # the same file wins over other.a
        ("c", CHAIN, "b", CHAIN), ("c", CHAIN, "a", CHAIN),
        ("d", CHAIN, "c", CHAIN), ("e", CHAIN, "d", CHAIN),  # Helper lives in another repository: no edge
        ("ping", CHAIN, "pong", CHAIN), ("pong", CHAIN, "ping", CHAIN), ("fact", CHAIN, "fact", CHAIN),
        ("(module)", TEST, "url_for", H),  # lib.url_for: rule 2, then the whole repository
        ("test_open", TEST, "Flask", APP),  # bare call to a class
        ("test_open", TEST, "Flask.open", APP),  # rule 4
        ("obj_call", TEST, "Flask.url_for", APP),  # rule 4: the imported file wins over Other.url_for
        ("class_call", TEST, "Flask.url_for", APP),  # Flask is an imported class, not a module: rule 4
    ])


def test_go_and_javascript_call_resolution(conn, repos):
    assert edges(conn, repos[1]) == sorted([
        ("main", "main.go", "Helper", "util/a.go"),  # u.Helper: the aliased package import is bare
        ("Other", "util/b.go", "Helper", "util/a.go"),
        ("start", "web/app.js", "helper", "web/lib.js"),
        ("a", "web/lib.js", "helper", "web/lib.js"),
    ])


@pytest.mark.parametrize(("receiver", "normalized"), [
    ("$this", "this"), ("Foo::bar", "Foo.bar"), ("self->engine", "self.engine"), ("a.b", "a.b"), (None, None),
    ("$repo->db", "repo.db"),
])
def test_receivers_are_normalized_to_dotted_names(receiver, normalized):
    assert graph_imports._normalize(receiver) == normalized


def test_self_receivers_include_the_new_languages():
    assert {"self", "cls", "this", "Self", "base"} <= build.SELF
