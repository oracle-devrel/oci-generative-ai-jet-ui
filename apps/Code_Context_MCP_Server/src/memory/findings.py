"""Agent memory findings: what one recorded run says about a symbol, a page or a question, keyed for merging
(specs/010-agent-memory, research R5).
"""

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal

from golestan_code_mcp.graph import queries
from golestan_code_mcp.wiki import read

NO_FACTS = {"list_repositories", "recall", "mark_used"}
NAMES = 5  # callers, callees or reached symbols named in a fact
SOURCE_LINES = 200  # of the subject's source sent to a configured model (research R13)


@dataclass
class Finding:
    subject_key: str
    subject: str
    kind: str  # the subject's symbol kind, or "page"
    path: str  # the subject's file, or a page's directory
    language: str
    aspect: str  # defined, module, callers, callees or impact
    value: dict
    tool: str
    arguments: dict
    run_id: int
    question: str | None
    refs: list[dict]  # the subject first, then related symbols


def _plain(value):
    """JSON from the database as plain Python: Oracle returns numbers as Decimal, which json cannot write."""
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _json(value):
    return _plain(json.loads(value) if isinstance(value, str) else value)


def pending(cur, repo_id: int) -> list[dict]:
    """The repository's runs not yet consolidated, oldest first."""
    cur.execute("""select r.id, r.tool, r.arguments, r.question, r.status, r.results
                     from ccctx_memory_run_repos l join ccctx_memory_runs r on r.id = l.run_id
                    where l.repo_id = :r and not l.consolidated
                    order by r.id""", r=repo_id)
    return [{"id": i, "tool": t, "arguments": _json(a) or {}, "question": q, "status": s, "results": _json(res) or []}
            for i, t, a, q, s, res in cur.fetchall()]


def _symbol(cur, repo_id: int, name: str, kind: str | None = None, path: str | None = None) -> dict | None:
    """The current definition with this name (and kind), preferring the given path."""
    row = cur.execute(
        """select s.name, s.kind, f.path, f.language, s.content_hash, s.start_line, s.end_line
             from ccctx_symbols s join ccctx_files f on f.id = s.file_id
            where f.repo_id = :r and s.name = :n and (:k is null or s.kind = :k)
            order by case when f.path = :p then 0 else 1 end, f.path, s.start_line
            fetch first 1 rows only""", r=repo_id, n=name, k=kind, p=path).fetchone()
    if row is None:
        return None
    keys = ("name", "kind", "path", "language", "content_hash", "start_line", "end_line")
    return dict(zip(keys, row))


def _page(cur, repo_id: int, name: str) -> dict | None:
    row = cur.execute("select name, directory, language, text from ccctx_wiki_pages where repo_id = :r and name = :n",
                      r=repo_id, n=name).fetchone()
    if row is None:
        return None
    text = row[3].read() if hasattr(row[3], "read") else row[3]
    return {"name": row[0], "kind": "page", "path": row[1], "language": row[2], "text": text,
            "content_hash": hashlib.sha256(text.encode()).hexdigest(), "start_line": None, "end_line": None}


def _ref(record: dict, role: str) -> dict:
    return {"role": role, "kind": record["kind"], "name": record["name"], "path": record["path"],
            "content_hash": record["content_hash"]}


def _key(record: dict) -> str:
    if record["kind"] == "page":
        return f"page:{record['name']}"
    return f"symbol:{record['path']}:{record['name']}:{record['kind']}"


def _names(rows: list[dict]) -> list[str]:
    return list(dict.fromkeys(r["name"] for r in rows))[:NAMES]


def finding(cur, repo_id: int, repo: str, run: dict) -> Finding | None:
    """The one finding a run gives for a repository, about its first result's code, or None."""
    if run["status"] != "ok" or run["tool"] in NO_FACTS:
        return None
    rows = [r for r in run["results"] if r.get("repo") == repo]
    tool, args = run["tool"], run["arguments"]
    if not rows or (tool == "read_wiki" and not args.get("page")):
        return None
    top, related, value = rows[0], [], {}
    if tool == "read_wiki" or (tool == "search_code" and top["kind"] == "page"):
        subject, aspect = _page(cur, repo_id, top["name"]), "module"
        if subject:
            value = {"directory": subject["path"], "summary": read._summary(subject["text"])}
    elif tool in ("search_code", "get_symbol"):
        kind = None if top["kind"] == "fact" else top["kind"]  # a fact hit stands for its own subject (R14)
        subject, aspect = _symbol(cur, repo_id, top["name"], kind, top.get("path")), "defined"
        if subject:
            value = {"path": subject["path"]} | ({"definitions": len(rows)} if tool == "get_symbol" else {})
    elif tool in ("find_callers", "find_callees"):
        column = "callee" if tool == "find_callers" else "caller"
        mine = [r for r in rows if r.get(column) == top.get(column)]
        subject, aspect = _symbol(cur, repo_id, top.get(column)), tool.removeprefix("find_")
        value, related = {"count": len(mine), "names": _names(mine)}, mine
    elif tool == "impact_of":
        try:
            found, _ = queries.definitions(cur.connection, args.get("name", ""), [repo])
        except ValueError:
            found = []
        subject = _symbol(cur, repo_id, found[0].name, found[0].kind, found[0].path) if found else None
        aspect = "impact"
        value, related = {"count": len(rows), "depth": args.get("depth", 3), "names": _names(rows)}, rows
    else:
        return None
    if subject is None:
        return None
    refs = [_ref(subject, "subject")]
    for name in value.get("names", []):
        row = next(r for r in related if r["name"] == name)
        if (rec := _symbol(cur, repo_id, name, row.get("kind"), row.get("path"))) is not None:
            refs.append(_ref(rec, "related"))
    return Finding(_key(subject), subject["name"], subject["kind"], subject["path"], subject["language"], aspect,
                   value, tool, args, run["id"], run["question"], refs)
