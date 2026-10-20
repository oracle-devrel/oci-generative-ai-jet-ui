"""Code search: the fused query by name or meaning, with its limits, language filter and results."""

from collections.abc import Mapping
from dataclasses import dataclass

from golestan_code_mcp.config import (
    environment,
    search_candidates,
    text_weight,
    vector_weight,
)
from golestan_code_mcp.parsing import tables
from golestan_code_mcp.registry import repo_id
from golestan_code_mcp.search import candidates, model, ranking

LIMIT = 10
MAX_LIMIT = 50
LANGUAGES = tuple(sorted(set(tables.EXTENSIONS.values()) | {"text"}))  # every language the chunker assigns

MODES = ("vector", "text", "hybrid")


@dataclass(frozen=True)
class Result:
    rank: int
    score: float  # fused score in hybrid mode, the one side's score otherwise (0-100)
    similarity: float | None  # the semantic side's similarity (0-1), None if it did not find this symbol
    keyword_rank: int | None
    semantic_rank: int | None
    repo: str
    kind: str
    name: str
    path: str  # a page hit's directory
    start_line: int | None  # None for a page hit: a page has no lines in the code
    end_line: int | None
    language: str
    snippet: str  # the opening of the stored source: at most SNIPPET_LINES lines and SNIPPET_CHARS characters
    state: str | None = None  # a page hit's fresh or stale; None for a symbol
    relevance: float = 0.0  # the score before feedback
    feedback: float = 0.0  # the usage feedback boost: score = relevance * (1 + feedback); 0 for facts (011)


def check_limit(limit) -> int:
    """The limit, if it is an integer from 1 to MAX_LIMIT. Needs no database."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    return limit


def check_language(language: str | None) -> str | None:
    """The language, if it is None or one the chunker assigns. Needs no database."""
    if language is not None and language not in LANGUAGES:
        raise ValueError(f"unknown language '{language}'; valid languages: {', '.join(LANGUAGES)}")
    return language



def search(conn, question: str, repos: list[str] | None = None, mode: str = "hybrid",
           env: Mapping[str, str] | None = None, language: str | None = None, limit: int = LIMIT,
           feedback: bool = True) -> list[Result]:
    """At most `limit` symbols for the question. Identifier definitions first, then fused order.

    feedback: results earlier sessions used are raised by at most the cap, among the candidates found (011 R5).

    hybrid: keyword and semantic sides fused with RRF (UNION). vector: semantic side only, none below FLOOR.
    text: keyword side only, every word must appear. `repos` narrows to those repositories; None searches all.
    `language` narrows to files of that language. A hit is in scope when its repository and language both match.
    """
    question = (question or "").strip()
    if not question:
        raise ValueError("the question is empty")
    if mode not in MODES:
        raise ValueError(f"unknown mode '{mode}'; valid modes: {', '.join(MODES)}")
    check_limit(limit)
    check_language(language)
    env = environment() if env is None else env
    wanted = {repo_id(conn, name) for name in repos} if repos else None  # unknown names refused before searching

    def in_scope(s: tuple) -> bool:
        return (wanted is None or s[0] in wanted) and (language is None or s[7] == language)

    scoped = wanted is not None or language is not None
    model.require_model(conn)

    request: dict = {"hybrid_index_name": model.INDEX, "return": {"topN": search_candidates(env)}}
    if mode != "text":
        request["vector"] = {"search_text": question, "score_weight": vector_weight(env)}
    keywords = candidates.text_query(question, every_word=mode == "text")
    if mode != "vector" and keywords:
        request["text"] = {"contains": keywords, "score_weight": text_weight(env)}
    if "vector" in request and "text" in request:
        request |= {"search_scorer": "rrf", "search_fusion": "UNION"}

    with conn.cursor() as cur:
        hits, symbols = candidates._candidates(cur, request, in_scope if scoped else None, limit)
        definitions = (candidates._definitions(cur, question)
                       if mode != "vector" and candidates.IDENTIFIER.fullmatch(question) else {})
        page_hits, pages = candidates._page_candidates(cur, request)

    fused = ranking._fuse(hits, symbols, in_scope)
    found = ranking._fuse(page_hits, pages, in_scope)
    boosts = ranking._boosts(conn, symbols | definitions | pages, env) if feedback else {}
    if boosts:
        ranking._boost(fused + found, boosts)
        fused.sort(key=lambda f: -f["score"])  # stable: ties keep the fused order
    by_rowid = {f["rowid"]: f for f in fused}
    first = [by_rowid.get(r) or {"rowid": r, "score": 0.0, "relevance": 0.0, "feedback": 0.0, "similarity": None,
                                 "text": None, "vector": None}
             for r, d in definitions.items() if in_scope(d)]
    first.sort(key=lambda f: (f["rowid"] not in by_rowid, -f["score"]))  # found by the search first, then path
    # "the json module": its page first
    named = [f for f in found if ranking.names_module(question, pages[f["rowid"]][3])]
    rest = ranking._place([f for f in fused if f["rowid"] not in definitions], [f for f in found if f not in named])
    rest = sorted(named, key=lambda f: -(f["similarity"] or -1)) + rest
    rows = symbols | definitions | pages
    if mode != "text":  # fact hits are placed by similarity, like pages, and never above a definition (010 R14)
        from golestan_code_mcp.memory import recall  # memory imports this module

        facts = recall.search_facts(conn, question, repos, language)
        rest = ranking._place(rest, [{"rowid": f"fact:{n}", "score": 0.0, "relevance": 0.0, "feedback": 0.0,
                                      "similarity": f["similarity"], "text": None, "vector": n}
                                     for n, f in enumerate(facts, 1)])
        rows |= {f"fact:{n}": (None, f["repo"], "fact", f["name"], f["path"], f["start_line"], f["end_line"],
                               f["language"], f["snippet"], "fresh") for n, f in enumerate(facts, 1)}
    return [
        Result(rank, f["score"], f["similarity"], f["text"], f["vector"], *rows[f["rowid"]][1:],
               relevance=f["relevance"], feedback=f["feedback"])
        for rank, f in enumerate((first + rest)[:limit], 1)
    ]
