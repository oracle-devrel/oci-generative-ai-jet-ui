"""TypeScript's and TSX's rules: definitions, kinds and visibility, calls and imports, and components."""

from golestan_code_mcp.parsing import chunks as parsing_chunks
from golestan_code_mcp.parsing.common import Call, Import

from parsing.languages.helpers import calls, definitions, docs, parsed


def test_typescript_definitions_kinds_and_visibility():
    assert definitions("typescript", "typescript/src/cart.ts") == {
        "add": ("function", 9, 11, True),
        "helper": ("function", 13, 15, False),
        "twice": ("function", 17, 17, True),
        "Shape": ("interface", 19, 21, True),
        "Pair": ("type", 23, 23, True),
        "Color": ("type", 25, 28, True),
        "Cart": ("class", 30, 44, True),
        "Cart.constructor": ("method", 31, 31, True),
        "Cart.area": ("method", 33, 35, True),
        "Cart.total": ("method", 37, 39, False),
        "Cart.#secret": ("method", 41, 43, False),
    }
    assert docs("typescript", "typescript/src/cart.ts") == {"add": "Adds two numbers."}  # stops at @param


def test_typescript_calls_and_imports():
    assert calls("typescript", "typescript/src/cart.ts") == {
        Call("add", "helper", "bare", None, 10),
        Call("twice", "add", "bare", None, 17),
        Call("Cart.area", "total", "attr", "this", 34),
        Call("Cart.area", "count", "attr", "api", 34),
        Call("Cart.total", "get", "bare", None, 38),
        Call("Cart.total", "max", "attr", "Math", 38),
        Call("Cart.#secret", "Cart", "bare", None, 42),
        Call("Cart.#secret", "area", "attr", None, 42),
    }
    assert parsed("typescript", "typescript/src/cart.ts")[2] == [
        Import("./api/client", 0, "get"), Import("./api", 0, "api"), Import("./types", 0, "Id")]
    reexport = 'export { get } from "./api/client";\nexport * from "./types";\n'
    assert parsing_chunks.parse("typescript", reexport)[2] == [Import("./api/client", 0, None), Import("./types", 0, None)]


def test_tsx_components():
    assert definitions("tsx", "tsx/App.tsx") == {"App": ("function", 3, 5, True)}
    assert calls("tsx", "tsx/App.tsx") == {Call("App", "format", "bare", None, 4)}
    assert parsed("tsx", "tsx/App.tsx")[2] == [Import("./format", 0, "format")]
