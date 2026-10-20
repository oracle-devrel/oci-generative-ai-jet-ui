"""Agent memory runs: record every MCP tool call in ccctx_memory_runs, off the answering path, and list them.

The runs are memory's episodic log.
"""

import atexit
import json
import logging
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime

import oracledb

from golestan_code_mcp import db, registry
from golestan_code_mcp.config import load
from golestan_code_mcp.memory import findings
from golestan_code_mcp.search import feedback as search_feedback

log = logging.getLogger("golestan_code_mcp.memory")

# What a run keeps of each result: its identity and location, never its text (FR-002, research R3).
KEEP = ("kind", "repo", "name", "path", "start_line", "end_line", "line", "score", "similarity", "callee", "caller",
        "hops", "state")
QUESTION = ("query", "name", "page", "topic")


def _rows(data: dict) -> list[dict]:
    if data.get("page"):
        p = data["page"]
        return [{"kind": "page", "name": p["name"], "repo": p["repo"], "path": p["directory"]}]
    if "pages" in data and "results" not in data:
        return [{"kind": "page", "name": p["name"], "repo": p["repo"], "state": p["state"]} for p in data["pages"]]
    if "repositories" in data:
        return [{"kind": "repository", "name": r["name"]} for r in data["repositories"]]
    if "facts" in data:
        return [{"kind": "fact", "repo": f["repo"], "name": f["subject"]} for f in data["facts"]]
    return [{k: row[k] for k in KEEP if row.get(k) is not None} for row in data.get("results", [])]


def run_of(tool: str, arguments: dict, result, client: str | None, ms: int) -> dict:
    """One run from a tool call: what was asked, by whom, and the identities and locations of what came back."""
    data = None if result is None else result.model_dump()
    if data is None:
        status, reason, rows = "error", None, []
    else:
        status = data.get("status") or ("ok" if data.get("database") == "reachable" else "unavailable")
        reason, rows = data.get("reason"), _rows(data)
    question = next((arguments[k] for k in QUESTION if arguments.get(k) is not None), None)
    repos = [arguments["repo"]] if arguments.get("repo") else sorted({r["repo"] for r in rows if r.get("repo")})
    return {"tool": tool, "arguments": arguments, "question": None if question is None else str(question)[:1000],
            "client": client, "status": status, "reason": reason and reason[:1000], "ms": ms,
            "result_count": len(rows), "results": rows, "repos": repos}


def store_use(conn, use: dict) -> None:
    """Write one use (011): its repository by name, its run by the id the writer gave it, if it was written."""
    with conn.cursor() as cur:
        search_feedback.write_use(cur, use | {"repo_id": registry.repo_id(conn, use["repo"]),
                                              "run_id": (use.get("run") or {}).get("id")})
    conn.commit()


def store_runs(conn, runs: list[dict]) -> None:
    """Insert runs and their repository links, in order, then commit. Unknown repositories are skipped."""
    with conn.cursor() as cur:
        ids = dict(cur.execute("select name, id from ccctx_repos").fetchall())  # a handful of rows
        for run in runs:
            run_id = cur.var(int)
            links = [ids[n] for n in run["repos"] if n in ids]
            cur.execute(
                "insert into ccctx_memory_runs (tool, arguments, question, client, status, reason, ms, result_count,"
                " results, scoped) values (:t, json(:a), :q, :c, :s, :r, :ms, :n, json(:res), :sc)"
                " returning id into :i",
                t=run["tool"], a=json.dumps(run["arguments"], default=str), q=run["question"], c=run["client"],
                s=run["status"], r=run["reason"], ms=run["ms"], n=run["result_count"],
                res=json.dumps(run["results"], default=str), sc=bool(links), i=run_id)
            rid = run["id"] = run_id.getvalue()[0]  # a use queued after this run links to it (011 research R3)
            cur.executemany("insert into ccctx_memory_run_repos (run_id, repo_id) values (:r, :p)",
                            [{"r": rid, "p": p} for p in links])
    conn.commit()


