"""Helpers for the server tests: calling tools over an in-memory session as a client does, the tool contracts,
and the core results each tool must match.
"""

import asyncio
import re
import subprocess
import uuid
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import Implementation

from golestan_code_mcp import db, registry
from golestan_code_mcp.server import app
from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.wiki import build
from golestan_code_mcp.search import model
from golestan_code_mcp.graph import queries
from golestan_code_mcp.config import load
from golestan_code_mcp.memory import runs

SPECS = Path(__file__).resolve().parents[2] / "specs"

CONTRACT = SPECS / "008-mcp-tools" / "contracts" / "tools.md"

WIKI_CONTRACT = SPECS / "009-module-wiki" / "contracts" / "tools.md"

MEMORY_CONTRACT = SPECS / "010-agent-memory" / "contracts" / "tools.md"

FEEDBACK_CONTRACT = SPECS / "011-usage-feedback" / "contracts" / "tools.md"

LANGUAGE_CONTRACT = SPECS / "012-language-coverage" / "contracts" / "tools.md"

TOOLS = ["search_code", "get_symbol", "find_callers", "find_callees", "impact_of", "read_wiki", "list_repositories",
         "recall", "mark_used"]

FACT_SENTENCE = ("A hit of kind fact is something an earlier session worked out about the code at its path; recall "
                 "lists all of them.")


async def _session(action):
    async with create_connected_server_and_client_session(app.mcp) as client:
        return await action(client)


def raw_call(tool, **arguments):
    return asyncio.run(_session(lambda c: c.call_tool(tool, arguments)))


def call(tool, **arguments):
    result = raw_call(tool, **arguments)
    assert not result.isError
    return result.structuredContent


def listed():
    return {t.name: t for t in asyncio.run(_session(lambda c: c.list_tools())).tools}


def contract():
    """The tool and parameter descriptions written in the contracts: step 8's, with steps 9 and 10 on top."""
    text = CONTRACT.read_text(encoding="utf-8")
    wiki_text = WIKI_CONTRACT.read_text(encoding="utf-8")
    tools = dict(re.findall(r"^\*\*`(\w+)`\*\*: (.+)$", text, re.MULTILINE))
    tools |= dict(re.findall(r"^\*\*`(\w+)`\*\*: (.+)$", wiki_text, re.MULTILINE))
    params = {}
    table = text.split("### Parameter descriptions", 1)[1].split("Parameter order", 1)[0]
    for line in table.splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)]
        if len(cells) == 6 and cells[2].startswith("`"):
            for tool in re.findall(r"`(\w+)`", cells[1]):
                params[(tool, cells[2].strip("`"))] = cells[4]
    table = wiki_text.split("## `read_wiki`", 1)[1].split("### Parameters", 1)[1].split("Parameter order", 1)[0]
    for line in table.splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)]
        if len(cells) == 5 and cells[1].startswith("`"):
            params[("read_wiki", cells[1].strip("`"))] = cells[3]
    memory_text = MEMORY_CONTRACT.read_text(encoding="utf-8")
    tools |= dict(re.findall(r"^\*\*`(recall)`\*\*: (.+)$", memory_text, re.MULTILINE))
    tools["search_code"] = tools["search_code"].replace("read it with read_wiki.", f"read it with read_wiki. {FACT_SENTENCE}")
    table = memory_text.split("## `recall`", 1)[1].split("### Parameters", 1)[1].split("Unknown arguments", 1)[0]
    for line in table.splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)]
        if len(cells) == 5 and cells[1].startswith("`"):
            params[("recall", cells[1].strip("`"))] = cells[3]
    feedback_text = FEEDBACK_CONTRACT.read_text(encoding="utf-8")
    tools |= dict(re.findall(r"^\*\*`(mark_used)`\*\*: (.+)$", feedback_text, re.MULTILINE))
    scores, added = (re.search(rf'^{k}: "(.+)"$', feedback_text, re.MULTILINE).group(1) for k in ("Scores", "Added"))
    old_scores = ("the scores behind its rank: the fused score, the keyword rank and the semantic rank (null when that "
                  "side did not find it).")
    assert old_scores in tools["search_code"]
    tools["search_code"] = tools["search_code"].replace(old_scores, f"{scores} {added}")
    for section, tool in (("## `mark_used`", "mark_used"), ("## `search_code`", "search_code")):
        table = feedback_text.split(section, 1)[1].split("| Parameter | Type | Description |", 1)[1].split("\n\n", 1)[0]
        for line in table.splitlines():
            cells = [c.strip() for c in line.split("|")]
            if len(cells) == 5 and cells[1].startswith("`"):
                params[(tool, cells[1].strip("`"))] = cells[3]
    languages = LANGUAGE_CONTRACT.read_text(encoding="utf-8").split("| Parameter | Description |", 1)[1]
    params[("search_code", "language")] = re.search(r"^\| `language` \| (.+) \|$", languages, re.M).group(1)
    return tools, params


