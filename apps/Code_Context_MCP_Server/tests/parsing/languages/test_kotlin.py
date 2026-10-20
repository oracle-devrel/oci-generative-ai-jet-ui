"""Kotlin's rules: definitions, docs, calls and imports."""

from golestan_code_mcp.parsing.common import Call, Import

from parsing.languages.helpers import calls, definitions, docs, parsed


def test_kotlin_definitions_docs_calls_and_imports():
    assert definitions("kotlin", "kotlin/com/acme/Order.kt") == {
        "String.slug": ("method", 6, 8, True),  # an extension function is a method of its receiver type
        "top": ("function", 10, 12, True),
        "Order": ("class", 14, 28, True),
        "Order.total": ("method", 15, 17, True),
        "Order.sum": ("method", 19, 21, False),
        "Order.create": ("method", 24, 26, True),  # the companion object is transparent
        "Registry": ("class", 30, 34, True),
        "Registry.all": ("method", 31, 33, True),
        "Shape": ("interface", 36, 38, True),
        "Point": ("class", 40, 40, True),
        "Color": ("type", 42, 45, True),
    }
    assert docs("kotlin", "kotlin/com/acme/Order.kt") == {"String.slug": "A slug of the text."}
    assert calls("kotlin", "kotlin/com/acme/Order.kt") == {
        Call("String.slug", "lowercase", "bare", None, 7), Call("String.slug", "replace", "attr", None, 7),
        Call("Order.total", "sum", "bare", None, 16), Call("Order.total", "Money", "bare", None, 16),
        Call("Order.create", "Order", "bare", None, 25), Call("Registry.all", "listOf", "bare", None, 32),
        Call("Registry.all", "create", "attr", "Order", 32)}
    assert parsed("kotlin", "kotlin/com/acme/Order.kt")[2] == [Import("com.acme.Money", 0, None)]
