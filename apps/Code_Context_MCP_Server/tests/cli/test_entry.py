"""ccctx mcp: the server starts without connecting, and serves the tools from any directory."""

import asyncio
import sys

from golestan_code_mcp import db
from golestan_code_mcp.server import app
from golestan_code_mcp.config import load

from cli.helpers import run


# --- ccctx mcp (008) ----------------------------------------------------------------------------------------


def test_mcp_starts_the_server_without_connecting(capsys, monkeypatch):
    monkeypatch.setenv("DB_PORT", "1")  # the server reports an outage per call; starting never connects
    started = []
    monkeypatch.setattr(app, "main", lambda: started.append(True))
    code, out, _ = run(capsys, "mcp")
    assert code == 0 and started == [True] and out == ""


def test_mcp_child_process_serves_the_tools_from_any_directory(tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    # the default child environment carries no DB_* settings, so they must come from the project's .env
    params = StdioServerParameters(command=sys.executable, args=["-m", "golestan_code_mcp.cli", "mcp"],
                                   cwd=str(tmp_path))

    async def session():
        async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
            await client.initialize()  # fails if anything but protocol messages reaches stdout
            tools = [t.name for t in (await client.list_tools()).tools]
            repos = (await client.call_tool("list_repositories", {})).structuredContent
            # recall loads the memory package (numpy): on Windows a lazy load under the stdio reader used to hang
            recall = await asyncio.wait_for(client.call_tool("recall", {"limit": 1}), 60)
            return tools, repos, recall.structuredContent

    tools, repos, recall = asyncio.run(session())
    assert tools == ["search_code", "get_symbol", "find_callers", "find_callees", "impact_of", "read_wiki",
                     "list_repositories", "recall", "mark_used"]
    try:
        db.connect(load()).close()
    except Exception:
        return  # without a database the listing above is the whole check
    assert repos["database"] == "reachable", repos["reason"]
    assert recall["status"] in ("ok", "unavailable")  # answered, whatever the store's state
