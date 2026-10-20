"""Reading the wiki: list a repository's pages, and read one with its citations resolved to where they are now."""

from dataclasses import dataclass
from datetime import datetime

from golestan_code_mcp.wiki import compile, store
from golestan_code_mcp.wiki import text as wiki_text
from golestan_code_mcp.wiki.store import WikiError


@dataclass(frozen=True)
class PageInfo:
    name: str
    repo: str
    directory: str
    language: str
    state: str
    symbols: int
    compiled_at: datetime
    stale_reason: str | None
    summary: str  # the first purpose sentence, or the structural one for a page without documentation


@dataclass(frozen=True)
class CitationView:
    name: str
    kind: str
    role: str
    repo: str | None  # read through the key; None once the record is gone
    path: str | None
    start_line: int | None  # None for a file
    end_line: int | None
    recorded_commit: str
    current_commit: str | None


@dataclass(frozen=True)
class Page:
    name: str
    repo: str
    directory: str
    language: str
    state: str
    compiled_at: datetime
    compiler: str
    stale_reason: str | None
    symbols: int
    text: str
    citations: list[CitationView]  # at most MAX_CITATIONS, in ROLES then name order
    truncated: bool


# --- reading -------------------------------------------------------------------------------------------------


def _summary(text: str) -> str:
    lines = text.split("\n")
    purpose = lines[3] if len(lines) > 3 and lines[3] != compile.NO_DOC else lines[2] if len(lines) > 2 else ""
    return wiki_text.SENTENCE_END.split(purpose, maxsplit=1)[0]


def pages(conn, repo: str | None = None) -> list[PageInfo]:
    """Every page, or one repository's, by repository then page name."""
    with conn.cursor() as cur:
        rid = store._repo(cur, repo) if repo is not None else None
        cur.execute("""select p.name, r.name, p.directory, p.language, p.state, p.symbols, p.compiled_at,
                              p.stale_reason, p.text
                         from ccctx_wiki_pages p join ccctx_repos r on r.id = p.repo_id
                        where :r is null or p.repo_id = :r""", r=rid)
        rows = [(*row[:-1], _summary(store._lob(row[-1]))) for row in cur.fetchall()]
    return sorted((PageInfo(*row) for row in rows), key=lambda p: (p.repo, p.name))


def read(conn, page: str, repo: str | None = None) -> Page:
    """One page with its citations, each located through its key. A name in several repositories needs `repo`."""
    with conn.cursor() as cur:
        rid = store._repo(cur, repo) if repo is not None else None
        cur.execute("""select p.id, p.name, r.name, p.directory, p.language, p.state, p.compiled_at, p.compiler,
                              p.stale_reason, p.symbols, p.text
                         from ccctx_wiki_pages p join ccctx_repos r on r.id = p.repo_id
                        where p.name = :n and (:r is null or p.repo_id = :r)""", n=page, r=rid)
        found = [(*row[:-1], store._lob(row[-1])) for row in cur.fetchall()]
        if not found:
            raise WikiError(f"no wiki page named '{page}'" + (f" in '{repo}'" if repo is not None else ""))
        if len(found) > 1:
            names = ", ".join(sorted(row[2] for row in found))
            raise WikiError(f"wiki page '{page}' is in more than one repository: {names}; pass --repo")
        page_id, *fields = found[0]
        cur.execute("""select c.name, c.kind, c.role, nvl(sr.name, fr.name), nvl(sf.path, f.path), s.start_line,
                              s.end_line, c.commit_sha,
                              case when c.role in ('key', 'calls') then s.commit_sha else fr.indexed_commit end
                         from ccctx_wiki_citations c
                         left join ccctx_symbols s on s.id = c.symbol_id
                         left join ccctx_files sf on sf.id = s.file_id
                         left join ccctx_repos sr on sr.id = sf.repo_id
                         left join ccctx_files f on f.id = c.file_id
                         left join ccctx_repos fr on fr.id = f.repo_id
                        where c.page_id = :p""", p=page_id)
        citations = sorted((CitationView(*row) for row in cur.fetchall()),
                           key=lambda c: (compile.ROLES.index(c.role), c.name))
    return Page(*fields, citations[:store.MAX_CITATIONS], len(citations) > store.MAX_CITATIONS)
