"""Usage feedback (specs/011-usage-feedback): which results clients used, and the bounded, fading boost it earns.

A use is keyed by the result's identity (repository, path, name), so it survives a re-ingest. Its weight halves
every half-life, and the boost grows with the weight up to the cap, reached at SATURATION. Only ccctx_feedback
is touched.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from golestan_code_mcp import registry
from golestan_code_mcp.config import environment, feedback_cap, feedback_half_life

BASE = {"cited": 1.0, "opened": 0.5}
SATURATION = 5.0  # weight at which the boost reaches the cap: five fresh citations


def boost(weight: float, cap: float) -> float:
    """The fraction a result's score is raised by: grows with the weight until it reaches the cap."""
    return cap * min(1.0, weight / SATURATION)


def resolve(cur, repo_id: int, path: str, name: str) -> str | None:
    """The kind of the indexed symbol at (path, name), or 'page' for the wiki page of that directory and name."""
    row = cur.execute(
        """select s.kind from ccctx_symbols s join ccctx_files f on f.id = s.file_id
            where f.repo_id = :r and f.path = :p and s.name = :n fetch first 1 rows only""",
        r=repo_id, p=path, n=name).fetchone()
    if row:
        return row[0]
    row = cur.execute("select 1 from ccctx_wiki_pages where repo_id = :r and directory = :p and name = :n",
                      r=repo_id, p=path, n=name).fetchone()
    return "page" if row else None


def write_use(cur, use: dict) -> None:
    """Record one use, once per result per session: a cited use upgrades an opened one, nothing else changes.

    use: repo_id, path, name, kind, how, client, session, run_id and optionally days_ago (backdated, for the CLI).
    """
    cur.execute(
        """merge into ccctx_feedback f
           using (select :r repo_id, :p path, :n name, :s session_id from dual) u
              on (f.session_id = u.session_id and f.repo_id = u.repo_id and f.path = u.path and f.name = u.name)
            when matched then update set f.how = 'cited', f.used_at = systimestamp, f.run_id = nvl(:run, f.run_id)
                 where f.how = 'opened' and :h = 'cited'
            when not matched then insert (repo_id, path, name, kind, how, client, session_id, run_id, used_at)
                 values (:r, :p, :n, :k, :h, :c, :s, :run, systimestamp - numtodsinterval(:d, 'DAY'))""",
        r=use["repo_id"], p=use["path"], n=use["name"], k=use["kind"], h=use["how"], c=use["client"],
        s=use["session"], run=use["run_id"], d=use.get("days_ago", 0))


def weights(cur, repo_ids, half_life: float) -> dict[tuple[int, str, str], tuple[int, float, object]]:
    """(repo_id, path, name) -> (uses, weight, last used) for every result with uses in these repositories."""
    ids = sorted(set(repo_ids))
    if not ids:
        return {}
    binds = ", ".join(f":i{n}" for n in range(len(ids)))  # a handful of repositories
    cur.execute(
        f"""select repo_id, path, name, count(*),
                   sum(case how when 'cited' then :cited else :opened end
                       * power(0.5, (cast(systimestamp as date) - cast(used_at as date)) / :half)),
                   max(used_at)
              from ccctx_feedback where repo_id in ({binds}) group by repo_id, path, name""",
        {"cited": BASE["cited"], "opened": BASE["opened"], "half": half_life} | {f"i{n}": i for n, i in enumerate(ids)})
    return {(r, p, n): (uses, float(w), last) for r, p, n, uses, w, last in cur}


@dataclass(frozen=True)
class FeedbackRow:
    kind: str
    name: str
    path: str
    uses: int
    weight: float
    boost: float
    last_used: datetime
    indexed: bool  # False when the symbol or page is gone: such a use boosts nothing


def listing(conn, repo: str, env=None) -> list[FeedbackRow]:
    """Every result of the repository with uses, highest weight first."""
    env = environment() if env is None else env
    rid = registry.repo_id(conn, repo)
    cap = feedback_cap(env)
    with conn.cursor() as cur:
        found = weights(cur, [rid], feedback_half_life(env))
        cur.execute("select path, name, max(kind) from ccctx_feedback where repo_id = :r group by path, name", r=rid)
        recorded = {(p, n): k for p, n, k in cur}
        # ponytail: one lookup per listed result; the list is what an operator reads, a few dozen rows
        now = {(p, n): resolve(cur, rid, p, n) for _, p, n in found}
    rows = [FeedbackRow(now[(p, n)] or recorded[(p, n)], n, p, uses, w, boost(w, cap), last, now[(p, n)] is not None)
            for (_, p, n), (uses, w, last) in found.items()]
    return sorted(rows, key=lambda r: (-r.weight, r.path, r.name))


def add(conn, repo: str, name: str, path: str | None = None, days_ago: float = 0, count: int = 1) -> tuple[str, str]:
    """Record `count` cited uses, each its own `cli:` session, dated `days_ago` back. Returns (path, kind)."""
    if days_ago < 0:
        raise ValueError("days ago must not be negative")
    rid = registry.repo_id(conn, repo)
    with conn.cursor() as cur:
        if path is None:
            cur.execute("""select distinct f.path from ccctx_symbols s join ccctx_files f on f.id = s.file_id
                            where f.repo_id = :r and s.name = :n
                           union select directory from ccctx_wiki_pages where repo_id = :r and name = :n
                           order by 1""", r=rid, n=name)
            paths = [row[0] for row in cur]
            if len(paths) > 1:
                raise ValueError(f"'{name}' is at several paths; pass --path:\n" + "\n".join(paths))
            path = paths[0] if paths else None
        kind = None if path is None else resolve(cur, rid, path, name)
        if kind is None:
            where = "" if path is None else f" at '{path}'"
            raise ValueError(f"not found: no indexed symbol or page named '{name}'{where} in '{repo}'")
        # every use is its own session, so a plain insert is what write_use's MERGE would do, without 1 trip each
        cur.executemany(
            """insert into ccctx_feedback (repo_id, path, name, kind, how, client, session_id, used_at)
               values (:r, :p, :n, :k, 'cited', 'cli', :s, systimestamp - numtodsinterval(:d, 'DAY'))""",
            [{"r": rid, "p": path, "n": name, "k": kind, "s": f"cli:{uuid.uuid4()}", "d": days_ago}
             for _ in range(count)])
    conn.commit()
    return path, kind


def reset(conn, repo: str | None) -> int:
    """Delete one repository's uses, or every use with None. Returns how many."""
    rid = registry.repo_id(conn, repo) if repo else None
    with conn.cursor() as cur:
        cur.execute("delete from ccctx_feedback where :r is null or repo_id = :r", r=rid)
        deleted = cur.rowcount
    conn.commit()
    return deleted
