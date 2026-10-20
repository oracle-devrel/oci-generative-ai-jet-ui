"""Swift's rules: definitions, docs, calls and imports."""

from golestan_code_mcp.parsing.common import Call, Import

from parsing.languages.helpers import calls, definitions, docs, parsed


def test_swift_definitions_docs_calls_and_imports():
    assert definitions("swift", "swift/Shapes.swift") == {
        "Circle": ("type", 4, 6, True),
        "Shape": ("interface", 8, 10, True),
        "Circle.area": ("method", 13, 16, True),  # in an extension of Circle
        "Circle.scale": ("method", 18, 20, False),
        "Engine": ("class", 23, 31, True),
        "Engine.init": ("method", 24, 26, True),
        "Engine.start": ("method", 28, 30, True),
        "Kind": ("type", 33, 35, True),
        "square": ("function", 37, 39, True),
    }
    assert docs("swift", "swift/Shapes.swift") == {"Circle": "A circle."}
    assert calls("swift", "swift/Shapes.swift") == {
        Call("Circle.area", "scale", "attr", "self", 14), Call("Circle.area", "square", "bare", None, 15),
        Call("Engine.init", "start", "bare", None, 25), Call("Engine.start", "Circle", "bare", None, 29),
        Call("Engine.start", "area", "attr", None, 29)}
    assert parsed("swift", "swift/Shapes.swift")[2] == [Import("Foundation", 0, None)]