def instructions():
    """The server instructions quoted in specs/010-agent-memory/contracts/tools.md."""
    section = MEMORY_CONTRACT.read_text(encoding="utf-8").split("## Server instructions", 1)[1].split("## ", 1)[0]
    return " ".join(line[2:].strip() for line in section.splitlines() if line.startswith("> "))


# --- search_code ------------------------------------------------------------------------------------------------

def ready():
    try:
        conn = db.connect(load())
        model.require_model(conn)
    except Exception:
        pytest.skip("database unreachable or hybrid index not built")
    return conn


# --- get_symbol -------------------------------------------------------------------------------------------------

def definitions(name, repo=None):
    try:
        with db.connect(load()) as conn:
            found, total = queries.definitions(conn, name, [repo] if repo else None)
    except Exception as e:  # database down or flask not indexed here
        pytest.skip(f"flask not indexed: {e}")
    return [vars(d) for d in found], total


# --- find_callers, find_callees, impact_of ----------------------------------------------------------------------

CORE = {"find_callers": queries.callers, "find_callees": queries.calls, "impact_of": queries.impact}

GRAPH_CALLS = [
    ("find_callers", {"name": "url_for", "repo": "flask"}),
    ("find_callers", {"name": "Flask.url_for"}),
    ("find_callees", {"name": "url_for", "repo": "flask"}),
    ("impact_of", {"name": "url_for", "repo": "flask"}),
    ("impact_of", {"name": "Flask.url_for", "depth": 1, "repo": "flask"}),
]


def core(tool, arguments):
    repo = arguments.get("repo")
    extra = [arguments.get("depth", 3)] if tool == "impact_of" else []
    try:
        with db.connect(load()) as conn:
            return [vars(r) for r in CORE[tool](conn, arguments["name"], *extra, [repo] if repo else None)]
    except Exception as e:  # database down or flask not indexed here
        pytest.skip(f"flask not indexed: {e}")


# --- outages and logging ----------------------------------------------------------------------------------------

UNREACHABLE = [
    ("search_code", {"query": "routing"}),
    ("get_symbol", {"name": "url_for"}),
    ("find_callers", {"name": "url_for"}),
    ("find_callees", {"name": "url_for"}),
    ("impact_of", {"name": "url_for"}),
    ("read_wiki", {"page": "flask/json"}),
]

# --- read_wiki --------------------------------------------------------------------------------------------------

PKG = '"""Ledger accounting for the demo."""\n' + "".join(
    f'\n\ndef post{i}():\n    """Post entry {i}."""\n    return {i}\n' for i in range(10))


def wiki_repo(conn, root):
    """Register, ingest and build the wiki of a repository with one page, `pkg`. Returns its name."""
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "__init__.py").write_text('"""The demo ledger package."""\n')
    (root / "src" / "pkg" / "core.py").write_text(PKG)
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root, check=True,
                       capture_output=True)
    name = f"t-{uuid.uuid4().hex[:8]}"
    registry.add_repo(conn, str(root), name)
    indexing_ingest.ingest(conn, name)
    build.build(conn, name)
    return name


CLIENT = Implementation(name="test-client", version="9.9")


def as_client(tool, **arguments):
    async def go():
        async with create_connected_server_and_client_session(app.mcp, client_info=CLIENT) as client:
            return await client.call_tool(tool, arguments)
    return asyncio.run(go())


def runs_since(conn, before):
    runs.flush()
    with conn.cursor() as cur:
        cur.execute("select tool, arguments, question, client, status, reason, result_count from ccctx_memory_runs"
                    " where id > :b order by id", b=before)
        return cur.fetchall()


MARK = f"zz_{uuid.uuid4().hex[:8]}"

CALLS = [
    ("search_code", {"query": f"where is {MARK}"}),
    ("get_symbol", {"name": MARK}),
    ("find_callers", {"name": MARK}),
    ("find_callees", {"name": MARK}),
    ("impact_of", {"name": MARK, "depth": 2}),
    ("read_wiki", {}),
    ("list_repositories", {}),
    ("recall", {}),
]


def uses(conn, repo):
    runs.flush()
    with conn.cursor() as cur:
        cur.execute("""select f.name, f.path, f.kind, f.how, f.run_id, f.client from ccctx_feedback f
                        where f.repo_id = :r order by f.id""", r=registry.repo_id(conn, repo))
        return cur.fetchall()


def newest_run(conn, tool):
    runs.flush()
    with conn.cursor() as cur:
        return cur.execute("select max(id) from ccctx_memory_runs where tool = :t", t=tool).fetchone()[0]


def search_hit(repo, name):
    out = as_client("search_code", query="post entry for the demo ledger", repo=repo, limit=20).structuredContent
    return next(h for h in out["results"] if h["name"] == name)
