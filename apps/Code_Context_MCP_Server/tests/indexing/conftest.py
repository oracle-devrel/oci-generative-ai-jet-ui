"""Fixtures of the ingest tests: the throwaway repositories they ingest."""

import pytest

from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.parsing import tables

from indexing.helpers import APP_PY, CS, ENV, LIB_PY, MAIN_GO, USE_PY, WEB_JS, pkg_module, register, stored, write
from support import git


@pytest.fixture
def repo(tmp_path):
    """A committed repository with one file for every skip reason and every chunking path."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    files = {
        ".gitignore": "*.log\nbuild/\n",
        "app.py": APP_PY,
        "main.go": MAIN_GO,
        "web.js": WEB_JS,
        "broken.py": "def oops(:\n    pass\n",
        "notes.txt": "".join(f"line {i}\n" for i in range(1, 131)),
        "empty.txt": "",
        "vendor/dep.go": MAIN_GO,
        "big.txt": "x" * 3000,
        "app.log": "ignored\n",
        "build/out.txt": "ignored\n",
    }
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8", newline="\n")
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    (root / "latin1.txt").write_bytes(b"caf\xe9\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    return root


@pytest.fixture
def graph_repo(repo):
    write(repo / "lib.py", LIB_PY)
    write(repo / "use.py", USE_PY)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "graph")
    return repo


@pytest.fixture
def wiki_repo(tmp_path):
    """A package of 10 definitions in two files, and an uncited file elsewhere."""
    root = tmp_path / "wrepo"
    root.mkdir()
    git(root, "init", "-q")
    (root / "pkg").mkdir()
    (root / "other").mkdir()
    write(root / "pkg" / "a.py", pkg_module("a"))
    write(root / "pkg" / "b.py", pkg_module("b"))
    write(root / "other" / "x.py", "def lonely():\n    return 0\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    return root


@pytest.fixture
def before_csharp(conn, tmp_path, monkeypatch):
    """(name, root) of a repository ingested while `.cs` had no rules: its Cart.cs is stored as `text` windows."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    for rel, text in {"app.py": APP_PY, "shop/Cart.cs": CS}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8", newline="\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    name = register(conn, root)
    with monkeypatch.context() as m:
        m.delitem(tables.EXTENSIONS, ".cs")
        assert indexing_ingest.ingest(conn, name, ENV).no_grammar == 1
    assert {(r[1], r[4]) for r in stored(conn, name) if r[0] == "shop/Cart.cs"} == {("text", "chunk")}
    return name, root
