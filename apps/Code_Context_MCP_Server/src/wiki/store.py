"""Wiki storage: the pages' hybrid index, and writing a page with its citations."""

from dataclasses import dataclass

import oracledb

from golestan_code_mcp import db
from golestan_code_mcp.search import model
from golestan_code_mcp.wiki import compile

INDEX = "CCCTX_WIKI_HYBRID_IX"

MAX_CITATIONS = 200


class WikiError(ValueError):
    """Refused wiki input. The message is safe to show the user."""


def _repo(cur, name: str) -> int:
    row = cur.execute("select id from ccctx_repos where name = :n", n=name).fetchone()
    if row is None:
        raise WikiError(f"no repository named '{name}'")
    return row[0]


@dataclass(frozen=True)
class _Stored:
    id: int
    name: str
    text: str
    state: str
    reason: str | None


def _lob(value):
    return value.read() if hasattr(value, "read") else value


def ensure_index(cur) -> bool:
    """Create the page index when the model is loaded and the index is missing. Whether the index exists now.

    DDL commits, so call it before writing anything that must stay one transaction.
    """
    if cur.execute("select count(*) from user_indexes where index_name = :i", i=INDEX).fetchone()[0]:
        return True
    if not model._state(cur)[0]:
        return False
    model._ensure_lexer(cur)
    try:  # same model, lexer and sync as the symbol index, so similarities compare across both (research R8)
        cur.execute(
            f"create hybrid vector index {INDEX} on ccctx_wiki_pages (search_text) parameters ('MODEL"
            f" {model.MODEL} VECTOR_IDXTYPE HNSW SYNC (ON COMMIT) LEXER {model.LEXER}')"
        )
    except oracledb.DatabaseError as e:
        if getattr(e.args[0], "full_code", "") != "ORA-00955":
            raise model.ModelError(f"could not build the page index: {db.describe(e)}") from None
    return True


# --- writing -------------------------------------------------------------------------------------------------


def _stored(cur, repo_id: int) -> dict[str, _Stored]:
    cur.execute("select directory, id, name, text, state, stale_reason from ccctx_wiki_pages where repo_id = :r",
                r=repo_id)
    return {d: _Stored(i, n, _lob(t), s, w) for d, i, n, t, s, w in cur.fetchall()}


def _write_page(cur, repo_id: int, draft: compile._Draft, old: _Stored | None) -> bool:
    """Store one page as fresh, compiled now, and replace its citations. Whether its text changed.

    An unchanged text is not rewritten, so the page index does not embed it again (research R11).
    """
    search_text = f"page {draft.name} in {draft.directory}\n{draft.text}"
    fields = {"n": draft.name, "l": draft.language, "c": draft.symbols, "p": compile.COMPILER}
    if old is None:
        page = cur.var(int)
        cur.setinputsizes(t=oracledb.DB_TYPE_CLOB, s=oracledb.DB_TYPE_CLOB)
        cur.execute("insert into ccctx_wiki_pages (repo_id, directory, name, language, symbols, state, compiled_at,"
                    " compiler, text, search_text) values (:r, :d, :n, :l, :c, 'fresh', systimestamp, :p, :t, :s)"
                    " returning id into :i", fields | {"r": repo_id, "d": draft.directory, "t": draft.text,
                                                       "s": search_text, "i": page})
        page_id = page.getvalue()[0]
    else:
        page_id = old.id
        cur.execute("update ccctx_wiki_pages set name = :n, language = :l, symbols = :c, state = 'fresh',"
                    " compiled_at = systimestamp, compiler = :p where id = :i", fields | {"i": page_id})
        if old.text != draft.text:
            cur.setinputsizes(t=oracledb.DB_TYPE_CLOB, s=oracledb.DB_TYPE_CLOB)
            cur.execute("update ccctx_wiki_pages set text = :t, search_text = :s where id = :i",
                        t=draft.text, s=search_text, i=page_id)
        cur.execute("delete from ccctx_wiki_citations where page_id = :i", i=page_id)
    seen, rows = set(), []
    for c in draft.citations:  # at most one row per (page, role, record)
        if (c["role"], c["s"], c["f"]) not in seen:
            seen.add((c["role"], c["s"], c["f"]))
            rows.append(c | {"page": page_id})
    cur.executemany("insert into ccctx_wiki_citations (page_id, symbol_id, file_id, role, name, kind, commit_sha,"
                    " content_hash) values (:page, :s, :f, :role, :name, :kind, :sha, :hash)", rows)
    return old is None or old.text != draft.text


def _apply(cur, repo_id: int, drafts: dict[str, compile._Draft], old: dict[str, _Stored],
           write) -> tuple[int, int, int]:
    """Delete the pages that no longer qualify, then write the existing pages `write` picks, then the new ones.

    Returns (added, rewritten, removed). Existing pages go first, so a page renamed by a clash frees its name.
    """
    gone = [{"i": o.id} for d, o in old.items() if d not in drafts]
    if gone:
        cur.executemany("delete from ccctx_wiki_pages where id = :i", gone)
    rewritten = 0
    for d in sorted(drafts.keys() & old.keys()):
        if write(drafts[d], old[d]):
            _write_page(cur, repo_id, drafts[d], old[d])
            rewritten += 1
    added = sorted(drafts.keys() - old.keys())
    for d in added:
        _write_page(cur, repo_id, drafts[d], None)
    return len(added), rewritten, len(gone)
