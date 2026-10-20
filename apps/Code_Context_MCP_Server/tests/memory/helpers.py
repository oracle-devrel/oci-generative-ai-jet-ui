"""Helpers for the memory tests: sample runs and repositories, tool calls as a client makes them, and readers of
runs, facts and uses.
"""

import uuid
import json

from golestan_code_mcp import db
from golestan_code_mcp.memory import consolidate
from golestan_code_mcp.memory import findings
from golestan_code_mcp.memory import recall
from golestan_code_mcp.memory import runs as memory_runs
from golestan_code_mcp.memory import store
from golestan_code_mcp.config import load
from golestan_code_mcp.server import app
from golestan_code_mcp import registry
from golestan_code_mcp.indexing import ingest as indexing_ingest

from support import commit, git, write

HIT = dict(rank=1, score=40.0, similarity=0.6, keyword_rank=1, semantic_rank=2, repo="flask", kind="function",
           name="url_for", path="src/flask/helpers.py", start_line=188, end_line=246, language="python",
           snippet="def url_for(...):", relevance=40.0, feedback=0.0)

FORBIDDEN = {"source", "snippet", "text"}


def fields(run):
    return {k for row in run["results"] for k in row}


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

OTHER = "from pkg.widgets import spin_widget\n\n\ndef use_widget():\n    return spin_widget(1)\n"

FILES = {"pkg/__init__.py": "", "pkg/widgets.py": WIDGETS, "pkg/other.py": OTHER}


def make_repo(conn, root, files=FILES):
    root.mkdir(parents=True)
    git(root, "init", "-q")
    write(root, files)
    commit(root, "init")
    name = f"t-{uuid.uuid4().hex[:8]}"
    registry.add_repo(conn, root, name)
    indexing_ingest.ingest(conn, name, ENV)
    return name


def ask(tool, **arguments):
    """Call a tool the way a client does; its run is recorded by the server."""
    result = app.mcp._tool_manager.get_tool(tool).fn(**arguments)
    memory_runs.flush()
    return result


def pending_runs(conn, name):
    with conn.cursor() as cur:
        return findings.pending(cur, registry.repo_id(conn, name))


def facts_of(conn, name):
    return {f.subject: f for f in recall.facts(conn, name, limit=50)}


def synthetic(name, tool, question, results, arguments=None):
    return {"tool": tool, "arguments": arguments or {"query": question, "repo": name}, "question": question,
            "client": None, "status": "ok", "reason": None, "ms": 1, "result_count": len(results),
            "results": results, "repos": [name]}


def hit(name, symbol, path="pkg/widgets.py", kind="function"):
    return {"kind": kind, "repo": name, "name": symbol, "path": path, "start_line": 1, "end_line": 2}


# --- distillers (T016) ---


class FakeLlm:
    def __init__(self, text="`spin_widget` spins a `Widget` and is used by `use_widget`.", fail=False):
        self.text, self.fail, self.prompts = text, fail, []

    def generate(self, prompt, response_json_schema=None, **_):
        self.prompts.append(prompt)
        if self.fail:
            raise RuntimeError("model down")
        from oracleagentmemory.apis.llms.llm import LlmResponse
        return LlmResponse(json.dumps({"text": self.text}))


def with_model(monkeypatch, llm):
    monkeypatch.setattr(store, "model", lambda env=None: (llm, "llm:fake/model"))


# --- recall (T023) ---


def seed(conn, name, subjects):
    """One consolidated fact per (symbol, question, count of agreeing runs)."""
    with db.connect(load()) as c:
        memory_runs.store_runs(c, [synthetic(name, "search_code", f"{q} {i}", [hit(name, s)])
                              for s, q, n in subjects for i in range(n)])
    consolidate.consolidate(conn, name)


# --- keeping pace with the code (T028 to T031) ---


def change(conn, name, root, files, remove=()):
    for rel in remove:
        (root / rel).unlink()
    write(root, files)
    commit(root)
    return indexing_ingest.ingest(conn, name, ENV)


def run_count(conn):
    with conn.cursor() as cur:
        return cur.execute("select count(*) from ccctx_memory_runs").fetchone()[0]


def a_use(name, symbol, run=None, how="cited", path="pkg/widgets.py"):
    return {"use": {"repo": name, "path": path, "name": symbol, "kind": "function", "how": how, "client": "c",
                    "session": uuid.uuid4().hex, "run": run}}


def uses_of(conn, name):
    memory_runs.flush()
    with conn.cursor() as cur:
        cur.execute("select name, how, run_id from ccctx_feedback where repo_id = :r order by id",
                    r=registry.repo_id(conn, name))
        return cur.fetchall()
