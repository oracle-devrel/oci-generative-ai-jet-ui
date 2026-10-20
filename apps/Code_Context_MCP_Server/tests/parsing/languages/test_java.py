"""Java's rules: definitions, docs, calls and imports."""

from golestan_code_mcp.parsing.common import Call, Import

from parsing.languages.helpers import calls, definitions, docs, parsed

# --- Java, Kotlin and Rust (US4) ---

ORDER_JAVA = "java/src/main/java/com/acme/Order.java"


def test_java_definitions_docs_calls_and_imports():
    assert definitions("java", ORDER_JAVA) == {
        "Order": ("class", 11, 38, True),
        "Order.Order": ("method", 14, 16, True),
        "Order.total": ("method", 18, 22, True),  # its @Override line is in the chunk
        "Order.sum": ("method", 24, 26, False),
        "Order.Line": ("interface", 28, 30, False),  # its bodiless member is not a definition
        "Order.Item": ("class", 32, 32, False),
        "Order.State": ("type", 34, 37, False),
    }
    assert docs("java", ORDER_JAVA) == {"Order": "An order of items."}  # stops at @author
    assert calls("java", ORDER_JAVA) == {
        Call("Order.total", "Money", "bare", None, 20), Call("Order.total", "add", "attr", "m", 21),
        Call("Order.total", "sum", "bare", None, 21), Call("Order.total", "max", "attr", "Math", 21),
        Call("Order.sum", "size", "attr", "this.items", 25)}
    assert parsed("java", ORDER_JAVA)[2] == [
        Import("com.acme.util.Money", 0, None), Import("com.acme.util.*", 0, None), Import("java.util.List", 0, None)]
