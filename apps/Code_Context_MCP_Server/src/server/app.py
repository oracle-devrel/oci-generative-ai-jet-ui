"""The MCP server: the FastMCP app, its instructions, and what every tool shares (logging, recording, answers).

Logs go to stderr; stdout carries the protocol.
"""

import functools
import inspect
import json
import logging
import sys
import time
import uuid
from typing import Annotated

import oracledb
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from golestan_code_mcp import db, schema
from golestan_code_mcp.config import load
from golestan_code_mcp.memory import runs as memory_runs

NAME = "golestan_code_mcp"
INSTRUCTIONS = (
    "This server indexes codebases and remembers what earlier sessions learned about them. At the start of a session, "
    "call recall (with the repository if you know it) to load the facts already worked out. Call recall before "
    "searching for something an earlier session may already have found. Use search_code, get_symbol and the graph "
    "tools for what recall does not answer.")
mcp = FastMCP(NAME, instructions=INSTRUCTIONS)
log = logging.getLogger("golestan_code_mcp.server")
READ_ONLY = ToolAnnotations(readOnlyHint=True)
SESSION = str(uuid.uuid4())  # one stdio connection per process: the session a use belongs to (011 research R2)
# (repo, path, name) -> the run of the latest search_code that returned it, for linking uses to it.
# ponytail: one stdio session per process; key by ctx.session for multi-session transports
_returned: dict[tuple[str, str, str], dict] = {}
LIMIT = 200  # graph tools return at most this many rows; truncated says when more existed

Name = Annotated[str, Field(description="A bare name (url_for), which matches url_for and every Class.url_for, or a "
                            "qualified name (Flask.url_for), which matches only that definition. Case-sensitive.")]
Repo = Annotated[str | None, Field(description="Look only in this registered repository, for example flask. "
                                   "list_repositories gives the valid names. Default: all repositories.")]


def _client() -> str | None:
    """The calling client's name and version from its handshake, or None outside a session."""
    try:
        info = mcp.get_context().session.client_params.clientInfo
        return f"{info.name} {info.version}"
    except Exception:  # noqa: BLE001 - no request context (direct calls, tests)
        return None


def _use(repo: str, path: str, name: str, kind: str, how: str) -> None:
    """Queue a use of a result behind the runs before it, linked to the search that returned it, if one did."""
    memory_runs.record({"use": {"repo": repo, "path": path, "name": name, "kind": kind, "how": how, "client": _client(),
                                "session": SESSION, "run": _returned.get((repo, path, name))}})


def _opened(tool: str, result) -> None:
    """Reading a result this session's searches returned is an opened use (011 research R8)."""
    if getattr(result, "status", None) != "ok":
        return
    if tool == "get_symbol":
        read = [(h.repo, h.path, h.name, h.kind) for h in result.results]
    elif tool == "read_wiki" and result.page is not None:
        read = [(result.page.repo, result.page.directory, result.page.name, "page")]
    else:
        return
    for repo, path, name, kind in read:
        if (repo, path, name) in _returned:
            _use(repo, path, name, kind, "opened")


def _logged(tool):
    """One structured record per call: tool, latency, status, result count, never the arguments or results.
    Then the call is recorded as a run for agent memory, which can never change or delay the answer (010 FR-003),
    and a search's results are remembered for the uses that may follow (011)."""
    signature = inspect.signature(tool)

    @functools.wraps(tool)
    def wrapper(*args, **kwargs):
        started, result = time.monotonic(), None
        try:
            result = tool(*args, **kwargs)
            return result
        finally:
            ms = round((time.monotonic() - started) * 1000)
            items = next((getattr(result, a) for a in ("results", "repositories", "pages", "facts")
                          if hasattr(result, a)), None)
            if items is not None and getattr(result, "page", None) is not None:
                items = [result.page]
            log.info(json.dumps({
                "event": "tool", "tool": tool.__name__, "ms": ms,
                "status": "error" if result is None else getattr(result, "status", None) or result.database,
                "results": None if items is None else len(items),
            }))
            try:
                # FastMCP passes every parameter, defaults included: record the effective call, minus unset ones
                arguments = {k: v for k, v in signature.bind(*args, **kwargs).arguments.items() if v is not None}
                run = memory_runs.run_of(tool.__name__, arguments, result, _client(), ms)
                memory_runs.record(run)
                if tool.__name__ == "search_code":
                    _returned.update({(r["repo"], r["path"], r["name"]): run for r in run["results"]})
                _opened(tool.__name__, result)
            except Exception:  # noqa: BLE001 - recording must never reach the client
                log.exception("could not record the run")
    return wrapper


def _answer(envelope, check, query, empty=None):
    """Refuse bad input before connecting, then answer from the core. Every failure is an unavailable result,
    with the envelope's `empty` fields (no results by default)."""
    empty = {"results": []} if empty is None else empty
    try:
        check()
        with db.connect(load()) as conn:
            schema.migrate(conn)
            return query(conn)
    except ValueError as e:  # ConfigError, RegistryError, ModelError and WikiError are ValueErrors
        return envelope(status="unavailable", reason=str(e), **empty)
    except oracledb.Error as e:
        return envelope(status="unavailable", reason=db.describe(e), **empty)


def _repos(repo: str | None) -> list[str] | None:
    return [repo] if repo else None


def main() -> None:
    log.addHandler(logging.StreamHandler(sys.stderr))  # stdout carries the protocol
    log.setLevel(logging.INFO)
    log.propagate = False
    # On Windows, loading an extension module (numpy's, under the memory package) while the stdio reader thread is
    # blocked reading stdin hangs the process. The first fact search or recall would do that, so load it first.
    import oracleagentmemory.core  # noqa: F401
    import oracleagentmemory.core.embedders  # noqa: F401

    mcp.run("stdio")
