"""Go's rules: definitions, calls, imports and doc comments."""

from parsing.helpers import GO_DOCS, docs, outline, refs


def test_go_outline():
    assert outline("go", "sample.go") == {
        ("Greet", "function", 6, 8),
        ("Counter", "type", 10, 12),
        ("Counter.Bump", "method", 14, 17),
        ("Greeter", "interface", 19, 21),
        ("Point", "type", 24, 26),
        ("Shape", "interface", 27, 29),
        ("Engine", "type", 32, 34),
        ("Engine.Use", "method", 36, 38),
    }


GO_SOURCE = """\
package main

import (
	"fmt"
	"net/http"
	str "strings"
)

func Run() {
	Greet()
	fmt.Println(str.ToUpper("a"), http.StatusOK)
}
"""


def test_go_calls_and_imports():
    calls, imports = refs("go", GO_SOURCE)
    assert calls == {
        ("Run", "Greet", "bare", None, 10),
        ("Run", "Println", "attr", "fmt", 11),
        ("Run", "ToUpper", "attr", "str", 11),
    }
    assert imports == {("fmt", 0, "fmt"), ("net/http", 0, "http"), ("strings", 0, "str")}


def test_go_symbol_and_package_docs():
    symbols, file_doc = docs("go", GO_DOCS)
    assert file_doc == "Package server serves widgets."
    assert symbols == {"Server": "Server holds the state. It is shared.", "Bare": None,
                       "Server.Start": "Block doc for Start.", "Point": "Point is a point.", "Shape": None,
                       "After": None}


def test_go_header_separated_by_a_blank_line_is_not_attached():
    assert docs("go", "// Copyright header.\n\npackage main\n\nfunc main() {}\n") == ({"main": None}, None)
