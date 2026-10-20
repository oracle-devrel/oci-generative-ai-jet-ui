"""The golestan_code_mcp stdio MCP server: the app, and its nine tools in five files.

Importing this package loads the tool files in the order the tools are listed (research R6), then makes every tool
refuse arguments it does not declare. `main` starts the server; it is the `golestan-code-mcp` entry point.
"""

from pydantic import ConfigDict

# The tools are listed in this order, so the imports are not sorted.
# isort: off
from golestan_code_mcp.server import search_tools  # noqa: F401
from golestan_code_mcp.server import graph_tools  # noqa: F401
from golestan_code_mcp.server import wiki_tools  # noqa: F401
from golestan_code_mcp.server import repository_tools  # noqa: F401
from golestan_code_mcp.server import memory_tools  # noqa: F401
# isort: on
from golestan_code_mcp.server.app import main, mcp

__all__ = ["main"]

# FastMCP drops arguments a tool does not declare. Refuse them instead: a stale `repos` would otherwise widen a
# search to every repository without saying so.
for _tool in mcp._tool_manager.list_tools():
    _strict = type(_tool.fn_metadata.arg_model.__name__, (_tool.fn_metadata.arg_model,),
                   {"model_config": ConfigDict(extra="forbid")})
    _tool.fn_metadata.arg_model = _strict
    _tool.parameters = _strict.model_json_schema(by_alias=True)
