"""The graph for the languages beyond Python, Go and JavaScript: definitions, callers and imports."""

import pytest

import uuid

from golestan_code_mcp import registry
from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.graph import queries

from graph.helpers import ENV, file_imports, make, outside

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


def test_csharp_ingests_as_definitions(csharp):
    _, summary = csharp
    assert (summary.no_grammar, summary.parse_errors) == (0, 1)  # only Broken.cs falls back


def test_csharp_callers_across_projects(conn, csharp):
    name, _ = csharp
    found = {(c.name, c.path, c.line, c.callee) for c in queries.callers(conn, "Start", [name])}
    assert found == {("ProductSteps.OpenProduct", "csharp/App/Steps/ProductSteps.cs", 17, "DriverFixture.Start"),
                     ("DriverFixture.Log", "csharp/App/Driver/DriverFixture.Logging.cs", 8, "DriverFixture.Start")}
    assert {(c.name, c.path) for c in queries.calls(conn, "DriverFixture.Start", [name])} >= {
        ("DriverFixture.GetWebDriver", "csharp/App/Driver/DriverFixture.cs"),
        ("BrowserDriver.Open", "csharp/App/Driver/BrowserDriver.cs")}


def test_csharp_usings_resolve_through_declared_namespaces(conn, csharp):
    name, _ = csharp
    driver = {f"csharp/App/Driver/{f}" for f in ("DriverFixture.cs", "DriverFixture.Logging.cs", "BrowserDriver.cs")}
    assert file_imports(conn, name) == {("csharp/App/Steps/ProductSteps.cs", f) for f in driver}
    assert outside(conn, name) == {"csharp/App/Driver/DriverFixture.cs": {"System"},
                                   "csharp/App/Steps/ProductSteps.cs": {"System.Linq"}}


def test_us2_ingests_as_definitions(us2):
    _, summary = us2
    assert (summary.no_grammar, summary.parse_errors) == (0, 4)  # only the four broken files fall back


def test_us2_callers(conn, us2):
    name, _ = us2
    assert {(c.name, c.path, c.line) for c in queries.callers(conn, "parse_config", [name])} == {
        ("load", "c/parse.c", 14), ("reload", "c/parse.c", 19)}  # not from the comment
    assert {(c.name, c.path, c.line) for c in queries.callers(conn, "Engine.start", [name])} == {
        ("main", "cpp/engine.cpp", 19)}
    assert {c.name for c in queries.calls(conn, "Engine.start", [name])} == {"Engine.warm", "Engine.speed"}
    assert {(c.name, c.path) for c in queries.callers(conn, "count", [name])} == {
        ("Cart.area", "typescript/src/cart.ts")}  # api.count() through `import * as api from "./api"`


def test_us2_imports_resolve(conn, us2):
    name, _ = us2
    assert file_imports(conn, name) == {
        ("typescript/src/cart.ts", "typescript/src/api/client.ts"),
        ("typescript/src/cart.ts", "typescript/src/api/index.ts"),
        ("typescript/src/cart.ts", "typescript/src/types.ts"),
        ("tsx/App.tsx", "tsx/format.ts"),
        ("c/parse.c", "c/config.h"),
        ("cpp/engine.cpp", "cpp/engine.h"),
    }
    assert outside(conn, name) == {"c/parse.c": {"stdio.h"}, "cpp/engine.h": {"vector"}}


def test_an_include_found_by_path_anywhere_in_the_repository(conn, tmp_path):
    root = tmp_path / "repo"
    make(root, {"include/util/str.h": "int len(const char *s);\n",
                "src/main.c": '#include "util/str.h"\n\nint main(void) {\n    return len("x");\n}\n'})
    name = f"t-{uuid.uuid4().hex[:8]}"
    registry.add_repo(conn, root, name)
    indexing_ingest.ingest(conn, name, ENV)
    assert file_imports(conn, name) == {("src/main.c", "include/util/str.h")}


def test_us4_ingests_as_definitions(us4):
    _, summary = us4
    assert (summary.no_grammar, summary.parse_errors) == (0, 3)  # Broken.java, OneLine.kt, broken.rs


def test_us4_callers(conn, us4):
    name, _ = us4
    java = "java/src/main/java/com/acme/"
    assert {(c.name, c.path, c.line) for c in queries.callers(conn, "add", [name])} == {
        ("Order.total", java + "Order.java", 21)}
    assert {c.name for c in queries.calls(conn, "Order.total", [name]) if c.path.endswith(".java")} == {
        "Money", "Money.add", "Order.sum"}  # sum() is this.sum()
    assert {(c.name, c.line) for c in queries.callers(conn, "Order.create", [name])} == {("Registry.all", 32)}
    assert {(c.name, c.path) for c in queries.callers(conn, "Circle.new", [name])} == {("make", "rust/src/lib.rs")}
    assert {c.name for c in queries.callers(conn, "square", [name])} == {"Circle.area"}


def test_us4_imports_resolve(conn, us4):
    name, _ = us4
    java = "java/src/main/java/com/acme/"
    assert file_imports(conn, name) == {
        (java + "Order.java", java + "util/Money.java"),  # the class import and the wildcard
        ("kotlin/com/acme/Order.kt", "kotlin/com/acme/Money.kt"),
        ("rust/src/lib.rs", "rust/src/geometry.rs"),  # mod geometry; and use crate::geometry::Circle
    }
    assert outside(conn, name) == {java + "Order.java": {"java.util"}, "rust/src/lib.rs": {"std"}}


def test_us5_ingests_as_definitions(us5):
    _, summary = us5
    assert (summary.no_grammar, summary.parse_errors) == (0, 3)  # broken.php, broken.rb, Broken.swift


def test_us5_callers(conn, us5):
    name, _ = us5
    assert {(c.name, c.path) for c in queries.callers(conn, "Logger.write", [name])} == {("Repo.log", "php/Repo.php")}
    assert {(c.name, c.path) for c in queries.callers(conn, "query", [name])} == {("Repo.find", "php/Repo.php")}
    assert {c.name for c in queries.callers(conn, "Acme.Parser.lex", [name])} == {"Acme.Parser.parse"}  # implicit self
    assert {c.name for c in queries.callers(conn, "Circle.area", [name])} == {"Engine.start"}
    assert {c.name for c in queries.callers(conn, "square", [name])} == {"Circle.area"}


def test_us5_imports_resolve(conn, us5):
    name, _ = us5
    assert file_imports(conn, name) == {
        ("php/Repo.php", "php/lib/db.php"),  # require_once __DIR__ . '/lib/db.php'
        ("php/Repo.php", "php/App/Util/Logger.php"),  # use App\Util\Logger; by PSR-4
        ("ruby/lib/parser.rb", "ruby/lib/lexer.rb"),  # require_relative "lexer"
    }  # Swift files import no files
    assert outside(conn, name) == {"ruby/lib/parser.rb": {"json"}, "swift/Shapes.swift": {"Foundation"}}
