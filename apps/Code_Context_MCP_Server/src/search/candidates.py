"""Code search, candidates: the keyword query, and the symbol, page and definition rows each search starts from."""

import json
import re

SNIPPET_LINES = 10
SNIPPET_CHARS = 800
IDENTIFIER = re.compile(r"[A-Za-z_][\w.]*")
MAX_CANDIDATES = 4000  # widest pool a repository filter may ask for
PAGE_CANDIDATES = 200  # page index chunks to read: every page of a few repositories
# Oracle Text operator words: never stemmed ($NOT is a syntax error), only ever searched literally in braces
RESERVED = {
    "ABOUT", "ACCUM", "AND", "BT", "BTG", "BTI", "BTP", "EQUIV", "FUZZY", "HASPATH", "INPATH", "MDATA", "MINUS",
    "NEAR", "NOT", "NT", "NTG", "NTI", "NTP", "OR", "PT", "RT", "SQE", "SYN", "TR", "TRSYN", "TT", "WITHIN",
}


def _snippet(text: str | None) -> str:
    return "\n".join((text or "").split("\n")[:SNIPPET_LINES]).rstrip("\r\n")


def text_query(question: str, every_word: bool = True) -> str:
    """The keyword query, built so the question's characters are never operators. Empty if no word is left.

    every_word (text mode): each word literally, in braces, all required (AND).
    otherwise (hybrid's keyword side): any word, ranked by how many match (ACCUM). A plain alphabetic word
    is stemmed ($routed also finds route), anything else stays literal, so identifiers such as url_for match exactly.
    """
    words = [w for w in (w.replace("{", "").replace("}", "").replace("\\", "") for w in question.split()) if w]
    if every_word:
        return " AND ".join(f"{{{w}}}" for w in words)
    return " ACCUM ".join(f"${w}" if _stemmable(w) else f"{{{w}}}" for w in words)


def _stemmable(word: str) -> bool:
    return word.isascii() and word.isalpha() and word.upper() not in RESERVED


def _hybrid(cur, request: dict) -> list[dict]:
    lob = cur.execute("select dbms_hybrid_vector.search(json(:j)) from dual", j=json.dumps(request)).fetchone()[0]
    return json.loads(lob.read() if hasattr(lob, "read") else lob) if lob else []


def _symbols(cur, rowids: list[str]) -> dict[str, tuple]:
    """rowid -> (repo id, repo, kind, name, path, start, end, language, snippet) for the given symbol rowids."""
    found = {}
    for i in range(0, len(rowids), 500):  # stay well inside Oracle's 1000-item IN list
        chunk = rowids[i:i + 500]
        binds = ", ".join(f"chartorowid(:{n + 1})" for n in range(len(chunk)))
        cur.execute(
            f"""select rowidtochar(s.rowid), r.id, r.name, s.kind, s.name, f.path, s.start_line, s.end_line,
                       f.language, dbms_lob.substr(s.source, {SNIPPET_CHARS}, 1)
                  from ccctx_symbols s join ccctx_files f on f.id = s.file_id join ccctx_repos r on r.id = f.repo_id
                 where s.rowid in ({binds})""",
            chunk,
        )
        found.update({row[0]: (*row[1:-1], _snippet(row[-1])) for row in cur})
    return found


def _page_rows(cur, rowids: list[str]) -> dict[str, tuple]:
    """rowid -> the _symbols tuple shape for wiki pages: kind 'page', the directory as path, no lines, plus state."""
    found = {}
    for i in range(0, len(rowids), 500):
        chunk = rowids[i:i + 500]
        binds = ", ".join(f"chartorowid(:{n + 1})" for n in range(len(chunk)))
        cur.execute(
            f"""select rowidtochar(p.rowid), r.id, r.name, 'page', p.name, p.directory, null, null, p.language,
                       dbms_lob.substr(p.text, {SNIPPET_CHARS}, 1), p.state
                  from ccctx_wiki_pages p join ccctx_repos r on r.id = p.repo_id
                 where p.rowid in ({binds})""",
            chunk,
        )
        found.update({row[0]: (*row[1:-2], _snippet(row[-2]), row[-1]) for row in cur})
    return found


def _definitions(cur, name: str) -> dict[str, tuple]:
    """Symbols whose name, or the last part of their dotted name, equals the identifier (any case)."""
    cur.execute(
        f"""select rowidtochar(s.rowid), r.id, r.name, s.kind, s.name, f.path, s.start_line, s.end_line,
                       f.language, dbms_lob.substr(s.source, {SNIPPET_CHARS}, 1)
             from ccctx_symbols s join ccctx_files f on f.id = s.file_id join ccctx_repos r on r.id = f.repo_id
            where s.kind <> 'chunk'
              and (lower(s.name) = :q
                   or (length(s.name) > length(:q) and lower(substr(s.name, -length(:q) - 1)) = '.' || :q))
            order by f.path, s.start_line""",
        q=name.lower(),
    )
    return {row[0]: (*row[1:-1], _snippet(row[-1])) for row in cur}


def _page_candidates(cur, request: dict) -> tuple[list[dict], dict[str, tuple]]:
    """Page hits for the same request, with their rows. Empty without a page index or anything to ask."""
    from golestan_code_mcp.wiki import store  # wiki imports this module

    if "vector" not in request and "text" not in request:
        return [], {}
    if not cur.execute("select count(*) from user_indexes where index_name = :i", i=store.INDEX).fetchone()[0]:
        return [], {}
    hits = _hybrid(cur, request | {"hybrid_index_name": store.INDEX, "return": {"topN": PAGE_CANDIDATES}})
    return hits, _page_rows(cur, list(dict.fromkeys(h["rowid"] for h in hits)))


def _candidates(cur, request: dict, in_scope, limit: int) -> tuple[list[dict], dict[str, tuple]]:
    """Hits and their symbols. With a repository or language filter, widen the pool until `limit` are in scope."""
    if "vector" not in request and "text" not in request:
        return [], {}
    while True:
        hits = _hybrid(cur, request)
        symbols = _symbols(cur, list(dict.fromkeys(h["rowid"] for h in hits)))
        topn = request["return"]["topN"]
        found = sum(1 for s in symbols.values() if in_scope is None or in_scope(s))
        # simplified: stops at MAX_CANDIDATES; a tiny repository beside huge ones may still return fewer
        if in_scope is None or found >= limit or len(hits) < topn or topn >= MAX_CANDIDATES:
            return hits, symbols
        request["return"]["topN"] = min(topn * 4, MAX_CANDIDATES)
