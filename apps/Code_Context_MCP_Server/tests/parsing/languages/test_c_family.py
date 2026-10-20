"""C's and C++'s rules: definitions, calls and includes, headers, classes, out-of-class definitions and
templates.
"""

from golestan_code_mcp.parsing.common import Call, Import

from parsing.languages.helpers import calls, definitions, docs, parsed


def test_c_definitions_calls_and_includes():
    assert definitions("c", "c/parse.c") == {
        "read_line": ("function", 4, 6, False),  # static
        "parse_config": ("function", 9, 11, True),
        "load": ("function", 13, 15, True),
        "reload": ("function", 17, 20, True),
    }
    assert docs("c", "c/parse.c") == {"parse_config": "Parses the file at path."}
    assert calls("c", "c/parse.c") == {
        Call("read_line", "printf", "bare", None, 5), Call("parse_config", "read_line", "bare", None, 10),
        Call("load", "parse_config", "bare", None, 14), Call("reload", "parse_config", "bare", None, 19)}
    assert parsed("c", "c/parse.c")[2] == [Import("config.h", 0, None), Import("<stdio.h>", 0, None)]


def test_a_header_is_read_as_cpp():
    chunks, _, _, file_doc, _ = parsed("cpp", "c/config.h")
    assert {c.name: (c.kind, c.start_line, c.end_line) for c in chunks} == {
        "config": ("type", 5, 7), "config_t": ("type", 9, 9)}  # inside the include guard; the prototype is not
    assert file_doc == "Configuration loading."


def test_cpp_classes_out_of_class_definitions_and_templates():
    assert definitions("cpp", "cpp/engine.h") == {
        "Engine": ("class", 6, 13, True),
        "Engine.speed": ("method", 9, 9, True),
        "Engine.warm": ("method", 12, 12, False),  # under private:
        "Point": ("type", 15, 17, True),
        "Mode": ("type", 19, 19, True),
    }  # the namespace is left out, and the bodiless `start` is not a definition here
    assert docs("cpp", "cpp/engine.h") == {"Engine": "An engine."}
    assert definitions("cpp", "cpp/engine.cpp") == {
        "Engine.start": ("method", 6, 10, True),  # app::Engine::start, after its last qualifier
        "maxof": ("function", 12, 15, True),  # the template line is in the chunk
        "main": ("function", 17, 21, True),
    }
    assert docs("cpp", "cpp/engine.cpp") == {"Engine.start": "Starts the engine."}


def test_cpp_calls_and_includes():
    assert calls("cpp", "cpp/engine.cpp") == {
        Call("Engine.start", "warm", "bare", None, 7), Call("Engine.start", "speed", "attr", "this", 8),
        Call("Engine.start", "run", "attr", "Helper", 9), Call("main", "start", "attr", "e", 19),
        Call("main", "maxof", "bare", None, 20)}
    assert parsed("cpp", "cpp/engine.h")[2] == [Import("<vector>", 0, None)]
    assert parsed("cpp", "cpp/engine.cpp")[2] == [Import("engine.h", 0, None)]
