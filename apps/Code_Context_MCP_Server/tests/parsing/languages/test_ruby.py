"""Ruby's rules: definitions, docs, calls and imports, and private methods."""

from golestan_code_mcp.parsing import chunks as parsing_chunks
from golestan_code_mcp.parsing.common import Call, Import

from parsing.languages.helpers import calls, definitions, docs, parsed


def test_ruby_definitions_docs_calls_and_imports():
    assert definitions("ruby", "ruby/lib/parser.rb") == {
        "Acme": ("class", 4, 23, True),
        "Acme.Parser": ("class", 7, 22, True),
        "Acme.Parser.parse": ("method", 8, 11, True),
        "Acme.Parser.create": ("method", 13, 15, True),  # def self.create
        "Acme.Parser.lex": ("method", 19, 21, False),  # after a bare `private`
    }
    assert docs("ruby", "ruby/lib/parser.rb") == {"Acme.Parser": "Parses text into tokens. Second line of the comment."}
    assert calls("ruby", "ruby/lib/parser.rb") == {
        Call("Acme.Parser.parse", "lex", "bare", None, 9), Call("Acme.Parser.parse", "build", "attr", "self", 10),
        Call("Acme.Parser.parse", "finish", "attr", None, 10), Call("Acme.Parser.lex", "new", "attr", "Lexer", 20),
        Call("Acme.Parser.lex", "split", "attr", None, 20)}  # `new` with no arguments is not a call; nor requires
    assert parsed("ruby", "ruby/lib/parser.rb")[2] == [Import("lexer", 1, None), Import("json", 0, None)]
    assert parsed("ruby", "ruby/Rakefile") is not None


def test_ruby_private_by_name():
    source = "class A\n  def a\n  end\n\n  def b\n  end\n  private :b\nend\n"
    assert {c.name: c.exported for c in parsing_chunks.parse("ruby", source)[0]} == {"A": True, "A.a": True, "A.b": False}
