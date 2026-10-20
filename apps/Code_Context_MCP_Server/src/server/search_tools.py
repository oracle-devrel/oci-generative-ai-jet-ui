"""The search tools: search_code and get_symbol."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from golestan_code_mcp.graph import queries
from golestan_code_mcp.search import query as search_query
from golestan_code_mcp.server import app
from golestan_code_mcp.server.app import Name, Repo


class SearchHit(BaseModel):
    rank: int
    score: float
    relevance: float
    feedback: float
    similarity: float | None
    keyword_rank: int | None
    semantic_rank: int | None
    repo: str
    kind: str
    name: str
    path: str
    start_line: int | None
    end_line: int | None
    language: str
    snippet: str
    state: Literal["fresh", "stale"] | None = None


class SearchResults(BaseModel):
    status: Literal["ok", "unavailable"]
    reason: str | None
    results: list[SearchHit]


@app.mcp.tool(
    description="Find code by what it does or by name: \"how are requests routed?\", \"where are sessions saved?\", "
    "\"url_for\". Use this first when you do not yet know which symbol to look at. If you already know the "
    "name, use get_symbol to read it, find_callers for its call sites, or impact_of for what a change would "
    "affect. Returns up to limit hits (default 10), best first. Each hit has the repository, path, symbol "
    "name, kind, language, line range, a snippet of the symbol's opening lines, and the scores behind its "
    "rank: the score, the relevance (the score before feedback), the feedback boost, the keyword rank and the "
    "semantic rank (null when that side did not find it). The feedback field is the boost from earlier sessions "
    "marking the result used: at most 0.2 (20 percent), fading over 30 days; relevance is the score before it. "
    "Keyword and semantic search are fused, and the definitions of an exact identifier come first. A hit of "
    "kind page is a wiki page about a whole module: its name is the page name, its path is the module's "
    "directory, its line range is null and its state says whether it is fresh or stale; read it with "
    "read_wiki. A hit of kind fact is something an earlier session worked out about the code at its path; recall "
    "lists all of them. Next step: call get_symbol with a hit's name to read its full source, or read_wiki with a "
    "page hit's name.",
    annotations=app.READ_ONLY,
)
@app._logged
def search_code(
    query: Annotated[str, Field(description="A question in plain English (how are requests routed) or an "
                                "identifier (url_for). Taken literally; there is no query syntax.")],
    repo: Annotated[str | None, Field(description="Search only this registered repository, for example flask. "
                                      "list_repositories gives the valid names. Default: all repositories.")] = None,
    language: Annotated[str | None, Field(description="Search only files of this language: one of "
                                          f"{', '.join(search_query.LANGUAGES)}. Default: all languages.")] = None,
    limit: Annotated[int, Field(description="How many hits to return, 1 to 50. Default 10.")] = 10,
    feedback: Annotated[bool, Field(description="Raise results that earlier sessions used, by at most 20 percent of "
                                    "their score. false ranks by relevance alone, exactly as with no feedback "
                                    "recorded. Default true.")] = True,
) -> SearchResults:
    def check():
        if not query.strip():
            raise ValueError("the question is empty")
        search_query.check_limit(limit)
        search_query.check_language(language)

    def query_(conn):
        hits = search_query.search(conn, query, app._repos(repo), language=language, limit=limit, feedback=feedback)
        return SearchResults(status="ok", reason=None, results=[SearchHit(**vars(h)) for h in hits])

    return app._answer(SearchResults, check, query_)


class SymbolHit(BaseModel):
    name: str
    kind: str
    repo: str
    path: str
    start_line: int
    end_line: int
    source: str
    cut: bool


class SymbolResults(BaseModel):
    status: Literal["ok", "unavailable"]
    reason: str | None
    results: list[SymbolHit]
    total: int = 0
    truncated: bool = False


@app.mcp.tool(
    description="Read the full source of a named definition (function, method, class, type) when you know its name, "
    "for example from a search_code hit. Use this instead of search_code when the name is known, and instead of "
    "opening files: it returns the source exactly as it was indexed. A bare name returns every definition with that "
    "name, each labeled with its qualified name; pass a qualified name or a repo to narrow. Returns up to 5 matches, "
    "each with its qualified name, kind, repository, path, line range and source. A source longer than 400 lines is "
    "cut there and marked cut, and its full line range is still given. total is the number of matches and "
    "truncated is true when more than 5 matched. Unparsed files indexed as line windows have no names and are not "
    "found here; use search_code for them.",
    annotations=app.READ_ONLY,
)
@app._logged
def get_symbol(name: Name, repo: Repo = None) -> SymbolResults:
    def query(conn):
        found, total = queries.definitions(conn, name, app._repos(repo))
        return SymbolResults(status="ok", reason=None, results=[SymbolHit(**vars(d)) for d in found],
                             total=total, truncated=total > len(found))

    return app._answer(SymbolResults, lambda: queries.check_name(name), query)
