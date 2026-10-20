"""PHP's rules: definitions, docs, calls and imports."""

from golestan_code_mcp.parsing.common import Call, Import

from parsing.languages.helpers import docs, parsed


def test_php_definitions_docs_calls_and_imports():
    chunks, file_calls, imports, file_doc, _ = parsed("php", "php/Repo.php")
    assert {c.name: (c.kind, c.start_line, c.end_line, c.exported) for c in chunks} == {
        "Repo": ("class", 16, 39, True),
        "Repo.find": ("method", 18, 22, True),
        "Repo.count": ("method", 24, 27, True),  # no modifier: public
        "Repo.log": ("method", 29, 33, False),
        "Repo.make": ("method", 35, 38, True),
        "IRepo": ("interface", 41, 44, True),  # its bodiless member is not a definition
        "Logs": ("interface", 46, 51, True),
        "Logs.trace": ("method", 48, 50, True),
        "top": ("function", 53, 56, True),
    }  # no namespace in names
    assert file_doc == "Data access for the demo." and docs("php", "php/Repo.php") == {"Repo": "A repository of rows."}
    assert set(file_calls) == {
        Call("Repo.find", "log", "attr", "this", 20), Call("Repo.find", "get", "attr", "Helper", 21),
        Call("Repo.find", "query", "bare", None, 21), Call("Repo.log", "write", "attr", "Logger", 32),
        Call("Repo.make", "Repo", "bare", None, 37)}  # nothing from the comment
    assert imports == [Import("App\\Util\\Logger", 0, None), Import("lib/db.php", 1, None)]
