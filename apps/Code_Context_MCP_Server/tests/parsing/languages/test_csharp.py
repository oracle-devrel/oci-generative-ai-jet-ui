"""C#'s rules: definitions, kinds and visibility, XML docs, calls, usings and namespaces."""

import pytest

from golestan_code_mcp.parsing import chunks as parsing_chunks
from golestan_code_mcp.parsing.common import Call, Import

from parsing.languages.helpers import calls, definitions, docs, parsed


# --- C# (US1) ---


@pytest.mark.parametrize("path", ["a.cs", "A/B/Thing.CS"])
def test_csharp_files(path):
    assert parsing_chunks.detect_language(path) == "csharp"


def test_csharp_definitions_kinds_and_visibility():
    assert definitions("csharp", "csharp/App/Driver/DriverFixture.cs") == {
        "DriverFixture": ("class", 7, 44, True),
        "DriverFixture.DriverFixture": ("method", 11, 14, True),
        "DriverFixture.Start": ("method", 19, 24, True),  # its [Obsolete] line is in the chunk
        "DriverFixture.GetWebDriver": ("method", 26, 31, False),
        "DriverFixture.Dispose": ("method", 33, 35, True),
        "DriverFixture.Options": ("class", 37, 43, True),
        "DriverFixture.Options.Timeout": ("method", 39, 42, True),
    }  # no namespace in names; the property and the field are not definitions
    assert definitions("csharp", "csharp/App/Driver/DriverFixture.Logging.cs") == {
        "DriverFixture": ("class", 3, 10, True), "DriverFixture.Log": ("method", 5, 9, False)}  # a partial part
    assert definitions("csharp", "csharp/App/Driver/BrowserDriver.cs") == {
        "BrowserDriver": ("class", 3, 15, True),
        "BrowserDriver.Configure": ("method", 7, 10, True),
        "BrowserDriver.Open": ("method", 12, 14, True),
        "IDriverFixture": ("interface", 17, 20, True),  # its bodiless member is not a definition
        "Point": ("class", 22, 22, True),
        "Size": ("type", 24, 27, True),
        "Browser": ("type", 29, 33, True),
    }
    assert definitions("csharp", "csharp/App/Steps/ProductSteps.cs") == {
        "ProductSteps": ("class", 6, 24, True),
        "ProductSteps.ProductSteps": ("method", 10, 13, True),
        "ProductSteps.OpenProduct": ("method", 15, 19, True),
        "ProductSteps.Helper": ("method", 21, 23, False),
    }


def test_csharp_xml_docs():
    assert docs("csharp", "csharp/App/Driver/DriverFixture.cs") == {
        "DriverFixture": "Holds the browser for a test run. Uses BrowserDriver.",
        "DriverFixture.Start": "Starts the browser.",
    }


def test_csharp_calls():
    assert calls("csharp", "csharp/App/Driver/DriverFixture.cs") == {
        Call("DriverFixture.Start", "GetWebDriver", "bare", None, 22),
        Call("DriverFixture.Start", "Open", "attr", "driver", 23),
        Call("DriverFixture.GetWebDriver", "BrowserDriver", "bare", None, 30),  # new BrowserDriver()
        Call("DriverFixture.GetWebDriver", "Configure", "attr", None, 30),
    }  # nothing from the comment or the string
    assert calls("csharp", "csharp/App/Driver/DriverFixture.Logging.cs") == {
        Call("DriverFixture.Log", "WriteLine", "attr", "Console", 7),
        Call("DriverFixture.Log", "Start", "attr", "this", 8),
    }
    assert calls("csharp", "csharp/App/Steps/ProductSteps.cs") == {
        Call("ProductSteps.OpenProduct", "Start", "attr", "fixture", 17),
        Call("ProductSteps.OpenProduct", "Helper", "bare", None, 18),
    }


def test_csharp_call_forms():
    source = ("class C\n{\n    void M()\n    {\n        d?.Open();\n        Get<int>();\n        a.b.Run();\n"
              "        base.M();\n        new List<int>();\n    }\n}\n")
    assert set(parsing_chunks.parse("csharp", source)[1]) == {
        Call("C.M", "Open", "attr", "d", 5), Call("C.M", "Get", "bare", None, 6), Call("C.M", "Run", "attr", "a.b", 7),
        Call("C.M", "M", "attr", "base", 8), Call("C.M", "List", "bare", None, 9)}


def test_csharp_usings_and_namespaces():
    _, _, imports, _, namespaces = parsed("csharp", "csharp/App/Steps/ProductSteps.cs")
    assert imports == [Import("App.Driver", 0, None), Import("System.Linq", 0, None)] and namespaces == ["App.Steps"]
    _, _, imports, _, namespaces = parsed("csharp", "csharp/App/Driver/DriverFixture.cs")
    assert imports == [Import("System", 0, None)] and namespaces == ["App.Driver"]
    source = ("global using static System.Math;\nusing Alias = A.B;\nnamespace Outer\n{\n    namespace Inner\n    {\n"
              "        class C\n        {\n        }\n    }\n}\n")
    _, _, imports, _, namespaces = parsing_chunks.parse("csharp", source)
    assert imports == [Import("System.Math", 0, None), Import("A.B", 0, None)]
    assert namespaces == ["Outer", "Outer.Inner"]


def test_csharp_file_that_does_not_parse():
    assert parsed("csharp", "csharp/Broken.cs") is None