# One writer thread with one connection keeps runs in call order and off the answering path (research R2). Uses
# (011) queue as {"use": ...} behind the run that returned their result, so the run already has its id.
_runs: queue.Queue = queue.Queue()
_writer: threading.Thread | None = None
_writer_lock = threading.Lock()
_STOP = object()


def record(run: dict) -> None:
    """Queue a run, or a use as {"use": use}, for the writer thread."""
    global _writer
    with _writer_lock:
        if _writer is None:
            _writer = threading.Thread(target=_write_runs, name="ccctx-memory-writer", daemon=True)
            _writer.start()
            atexit.register(_drain)
    _runs.put(run)


def _write_runs() -> None:
    conn = None
    while True:
        run = _runs.get()
        try:
            if run is _STOP:
                return
            if conn is None:
                conn = db.connect(load())
            if "use" in run:
                store_use(conn, run["use"])
            else:
                store_runs(conn, [run])
        except Exception as e:  # never reaches the client (FR-003); the run or use is dropped
            reason = (db.describe(e) if isinstance(e, oracledb.Error) else str(e))[:300]
            log.warning(json.dumps({"event": "feedback_record_failed", "reason": reason} if "use" in run else
                                   {"event": "memory_record_failed", "tool": run["tool"], "reason": reason}))
            if conn is not None:
                try:
                    conn.close()
                except Exception:  # noqa: BLE001 - a broken connection may fail to close too
                    pass
                conn = None
        finally:
            _runs.task_done()


def flush() -> None:
    """Wait until every recorded run has been written or dropped."""
    _runs.join()


def _drain() -> None:
    if _writer is not None and _writer.is_alive():
        _runs.put(_STOP)
        _writer.join(5)


@dataclass(frozen=True)
class RunView:
    id: int
    called_at: datetime
    tool: str
    question: str | None
    client: str | None
    status: str
    reason: str | None
    result_count: int
    top: dict | None
    used: list[str] = field(default_factory=list)  # names of results with a use linked to this run, in result order


def runs(conn, repo: str | None = None, limit: int = 20, skip_tool: str | None = None) -> list[RunView]:
    """The newest runs first, optionally only those belonging to a repository."""
    rid = registry.repo_id(conn, repo) if repo else None
    with conn.cursor() as cur:
        cur.execute(
            "select r.id, r.called_at, r.tool, r.question, r.client, r.status, r.reason, r.result_count,"
            " json_query(r.results, '$[0]' returning varchar2(4000) null on error)"
            " from ccctx_memory_runs r"
            " where (:rid is null or exists (select 1 from ccctx_memory_run_repos l"
            "                                 where l.run_id = r.id and l.repo_id = :rid))"
            "   and (:skip is null or r.tool <> :skip)"
            " order by r.id desc fetch first :lim rows only", rid=rid, skip=skip_tool, lim=limit)
        found = cur.fetchall()
        used: dict[int, set] = {}
        orders: dict[int, list] = {}
        if found:  # at most `limit` runs, so one IN list
            binds = ", ".join(f":{n + 1}" for n in range(len(found)))
            cur.execute(f"select run_id, path, name from ccctx_feedback where run_id in ({binds})",
                        [row[0] for row in found])
            for run_id, path, name in cur:
                used.setdefault(run_id, set()).add((path, name))
        if used:
            binds = ", ".join(f":{n + 1}" for n in range(len(used)))
            cur.execute(f"select id, results from ccctx_memory_runs where id in ({binds})", list(used))
            orders = {i: findings._json(res) or [] for i, res in cur}
    return [RunView(*row[:8], json.loads(row[8]) if row[8] else None,
                    [r["name"] for r in orders.get(row[0], []) if (r.get("path"), r.get("name")) in used[row[0]]])
            for row in found]
