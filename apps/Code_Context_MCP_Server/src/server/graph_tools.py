"""The graph tools: find_callers, find_callees and impact_of."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from golestan_code_mcp.graph import queries
from golestan_code_mcp.server import app
from golestan_code_mcp.server.app import Name, Repo


class CallerHit(BaseModel):
    repo: str
    kind: str
    name: str
    path: str
    line: int
    callee: str


class CalleeHit(BaseModel):
    caller: str
    line: int
    repo: str
    kind: str
    name: str
    path: str
    start_line: int
    end_line: int


class ImpactHit(BaseModel):
    hops: int
    repo: str
    kind: str
    name: str
    path: str
    start_line: int
    end_line: int


class CallerResults(BaseModel):
    status: Literal["ok", "unavailable"]
    reason: str | None
    results: list[CallerHit]
    truncated: bool = False


class CalleeResults(CallerResults):
    results: list[CalleeHit]


class ImpactResults(CallerResults):
    results: list[ImpactHit]


def _graph(envelope, hit, check, rows):
    """A graph question as an envelope of at most LIMIT rows."""
    def query(conn):
        found = rows(conn)
        return envelope(status="ok", reason=None, results=[hit(**vars(r)) for r in found[:app.LIMIT]],
                        truncated=len(found) > app.LIMIT)

    return app._answer(envelope, check, query)


@app.mcp.tool(
    description="Who calls this? Lists every call to the definitions matching name: the calling symbol, its kind, the "
    "repository, path and line of the call, and which definition is called. Use it before changing a function's "
    "signature or behavior, to see its direct call sites. For everything a change could reach through chains of "
    "calls, use impact_of; for what this symbol itself calls, use find_callees. Calls come from the parse tree, so "
    "comments, docstrings and strings never count. A call at module level has kind file and name (module). At most "
    "200 rows; truncated is true when more exist. Next step: get_symbol on a caller to read it.",
    annotations=app.READ_ONLY,
)
@app._logged
def find_callers(name: Name, repo: Repo = None) -> CallerResults:
    return _graph(CallerResults, CallerHit, lambda: queries.check_name(name),
                  lambda conn: queries.callers(conn, name, app._repos(repo)))


@app.mcp.tool(
    description="What does this call? Lists the indexed symbols called from the body of each definition matching "
    "name, with the line of each call and where the called symbol is defined (repository, path, line range). Use it "
    "to follow what a function does one level down; for who calls it, use find_callers. Calls into code that is not "
    "indexed, such as the standard library or dependencies, are not listed. At most 200 rows; truncated is true "
    "when more exist. Next step: get_symbol on a callee to read it.",
    annotations=app.READ_ONLY,
)
@app._logged
def find_callees(name: Name, repo: Repo = None) -> CalleeResults:
    return _graph(CalleeResults, CalleeHit, lambda: queries.check_name(name),
                  lambda conn: queries.calls(conn, name, app._repos(repo)))


@app.mcp.tool(
    description="What could break if I change this? Lists every symbol that reaches the definitions matching name "
    "through calls in at most depth hops, once each at its shortest distance (hops), nearest first, with the "
    "repository, path and line range. Use it to gauge the reach of a change; for just the direct call sites and "
    "their lines, use find_callers. At most 200 rows; truncated is true when more exist. Next step: get_symbol on "
    "the nearest symbols to see how they use it.",
    annotations=app.READ_ONLY,
)
@app._logged
def impact_of(
    name: Name,
    depth: Annotated[int, Field(description="How many call hops to follow, 1 to 5. Default 3. 1 gives only the "
                                "direct callers.")] = 3,
    repo: Repo = None,
) -> ImpactResults:
    def check():
        queries.check_name(name)
        queries.check_depth(depth)

    return _graph(ImpactResults, ImpactHit, check, lambda conn: queries.impact(conn, name, depth, app._repos(repo)))
