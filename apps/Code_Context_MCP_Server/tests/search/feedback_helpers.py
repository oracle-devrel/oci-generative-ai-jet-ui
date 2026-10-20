"""Helpers for the usage feedback tests: a throwaway repository, recording uses, and searching with and without
their boost.
"""

import uuid
from types import SimpleNamespace

from golestan_code_mcp import registry
from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.wiki import build
from golestan_code_mcp.search import feedback as search_feedback
from golestan_code_mcp.search import query

from support import git

ENV = {"CCCTX_MAX_FILE_BYTES": "20000"}

WIDGETS = '''"""Widgets and how they spin."""


def spin_widget(w):
    """Spin a widget once."""
    return turn_helper(w)


def turn_helper(w):
    return w


class Widget:
    """A widget."""

    def run(self):
        return spin_widget(self)
'''

FILES = {"pkg/__init__.py": "", "pkg/widgets.py": WIDGETS} | {
    f"pkg/m{i}.py": f"def f{i}():\n    return {i}\n" for i in range(10)}


def make_repo(conn, root, files):
    """A throwaway `t-` repository, ingested, with its wiki pages built."""
    root.mkdir(parents=True)
    git(root, "init", "-q")
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8", newline="\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    name = f"t-fb{uuid.uuid4().hex[:6]}"
    registry.add_repo(conn, root, name)
    indexing_ingest.ingest(conn, name, ENV)
    build.build(conn, name)
    return SimpleNamespace(name=name, id=registry.repo_id(conn, name), root=root)


def use(repo, name="spin_widget", path="pkg/widgets.py", how="cited", session=None, days_ago=0, kind="function"):
    return {"repo_id": repo.id, "path": path, "name": name, "kind": kind, "how": how, "client": "test",
            "session": session or uuid.uuid4().hex, "run_id": None, "days_ago": days_ago}


def write(conn, *uses):
    with conn.cursor() as cur:
        for u in uses:
            search_feedback.write_use(cur, u)
    conn.commit()


def stored(conn, repo, name="spin_widget"):
    with conn.cursor() as cur:
        cur.execute("select how, session_id from ccctx_feedback where repo_id = :r and name = :n order by id",
                    r=repo.id, n=name)
        return cur.fetchall()


# --- the bounded boost in search (US2, research R5) ---

QUESTION = "spin a widget"

CAP = search_feedback.boost(1e9, 0.2)


def hammer(conn, repo, name, path="pkg/widgets.py", kind="function", count=1000):
    write(conn, *(use(repo, name, path, kind=kind) for _ in range(count)))


def search(conn, repo, question=QUESTION, **kwargs):
    return query.search(conn, question, [repo.name], env=kwargs.pop("env", {}), **kwargs)


def symbols(results):
    return [r for r in results if r.kind not in ("page", "fact")]
