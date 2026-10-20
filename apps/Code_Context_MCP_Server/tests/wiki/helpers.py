"""Helpers for the wiki tests: sample repositories, and readers of the stored pages and citations."""

import posixpath
import uuid
import shutil
from pathlib import Path

from golestan_code_mcp import registry
from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.wiki import build as wiki_build

from support import commit, git, write

ENV = {"CCCTX_MAX_FILE_BYTES": "20000"}


def functions(prefix: str, n: int) -> str:
    return "".join(f"def {prefix}{i}():\n    return {i}\n\n\n" for i in range(n))


CORE_PY = '''"""Core widget code. See core.py at line 3 for details."""
import json
from typing import Any

from .sub.util import sub_a


class Widget:
    """A widget, see :class:`~pkg.core.Gadget` for more. Defined in core.py."""

    def spin(self):
        """Spin it."""
        return sub_a()

    def stop(self):
        return 1


class Gadget:
    """A gadget made by :func:`make_widget`."""


def make_widget():
    """Make a ``Widget`` instance."""
    return Widget()


''' + functions("f", 5)

TESTS_PY = "from pkg.core import Widget, make_widget\nimport pkg\n\n\n" + "".join(
    f"def test_{i}():\n    return {'make_widget' if i == 2 else 'Widget'}()\n\n\n" for i in range(12))

SERVER_GO = """// Copyright header, not attached.

// Package server serves widgets.
package server

import (
	"fmt"
	"net/http"
)

// Server holds the state.
type Server struct{}

// Start starts it.
func (s *Server) Start() {
	fmt.Println(http.StatusOK)
}
""" + "".join(f"\nfunc F{i}() {{\n}}\n" for i in range(8))

FILES = {
    "src/pkg/__init__.py": '"""Widgets for the demo package.\n\nSecond paragraph.\n"""\nfrom .core import Widget, make_widget\n',
    "src/pkg/core.py": CORE_PY,
    "src/pkg/sub/util.py": functions("sub_", 10).replace("def sub_0", "def sub_a"),
    "nine/mod.py": functions("n", 9),
    "nine/notes.txt": "".join(f"note {i}\n" for i in range(130)),
    "docs/guide.md": "".join(f"guide {i}\n" for i in range(200)),
    "tests/test_pkg.py": TESTS_PY,
    "root.py": functions("r", 10),
    "x/mod.py": 'class Thing:\n    """A thing in x."""\n\n\n' + functions("x", 9),
    "src/x/mod.py": functions("y", 10),
    "server/server.go": SERVER_GO,
}


def make_repo(conn, root, files=FILES, build=True):
    root.mkdir()
    git(root, "init", "-q")
    write(root, files)
    commit(root, "init")
    name = f"t-{uuid.uuid4().hex[:8]}"
    registry.add_repo(conn, root, name)
    indexing_ingest.ingest(conn, name, ENV)
    if build:
        wiki_build.build(conn, name)
    return name


def rid(conn, name):
    return registry.repo_id(conn, name)


def lob(v):
    return v.read() if hasattr(v, "read") else v


def page_rows(conn, name):
    with conn.cursor() as cur:
        cur.execute("""select p.directory, p.name, p.language, p.symbols, p.text, p.search_text, p.state,
                              p.compiler, p.stale_reason
                         from ccctx_wiki_pages p join ccctx_repos r on r.id = p.repo_id where r.name = :n""", n=name)
        return {row[1]: tuple(lob(v) for v in row) for row in cur}


def citation_rows(conn, name):
    with conn.cursor() as cur:
        cur.execute("""select p.name, c.role, c.name, c.kind, c.commit_sha, c.content_hash, c.symbol_id, c.file_id
                         from ccctx_wiki_citations c join ccctx_wiki_pages p on p.id = c.page_id
                         join ccctx_repos r on r.id = p.repo_id where r.name = :n""", n=name)
        return sorted(cur.fetchall())


def text(conn, name, page):
    return page_rows(conn, name)[page][4]


# --- citations -----------------------------------------------------------------------------------------------


def module_name(path):
    directory = posixpath.dirname(path) or "."
    return directory.removeprefix("src/")


# --- staleness -----------------------------------------------------------------------------------------------


def execute(conn, sql, **binds):
    with conn.cursor() as cur:
        cur.execute(sql, binds)
    conn.commit()


def symbol_of(conn, name, symbol):
    with conn.cursor() as cur:
        return cur.execute("""select s.id, s.commit_sha from ccctx_symbols s join ccctx_files f on f.id = s.file_id
                               where f.repo_id = :r and s.name = :s""", r=rid(conn, name), s=symbol).fetchone()


def mark(conn, name):
    with conn.cursor() as cur:
        marked = wiki_build.mark_stale(cur, rid(conn, name))
    conn.commit()
    return marked


LANGUAGE_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "languages"


def language_wiki(conn, root, *languages):
    """A `t-` repository of the named languages' fixture files, ingested and with its wiki built. Returns its name."""
    root.mkdir(parents=True)
    for language in languages:
        shutil.copytree(LANGUAGE_FIXTURES / language, root / language)
    git(root, "init", "-q")
    commit(root, "init")
    name = f"t-{uuid.uuid4().hex[:8]}"
    registry.add_repo(conn, root, name)
    indexing_ingest.ingest(conn, name, ENV)
    wiki_build.build(conn, name)
    return name


def page_of(conn, name, directory):
    return next(row for row in page_rows(conn, name).values() if row[0] == directory)
