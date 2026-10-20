"""The memory tools: recall and mark_used."""

from typing import Annotated, Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from golestan_code_mcp import registry
from golestan_code_mcp.memory import recall as memory_recall
from golestan_code_mcp.search import feedback as search_feedback
from golestan_code_mcp.search import query as search_query
from golestan_code_mcp.server import app, wiki_tools


class RecallSource(BaseModel):
    role: Literal["subject", "related"]
    name: str
    kind: str
    repo: str
    path: str | None
    start_line: int | None
    end_line: int | None


class RecallFact(BaseModel):
    id: str
    repo: str
    subject: str
    kind: str
    state: Literal["fresh", "stale"]
    stale_reason: str | None
    confidence: float
    distiller: str
    text: str
    questions: list[str]
    runs: list[int]
    updated_at: str
    sources: list[RecallSource]


class RecallRun(BaseModel):
    id: int
    at: str
    tool: str
    question: str | None
    client: str | None
    status: str
    result_count: int
    top: dict | None


class RecallResults(BaseModel):
    status: Literal["ok", "unavailable"]
    reason: str | None
    facts: list[RecallFact] = []
    runs: list[RecallRun] = []
    total: int = 0
    truncated: bool = False


@app.mcp.tool(
    description="Call this at the start of a session, and before searching, to load what earlier sessions already "
    "worked out about a codebase. Returns the stored facts, fresh first and most confident first, or most related to "
    "topic when one is given, and the most recent tool calls. Each fact has its subject (a symbol or wiki page), its "
    "text, a confidence from 0 to 1, whether it is fresh or stale (and why), what wrote its text (a configured model "
    "or the template distiller), the IDs of the runs it was distilled from, and the repository, path and line range "
    "of the code it describes. A stale fact describes code that has changed since; check it with get_symbol before "
    "relying on it. Facts are distilled from earlier calls by ccctx memory consolidate and after every ingestion. Next "
    "step: get_symbol on a fact's subject to read its source, or search_code for what recall does not cover.",
    annotations=app.READ_ONLY,
)
@app._logged
def recall(
    repo: Annotated[str | None, Field(description="Recall only this registered repository, for example flask. "
                                      "list_repositories gives the valid names. Default: all repositories.")] = None,
    topic: Annotated[str | None, Field(description="Put the facts most related to this first, for example "
                                       "\"sessions\" or \"url_for\". Default: most confident first.")] = None,
    limit: Annotated[int, Field(description="How many facts to return, 1 to 50. Default 20.")] = 20,
) -> RecallResults:
    def check():
        search_query.check_limit(limit)
        if topic is not None and not topic.strip():
            raise ValueError("the topic is empty")

    def query(conn):
        r = memory_recall.recall(conn, repo, topic, limit)
        return RecallResults(status="ok", reason=None, total=r.total, truncated=r.total > len(r.facts), facts=[
            RecallFact(id=f.id, repo=f.repo, subject=f.subject, kind=f.kind, state=f.state, stale_reason=f.stale_reason,
                       confidence=f.confidence, distiller=f.distiller, text=f.text, questions=f.questions[:5],
                       runs=f.runs[-20:], updated_at=f.updated_at, sources=[RecallSource(**s) for s in f.sources])
            for f in r.facts], runs=[
            RecallRun(id=x.id, at=wiki_tools._iso(x.called_at), tool=x.tool, question=x.question, client=x.client,
                      status=x.status, result_count=x.result_count, top=x.top) for x in r.runs])

    return app._answer(RecallResults, check, query, empty={})


class MarkUsedResult(BaseModel):
    status: Literal["ok", "unavailable"]
    reason: str | None
    repo: str
    path: str
    name: str
    kind: str | None
    linked: bool


@app.mcp.tool(
    description="Tell the server a result helped: call this for each search hit you cite in your answer or rely on. "
    "Pass the hit's repo, path and name exactly as search_code returned them. Results that clients mark get a small, "
    "capped boost in later searches, and the boost fades over 30 days. Reading a hit with get_symbol or read_wiki "
    "already counts as a lighter use, so mark only what you actually used.",
    annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False),
)
@app._logged
def mark_used(
    repo: Annotated[str, Field(description="The hit's repository, exactly as search_code returned it, for example "
                               "flask.")],
    path: Annotated[str, Field(description="The hit's path, exactly as search_code returned it (a page hit's "
                               "directory).")],
    name: Annotated[str, Field(description="The hit's name, exactly as search_code returned it, for example url_for "
                               "or Flask.url_for.")],
) -> MarkUsedResult:
    def query(conn):
        rid = registry.repo_id(conn, repo)
        with conn.cursor() as cur:
            kind = search_feedback.resolve(cur, rid, path, name)
        if kind is None:
            raise ValueError(f"not found: no indexed symbol or page named '{name}' at '{path}' in '{repo}'")
        app._use(repo, path, name, kind, "cited")  # recorded in the background: a failure never changes this answer
        return MarkUsedResult(status="ok", reason=None, repo=repo, path=path, name=name, kind=kind,
                              linked=(repo, path, name) in app._returned)

    return app._answer(MarkUsedResult, lambda: None, query,
                       empty={"repo": repo, "path": path, "name": name, "kind": None, "linked": False})
