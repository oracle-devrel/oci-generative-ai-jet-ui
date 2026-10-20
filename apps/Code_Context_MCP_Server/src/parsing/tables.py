"""The language tables: each language's grammar, extensions, definition walker, call and import readers, and doc
readers.

Each language file under parsing/languages/ registers itself with register(). The tables are complete as soon
as this module is imported: its last line imports every language file. A language's extensions are added together
with its rules, never before: a file stored under a language without rules would never be re-read once the rules
arrive.
"""

from collections.abc import Callable, Iterator

from tree_sitter import Node

from golestan_code_mcp.parsing.common import Found

# language -> (grammar module, function returning its language), imported on the first file of that language
GRAMMARS: dict[str, tuple[str, str]] = {}

# The languages without rules are here; register() adds each language with rules.
EXTENSIONS = {
    ".py": "python",
    ".go": "go",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".html": "html",
    ".htm": "html",
    ".json": "json",
    ".sh": "shell",
    ".bash": "shell",
    ".txt": "text",
    ".css": "css",
    ".sql": "sql",
    ".tmpl": "text",
    ".proto": "proto",
    ".cfg": "ini",
    ".ini": "ini",
    ".bat": "batch",
}

NAMES: dict[str, str] = {}  # file names with a language but no telling extension (Rakefile)

WALKERS: dict[str, Callable[[Node], Iterator[Found]]] = {}

# The call node types with their callee field, and the attribute node type with its (receiver, name) fields.
# A language may give a function (root, scopes) -> list[Call] instead.
CALLS: dict = {}

IMPORTS: dict = {}
SYMBOL_DOCS: dict = {}
FILE_DOCS: dict = {}
NAMESPACES: dict = {}  # language -> root -> the namespaces the file declares (C#)
LEADING: dict[str, set[str]] = {}  # language -> sibling node types above a definition that belong to its chunk


def register(language: str, extensions: tuple[str, ...], grammar: tuple[str, str], walker, calls, imports, doc,
             file_doc=None, namespaces=None, leading=None) -> None:
    EXTENSIONS.update(dict.fromkeys(extensions, language))
    GRAMMARS[language], WALKERS[language], CALLS[language] = grammar, walker, calls
    IMPORTS[language], SYMBOL_DOCS[language] = imports, doc
    for table, value in ((FILE_DOCS, file_doc), (NAMESPACES, namespaces), (LEADING, leading)):
        if value is not None:
            table[language] = value


# Imported last: the language files call register() above as they load.
from golestan_code_mcp.parsing import languages  # noqa: E402, F401
