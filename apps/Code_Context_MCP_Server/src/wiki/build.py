"""Wiki builds: compile every page of a repository, mark pages stale after an ingest, and recompile them.

An ingestion marks a page stale when a cited symbol's commit changes or a cited record is gone, then
recompiles it (research R7). A directory gets a page when it holds at least THRESHOLD named definitions.
"""

import json
import logging
import time
from dataclasses import dataclass

import oracledb

from golestan_code_mcp import db
from golestan_code_mcp.wiki import compile, store
from golestan_code_mcp.wiki.store import WikiError

log = logging.getLogger("golestan_code_mcp.wiki")



@dataclass
class Refresh:
    stale: list[tuple[str, str]]  # (page, reason) of the pages that went stale
    recompiled: int = 0
    added: int = 0
    removed: int = 0
    error: str | None = None  # why the recompile failed; the pages then stay stale


@dataclass(frozen=True)
class Built:
    repo: str
    pages: int
    added: int
    updated: int  # existing pages whose text changed
    removed: int
    seconds: float


def _log(repo: str, started: float, built: int, stale: int, recompiled: int, removed: int) -> None:
    log.info(json.dumps({"event": "wiki", "repo": repo, "built": built, "stale": stale, "recompiled": recompiled,
                         "removed": removed, "ms": round((time.monotonic() - started) * 1000)}))


def _targets(cur, repo: str | None) -> list[tuple[int, str]]:
    """(id, name) of the repositories to build: the named one, or every indexed one, in name order."""
    if repo is not None:
        rid = store._repo(cur, repo)
        if not cur.execute("select count(*) from ccctx_files where repo_id = :r and rownum = 1", r=rid).fetchone()[0]:
            raise WikiError(f"repository '{repo}' is not indexed yet; run `ccctx ingest {repo}`")
        return [(rid, repo)]
    rows = cur.execute("select r.id, r.name from ccctx_repos r"
                       " where exists (select 1 from ccctx_files f where f.repo_id = r.id)").fetchall()
    if not rows:
        raise WikiError("no indexed repositories")
    return sorted(rows, key=lambda row: row[1])


def build(conn, repo: str | None = None) -> list[Built]:
    """Compile every qualifying directory of the repository, or of every indexed one. One transaction each."""
    with conn.cursor() as cur:
        targets = _targets(cur, repo)
        store.ensure_index(cur)
    return [_build(conn, rid, name) for rid, name in targets]


def _build(conn, repo_id: int, repo: str) -> Built:
    started = time.monotonic()
    with conn.cursor() as cur:
        try:
            cur.execute("select id from ccctx_repos where id = :r for update", r=repo_id)  # waits for an ingest
            drafts = compile._compile(cur, repo_id, repo)
            old = store._stored(cur, repo_id)
            updated = sum(old[d].text != drafts[d].text for d in drafts.keys() & old.keys())
            added, rewritten, removed = store._apply(cur, repo_id, drafts, old, lambda draft, stored: True)
            cur.execute("update ccctx_repos set wiki_at = nvl(wiki_at, systimestamp) where id = :r", r=repo_id)
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
    _log(repo, started, len(drafts), 0, rewritten, removed)
    return Built(repo, len(drafts), added, updated, removed, round(time.monotonic() - started, 1))


# --- staleness -----------------------------------------------------------------------------------------------


def enabled(cur, repo_id: int) -> bool:
    """Whether the repository has a wiki: `wiki build` ran for it once."""
    row = cur.execute("select wiki_at from ccctx_repos where id = :r", r=repo_id).fetchone()
    return bool(row and row[0])


def _rewritten(cur, repo_id: int, name: str) -> str | None:
    """The commit of the symbol now carrying a cited name whose record is gone, or None if no symbol has it."""
    row = cur.execute("""select min(s.commit_sha) from ccctx_symbols s join ccctx_files f on f.id = s.file_id
                          where f.repo_id = :r and s.name = :n and s.kind <> 'chunk'""", r=repo_id, n=name).fetchone()
    return row[0]


def mark_stale(cur, repo_id: int) -> list[tuple[str, str]]:
    """Mark stale every fresh page with a symbol citation whose symbol changed commit or is gone, or a file citation
    whose file is gone. Returns (page, reason) in page-name order. Runs inside the caller's transaction."""
    if not enabled(cur, repo_id):
        return []
    rows = cur.execute(
        """select p.id, p.name, c.role, c.name, c.commit_sha, s.commit_sha, c.symbol_id, c.file_id
             from ccctx_wiki_pages p join ccctx_wiki_citations c on c.page_id = p.id
             left join ccctx_symbols s on s.id = c.symbol_id
            where p.repo_id = :r and p.state = 'fresh'
              and ((c.role in ('key', 'calls') and (c.symbol_id is null or s.commit_sha <> c.commit_sha))
                   or (c.role in ('file', 'depends', 'uses') and c.file_id is null))""", r=repo_id).fetchall()
    first: dict[int, tuple[str, str]] = {}
    for pid, page, role, cited, recorded, current, sid, fid in sorted(
            rows, key=lambda r: (compile.ROLES.index(r[2]), r[3])):
        if pid not in first:
            if role in compile.SYMBOL_ROLES and sid is None:  # an edited symbol is deleted and inserted again
                current = _rewritten(cur, repo_id, cited)
            gone = (current if role in compile.SYMBOL_ROLES else fid) is None
            cited = cited[:400]  # stale_reason holds 512
            if gone:
                reason = f"{cited} is gone"
            elif current == recorded:  # a full re-ingestion rewrote it at the same commit
                reason = f"{cited} was re-indexed"
            else:
                reason = f"{cited} changed ({recorded[:12]} -> {current[:12]})"
            first[pid] = (page, reason)
    if first:
        cur.executemany("update ccctx_wiki_pages set state = 'stale', stale_reason = :w where id = :i",
                        [{"i": pid, "w": reason} for pid, (_, reason) in first.items()])
    return sorted(first.values())


def refresh(conn, repo_id: int) -> Refresh:
    """Recompile every stale page, add pages for directories that now qualify and remove the others, in a
    transaction of its own. Never raises: on failure it rolls back, the pages stay stale and `error` says why."""
    started, stale = time.monotonic(), []
    with conn.cursor() as cur:
        try:
            repo, wiki_at = cur.execute("select name, wiki_at from ccctx_repos where id = :r for update",
                                        r=repo_id).fetchone()
            if wiki_at is None:
                conn.rollback()
                return Refresh([])
            old = store._stored(cur, repo_id)
            stale = sorted((o.name, o.reason) for o in old.values() if o.state == "stale")
            drafts = compile._compile(cur, repo_id, repo)
            added, recompiled, removed = store._apply(
                cur, repo_id, drafts, old, lambda draft, page: page.state == "stale" or page.name != draft.name)
            conn.commit()
        except Exception as e:
            conn.rollback()
            return Refresh(stale, error=db.describe(e) if isinstance(e, oracledb.Error) else str(e))
    _log(repo, started, added + recompiled, len(stale), recompiled, removed)
    return Refresh(stale, recompiled, added, removed)
