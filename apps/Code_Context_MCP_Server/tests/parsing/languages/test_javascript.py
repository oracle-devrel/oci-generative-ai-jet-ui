"""JavaScript's rules: definitions, calls, imports and JSDoc comments."""

from parsing.helpers import docs, outline, refs


def test_javascript_outline():
    assert outline("javascript", "sample.js") == {
        ("add", "function", 3, 5),
        ("count", "function", 7, 9),
        ("Counter", "class", 11, 20),
        ("Counter.constructor", "method", 12, 14),
        ("Counter.bump", "method", 16, 19),
        ("square", "function", 22, 24),
        ("main", "function", 26, 28),
    }


JS_SOURCE = """\
import { join } from "./paths";
import React from "react";
const util = require("./util");

function main() {
  helper();
  util.format("a");
  return new Widget();
}
"""


def test_javascript_calls_and_imports():
    calls, imports = refs("javascript", JS_SOURCE)
    assert {c for c in calls if c[0] == "main"} == {
        ("main", "helper", "bare", None, 6),
        ("main", "format", "attr", "util", 7),
        ("main", "Widget", "bare", None, 8),
    }
    assert imports == {("./paths", 0, "join"), ("./util", 0, "util")}


JS_DOCS = """\
/** File comment, never stored. */

/**
 * Add two numbers.
 *
 * @param a first
 */
function add(a, b) {
  return a + b;
}

// a line comment is not a doc
function plain() {}

export class Counter {
  /** Bump it. */
  bump() {}
}
"""


def test_javascript_docs():
    symbols, file_doc = docs("javascript", JS_DOCS)
    assert file_doc is None  # simplified: no JS file docs
    assert symbols == {"add": "Add two numbers.", "plain": None, "Counter": None, "Counter.bump": "Bump it."}
