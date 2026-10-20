"""Helpers for the graph tests: two tiny repositories (Python with JavaScript, and Go), and readers of the
stored edges and imports.
"""

import subprocess
import uuid
import shutil
from pathlib import Path

from golestan_code_mcp import registry
from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.graph import imports as graph_imports

ENV = {"CCCTX_MAX_FILE_BYTES": "2048"}

PY = {
    "src/lib/__init__.py": "",
    "src/lib/helpers.py": '''import json


def url_for(x):
    return encode(x)


def encode(x):
    print(x)
    return json.dumps(x)


def dumps(x):
    return x
''',
    "src/lib/app.py": '''from . import helpers


class Flask:
    def url_for(self, x):
        return helpers.url_for(x)

    def open(self):
        return self.url_for(1)
''',
    "src/lib/other.py": '''class Other:
    def url_for(self):
        return 1

    def run(self):
        return self.url_for()


def a():
    return 0
''',
    "src/lib/chain.py": '''def a():
    return 1


def b():
    return a()


def c():
    return b() + a()


def d():
    return c()


def e():
    return d() + Helper()


def ping():
    return pong()


def pong():
    return ping()


def fact(n):
    return fact(n - 1)
''',
    "tests/test_app.py": '''import lib
from lib.app import Flask

lib.url_for(0)


def test_open():
    return Flask().open()


def obj_call(app):
    return app.url_for(2)


def class_call():
    return Flask.url_for(None, 3)
''',
}

GO = {
    "main.go": '''package main

import (
	"fmt"
	u "example.com/m/util"
)

func main() {
	fmt.Println(u.Helper())
}
''',
    "util/a.go": '''package util

import "example.com/m"

func Helper() int {
	return 1
}
''',
    "util/b.go": '''package util

func Other() int {
	return Helper()
}
''',
    "web/app.js": '''import { helper } from "./lib";

function start() {
  return helper();
}
''',
    "web/lib.js": '''export function helper() {
  return 1;
}

export function a() {
  return helper();
}
''',
}


def make(root, files):
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8", newline="\n")
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root, check=True,
                       capture_output=True)
    return root


def edges(conn, name):
    """(caller, caller path, callee, callee path) for every call edge of the repository; (module) for a file."""
    with conn.cursor() as cur:
        cur.execute(
            """select s.name, f.path, t.name, tf.path from ccctx_calls e
                 join ccctx_symbols s on s.id = e.caller_id join ccctx_files f on f.id = s.file_id
                 join ccctx_symbols t on t.id = e.callee_id join ccctx_files tf on tf.id = t.file_id
                 join ccctx_repos r on r.id = f.repo_id where r.name = :n
               union all
               select '(module)', f.path, t.name, tf.path from ccctx_file_calls e
                 join ccctx_files f on f.id = e.file_id
                 join ccctx_symbols t on t.id = e.callee_id join ccctx_files tf on tf.id = t.file_id
                 join ccctx_repos r on r.id = f.repo_id where r.name = :n""",
            n=name,
        )
        return sorted(cur.fetchall())


def imports(conn, name):
    with conn.cursor() as cur:
        cur.execute(
            """select f.path, t.path from ccctx_imports i
                 join ccctx_files f on f.id = i.importer_id join ccctx_files t on t.id = i.imported_id
                 join ccctx_repos r on r.id = f.repo_id where r.name = :n""",
            n=name,
        )
        return sorted(cur.fetchall())


H, APP, OTHER, CHAIN, TEST = "src/lib/helpers.py", "src/lib/app.py", "src/lib/other.py", "src/lib/chain.py", \
    "tests/test_app.py"


# --- callers, calls, impact (T009) --------------------------------------------------------------------------


def rows(results, *fields):
    return [tuple(getattr(r, f) for f in fields) for r in results]


# --- definitions (008 T004) ---------------------------------------------------------------------------------

DEFS = {
    "pkg/a.py": '''class A:
    def run(self):
        return 1


class B:
    def run(self):
        return 2


def run():
    return 3
''',
    "pkg/b.py": '''def run():
    return 4


class C:
    def run(self):
        return 5
''',
    "pkg/c.py": '''def run():
    return 6
''',
    "pkg/big.py": "def big():\n" + "    x = 1\n" * 449,  # a 450-line definition
    "notes.md": "# notes\n\nline windows only\n",
}

# --- external imports (009 T004) ----------------------------------------------------------------------------

EXT = {
    "src/pkg/__init__.py": "",
    "src/pkg/other.py": "X = 1\n",
    "src/pkg/mod.py": '''import json
import werkzeug.http
from typing import Any
from . import other
from .missing import gone
import pkg.other
''',
    "main.go": '''package main

import (
	"fmt"
	"net/http"
	u "example.com/m/util"
)

func main() {
	fmt.Println(u.Helper(), http.StatusOK)
}
''',
    "util/a.go": '''package util

import "example.com/m"

func Helper() int {
	return 1
}
''',
}

LANGUAGE_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "languages"


def language_repo(conn, root, *languages):
    """A `t-` repository of the named languages' fixture files, ingested. Returns (name, summary)."""
    root.mkdir(parents=True)
    for language in languages:
        shutil.copytree(LANGUAGE_FIXTURES / language, root / language)
    make(root, {})
    name = f"t-{uuid.uuid4().hex[:8]}"
    registry.add_repo(conn, root, name)
    return name, indexing_ingest.ingest(conn, name, ENV)


def file_imports(conn, name):
    """(importer, imported) paths of the repository's import edges."""
    with conn.cursor() as cur:
        cur.execute("""select f.path, t.path from ccctx_imports i join ccctx_files f on f.id = i.importer_id
                         join ccctx_files t on t.id = i.imported_id join ccctx_repos r on r.id = f.repo_id
                        where r.name = :n""", n=name)
        return set(cur.fetchall())


def outside(conn, name):
    """path -> the outside packages it imports."""
    with conn.cursor() as cur:
        rid = registry.repo_id(conn, name)
        paths = dict(cur.execute("select id, path from ccctx_files where repo_id = :r", r=rid).fetchall())
        return {paths[fid]: names for fid, names in graph_imports.external_imports(cur, rid).items()}
