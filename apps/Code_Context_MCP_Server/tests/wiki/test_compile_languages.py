"""The wiki compiler for the languages beyond Python, Go and JavaScript: their pages, and their test files last."""

import re

import pytest

from golestan_code_mcp.wiki import compile

from wiki.helpers import language_wiki, page_of, page_rows

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


def test_a_csharp_directory_page(conn, tmp_path):
    name = language_wiki(conn, tmp_path / "repo", "csharp")
    _, page, language, symbols, body, *_ = page_of(conn, name, "csharp/App/Driver")
    assert language == "csharp" and symbols == 16
    assert f"`{page}` is a C# directory of 3 files and 16 definitions" in body
    keys = re.findall(r"^- `([^`]+)` \(", body, re.M)
    assert {"DriverFixture", "BrowserDriver"} <= set(keys[:4])
    assert "## Used by\n- `csharp/App/Steps`\n" in body  # its `using App.Driver;`, through declared namespaces
    assert "DriverFixture.Start" in keys and "DriverFixture.GetWebDriver" not in keys  # called from outside; private
    assert "csharp/App/Steps" not in {row[0] for row in page_rows(conn, name).values()}  # 4 definitions, no page


def test_a_typescript_directory_page(conn, tmp_path):
    name = language_wiki(conn, tmp_path / "repo", "typescript", "cpp")
    _, page, language, _, body, *_ = page_of(conn, name, "typescript/src")
    assert language == "typescript" and f"`{page}` is a TypeScript directory" in body
    assert "Cart.#secret" not in re.findall(r"^- `([^`]+)` \(", body, re.M)[:5]


@pytest.mark.parametrize(("path", "test"), [
    ("src/cart.test.ts", True), ("src/cart.spec.tsx", True), ("src/cart.ts", False), ("test/test_parse.c", True),
    ("src/parse_test.cpp", True), ("src/parse.cpp", False),
])
def test_us2_test_files_rank_last(path, test):
    assert compile._is_test(path) is test


def test_a_kotlin_directory_page(conn, tmp_path):
    name = language_wiki(conn, tmp_path / "repo", "kotlin")
    _, page, language, _, body, *_ = page_of(conn, name, "kotlin/com/acme")
    assert language == "kotlin" and f"`{page}` is a Kotlin directory" in body


@pytest.mark.parametrize(("path", "test"), [
    ("src/OrderTest.java", True), ("src/OrderTests.kt", True), ("src/Order.java", False), ("tests/geometry.rs", True),
    ("src/geometry.rs", False),
])
def test_us4_test_files_rank_last(path, test):
    assert compile._is_test(path) is test


def test_every_language_with_rules_has_a_plain_name():
    from golestan_code_mcp.parsing import tables

    assert set(compile.LANGUAGE_NAMES) == set(tables.GRAMMARS)
    assert {compile.LANGUAGE_NAMES[k] for k in ("php", "ruby", "swift")} == {"PHP", "Ruby", "Swift"}


@pytest.mark.parametrize(("path", "test"), [
    ("tests/RepoTest.php", True), ("lib/parser_test.rb", True), ("spec/parser_spec.rb", True),
    ("ShapesTests.swift", True), ("lib/parser.rb", False), ("Repo.php", False),
])
def test_us5_test_files_rank_last(path, test):
    assert compile._is_test(path) is test
