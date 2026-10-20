"""Rust's rules: definitions, docs, calls and imports, and impl names."""

from golestan_code_mcp.parsing import chunks as parsing_chunks
from golestan_code_mcp.parsing.common import Call, Import

from parsing.languages.helpers import calls, definitions, docs, parsed


def test_rust_definitions_docs_calls_and_imports():
    chunks, file_calls, imports, file_doc, _ = parsed("rust", "rust/src/lib.rs")
    assert {c.name: (c.kind, c.start_line, c.end_line, c.exported) for c in chunks} == {
        "make": ("function", 9, 11, True), "helper": ("function", 13, 15, False)}
    assert file_doc == "Geometry for the demo." and docs("rust", "rust/src/lib.rs") == {"make": "Makes a circle."}
    assert set(file_calls) == {Call("make", "new", "attr", "Circle", 10), Call("make", "scale", "attr", None, 10),
                               Call("helper", "Ok", "bare", None, 14)}
    assert imports == [Import("geometry", 1, None), Import("crate::geometry::Circle", 0, None),
                       Import("std::fmt", 0, "fmt")]  # mod is relative; a module, not a type, is bound
    assert definitions("rust", "rust/src/geometry.rs") == {
        "Circle": ("type", 2, 5, True),  # the #[derive] line is in the chunk, the doc above it is not
        "Shape": ("interface", 7, 9, True),
        "Circle.area": ("method", 12, 14, True),  # impl Shape for Circle
        "Circle.new": ("method", 18, 20, True),
        "Circle.scale": ("method", 22, 25, True),
        "Kind": ("type", 28, 30, True),
        "square": ("function", 32, 34, False),
    }
    assert docs("rust", "rust/src/geometry.rs") == {"Circle": "A circle."}
    assert calls("rust", "rust/src/geometry.rs") == {Call("Circle.area", "square", "bare", None, 13)}  # no macros


def test_rust_impl_names_drop_generics():
    source = "struct Stack<T> {\n    items: Vec<T>,\n}\n\nimpl<T> Stack<T> {\n    fn push(&mut self, x: T) {\n    }\n}\n"
    assert {c.name for c in parsing_chunks.parse("rust", source)[0]} == {"Stack", "Stack.push"}
