"""The wiki tool: read_wiki."""

import posixpath
from datetime import UTC
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from golestan_code_mcp.server import app
from golestan_code_mcp.wiki import read as wiki_read
from golestan_code_mcp.wiki.store import WikiError


class WikiCitation(BaseModel):
    name: str
    kind: str
    role: Literal["key", "file", "depends", "uses", "calls"]
    repo: str | None
    path: str | None
    start_line: int | None
    end_line: int | None
    commit: str
    current_commit: str | None


class WikiPage(BaseModel):
    name: str
    repo: str
    directory: str
    language: str
    state: Literal["fresh", "stale"]
    compiled_at: str
    compiler: str
    stale_reason: str | None
    symbols: int
    text: str
    citations: list[WikiCitation]
    truncated: bool


class WikiPageInfo(BaseModel):
    name: str
    repo: str
    state: Literal["fresh", "stale"]
    summary: str


class WikiResults(BaseModel):
    status: Literal["ok", "unavailable"]
    reason: str | None
    page: WikiPage | None = None
    pages: list[WikiPageInfo] = []
    truncated: bool = False


def _iso(at) -> str:
    return (at.astimezone(UTC) if at.tzinfo else at).strftime("%Y-%m-%dT%H:%M:%SZ")


@app.mcp.tool(
    description="What does this module do? Reads the tool's wiki page about a module (a directory of indexed code): its "
    "purpose, its key symbols with one line each, the modules it depends on and the modules that use it. Use "
    "it when a question is about a module as a whole rather than one function, or after search_code returns a"
    " hit of kind page. Pass page to read one page; it returns the text, whether it is fresh or stale (and "
    "what made it stale), when and by what it was compiled, and its citations, each with the repository, path"
    " and line range of the symbol or file it names. Omit page to list the pages, optionally for one repo, "
    "with each page's name, state and first purpose line. A stale page describes code that has changed since;"
    " check its citations. Next step: get_symbol on a key symbol to read its source.",
    annotations=app.READ_ONLY,
)
@app._logged
def read_wiki(
    page: Annotated[str | None, Field(description="The page name, for example flask/json, as returned by "
                                      "search_code or by listing. Case-sensitive. Default: list the pages "
                                      "instead.")] = None,
    repo: Annotated[str | None, Field(description="Look only in this registered repository, for example flask. "
                                      "list_repositories gives the valid names. Needed when two repositories "
                                      "have a page of the same name. Default: all repositories.")] = None,
) -> WikiResults:
    def check():
        if page is not None and not page.strip():
            raise ValueError("the page name is empty")

    def query(conn):
        if page is None:
            found = wiki_read.pages(conn, repo)
            return WikiResults(status="ok", reason=None, truncated=len(found) > app.LIMIT, pages=[
                WikiPageInfo(name=p.name, repo=p.repo, state=p.state, summary=p.summary) for p in found[:app.LIMIT]])
        try:
            p = wiki_read.read(conn, page, repo)
        except WikiError as e:  # the CLI's flag is this tool's parameter
            raise ValueError(str(e).replace("; pass --repo", "; pass repo")) from None
        citations = [WikiCitation(name=posixpath.basename(c.name) if c.kind == "file" else c.name, kind=c.kind,
                                  role=c.role, repo=c.repo, path=c.path, start_line=c.start_line,
                                  end_line=c.end_line, commit=c.recorded_commit, current_commit=c.current_commit)
                     for c in p.citations]
        return WikiResults(status="ok", reason=None, page=WikiPage(
            name=p.name, repo=p.repo, directory=p.directory, language=p.language, state=p.state,
            compiled_at=_iso(p.compiled_at), compiler=p.compiler, stale_reason=p.stale_reason, symbols=p.symbols,
            text=p.text, citations=citations, truncated=p.truncated))

    return app._answer(WikiResults, check, query, empty={})
