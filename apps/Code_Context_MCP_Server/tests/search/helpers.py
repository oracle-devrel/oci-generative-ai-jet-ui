"""Helpers for the search tests: throwaway symbols and repositories, a ledger of pages, and readers of hits."""

import re
from pathlib import Path
import uuid

import oracledb

from golestan_code_mcp.parsing import chunks

RUN = uuid.uuid4().hex[:6]

A, B, C = f"t-{RUN}a", f"t-{RUN}b", f"t-{RUN}c"

TOKEN = f"quokka_{RUN}"  # appears in every symbol of C and nowhere else

# the list in specs/012-language-coverage/contracts/tools.md, which extends 008's with the new languages
LANGUAGE_LIST = re.search(r"Search only files of this language: one of (.+?)\. Default",
                          (Path(__file__).resolve().parents[2] / "specs" / "012-language-coverage" / "contracts"
                           / "tools.md").read_text(encoding="utf-8")).group(1)

SYMBOLS = {
    A: [
        ("url_for", "function", "pkg/helpers.py",
         "def url_for(endpoint, **values):\n    # build a URL for the given endpoint\n    return current_app.url_for(endpoint, **values)\n"),
        ("App.url_for", "method", "pkg/app.py",
         "def url_for(self, endpoint, **values):\n    # generate a URL to the endpoint with the given values\n    return self.url_map.build(endpoint, values)\n"),
        ("redirect_home", "function", "pkg/views.py",
         "def redirect_home():\n    # send the user back to the start page\n    return redirect(url_for('index'))\n"),
        ("route_request", "function", "pkg/routing.py",
         "def route_request(path):\n    # match the incoming URL path against registered routes and dispatch to its handler\n"
         "    return ROUTES[path]()\n"),
        ("bake_bread", "function", "pkg/kitchen.py",
         "def bake_bread():\n    # mix flour, water, yeast and salt, knead the dough and bake the loaf\n    return oven.bake(dough)\n"),
    ],
    B: [
        ("Engine.Use", "method", "gin.go",
         "func (engine *Engine) Use(middleware ...HandlerFunc) IRoutes {\n\t// attach global middleware\n"
         "\tengine.RouterGroup.Use(middleware...)\n\treturn engine\n}\n"),
        ("handleChain", "function", "context.go",
         "func handleChain(c *Context) {\n\t// run each middleware in the chain for the request, then the handler\n"
         "\tfor c.index < len(c.handlers) { c.handlers[c.index](c); c.index++ }\n}\n"),
    ],
    C: [  # 4 Go and 6 Python symbols sharing TOKEN; the language comes from the path, as the chunker assigns it
        *[(f"Quokka{i}", "function", f"q{i}.go", f"func Quokka{i}() {{\n\t// {TOKEN}\n}}\n") for i in range(4)],
        *[(f"quokka_py{i}", "function", f"q{i}.py", f"def quokka_py{i}():\n    # {TOKEN}\n    pass\n")
          for i in range(4)],
        ("tall", "function", "tall.py", "def tall():\n" + "".join(f"    x{n} = '{TOKEN}'\n" for n in range(30))),
        ("wide", "function", "wide.py", f"def wide():\n    return '{TOKEN}' + '" + "w" * 1000 + "'\n"),
    ],
}

LITERALS = ["a_b", "x-y", "(foo)", "c&d", "50%", '"quoted"', "{brace}", "back\\slash", "a | b", "NOT near"]


def add_symbol(cur, file_id, name, kind, path, source):
    cur.setinputsizes(t=oracledb.DB_TYPE_CLOB, s=oracledb.DB_TYPE_CLOB)
    cur.execute(
        """insert into ccctx_symbols (file_id, name, kind, start_line, end_line, content_hash, commit_sha,
                                      search_text, source)
           values (:f, :n, :k, 1, :e, :h, :c, :t, :s)""",
        f=file_id, n=name, k=kind, e=source.count("\n"), h="0" * 64, c="a" * 40,
        t=f"{kind} {name} in {path}\n{source}", s=source,
    )


def names(results):
    return [r.name for r in results]


# --- language, limit and snippets (008 contracts/tools.md `search_code`) ----------------------------------


def opening(source: str) -> str:
    """The contract's snippet: the source's first 10 lines, cut to 800 characters, no trailing newline."""
    return "\n".join(source[:800].split("\n")[:10]).rstrip("\n")


def in_language(repo, language):
    return [name for name, _, path, _ in SYMBOLS[repo] if chunks.detect_language(path) == language]


# --- wiki pages in search (009 US4, research R8) -------------------------------------------------------------


def hit(name, similarity):
    return {"rowid": name, "similarity": similarity}


D = f"t-{RUN}d"

LEDGER_TEXT = (
    "# ledger\n\n"
    "`ledger` is a Python package of 2 files and 10 definitions: 10 functions.\n"
    "The ledger module records accounting transactions and keeps the balance of every account.\n\n"
    "## Key symbols\n"
    "- `post_entry` (function): Post one transaction to the ledger.\n"
    "- `balance_of` (function): The balance of an account.\n\n"
    "## Depends on\n- none\n\n## Used by\n- none\n"
)

LEDGER_SYMBOLS = [
    ("post_entry", "def post_entry(entry):\n    # post one transaction to the ledger\n    return book.append(entry)\n"),
    ("balance_of", "def balance_of(account):\n    # sum the postings of one account\n    return sum(account.postings)\n"),
]
