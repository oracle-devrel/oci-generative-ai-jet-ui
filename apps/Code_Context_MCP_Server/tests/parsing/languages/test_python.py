"""Python's rules: definitions, calls, imports and docstrings."""

from parsing.helpers import PY_DOCS, PY_SOURCE, docs, outline, refs


def test_python_outline():
    assert outline("python", "sample.py") == {
        ("add", "function", 6, 7),
        ("greet", "function", 10, 14),
        ("Counter", "class", 17, 31),
        ("Counter.__init__", "method", 18, 19),
        ("Counter.value", "method", 21, 23),
        ("Counter.bump", "method", 25, 27),
        ("Counter.Step", "class", 29, 31),
        ("Counter.Step.size", "method", 30, 31),
        ("square", "function", 34, 36),
    }


def test_python_calls():
    calls, _ = refs("python", PY_SOURCE)
    assert calls == {
        (None, "register", "bare", None, 11),
        ("handler", "join", "attr", "a.b", 17),
        ("handler", "helper", "bare", None, 18),
        ("Box", "compute", "bare", None, 22),
        ("Box.grow", "shrink", "attr", "self", 25),
        ("Box.grow", "tally", "bare", None, 26),
    }


def test_python_imports():
    _, imports = refs("python", PY_SOURCE)
    assert imports == {("a.b", 0, "a"), ("a.b.c", 0, "c"), ("x", 1, "x"), ("m.y", 2, "z"), ("q", 0, None)}


def test_python_symbol_and_module_docs():
    symbols, file_doc = docs("python", PY_DOCS)
    assert file_doc == "Tools for widgets."
    assert symbols == {"documented": "Make a widget from parts.", "bare": None, "Box": "A box.",
                       "Box.open": "Open it."}


def test_python_file_without_docstring():
    assert docs("python", "import os\n\n\ndef f():\n    pass\n") == ({"f": None}, None)
