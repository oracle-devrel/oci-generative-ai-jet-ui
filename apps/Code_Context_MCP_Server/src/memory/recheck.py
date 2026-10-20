"""Agent memory re-check: after an ingest, mark facts stale whose subject changed, repoint or re-ask them."""

from golestan_code_mcp.graph import queries
from golestan_code_mcp.memory import distill, findings, runs
from golestan_code_mcp.memory.distill import _Fact
from golestan_code_mcp.search import query
from golestan_code_mcp.wiki import read


def _ask_again(conn, repo: str, tool: str, args: dict) -> list[dict]:
    """A finding's call run again through the core the tool uses, never the tool: no run is recorded (R8)."""
    try:
        if tool == "search_code":
            hits = query.search(conn, args["query"], [repo], language=args.get("language"),
                                limit=args.get("limit", query.LIMIT))
            rows = [vars(h) for h in hits if h.kind != "fact"]  # a fact must not confirm itself
        elif tool == "get_symbol":
            rows = [vars(d) for d in queries.definitions(conn, args["name"], [repo])[0]]
        elif tool == "find_callers":
            rows = [vars(r) for r in queries.callers(conn, args["name"], [repo])]
        elif tool == "find_callees":
            rows = [vars(r) for r in queries.calls(conn, args["name"], [repo])]
        elif tool == "impact_of":
            rows = [vars(r) for r in queries.impact(conn, args["name"], args.get("depth", 3), [repo])]
        else:  # read_wiki
            page = read.read(conn, args["page"], repo)
            rows = [{"kind": "page", "name": page.name, "repo": page.repo, "path": page.directory}]
    except ValueError:  # the name or page no longer exists
        rows = []
    return [{k: r[k] for k in runs.KEEP if r.get(k) is not None} | {"repo": repo} for r in rows]


def _stale(fact: _Fact, reason: str) -> None:
    fact.meta["state"], fact.meta["stale_reason"] = "stale", reason[:512]
    distill._contradict(fact)


def _rekey(facts: dict[str, _Fact], fact: _Fact, key: str) -> None:
    if key != fact.meta["subject_key"] and key not in facts:
        facts[key] = facts.pop(fact.meta["subject_key"])
        fact.meta["subject_key"] = key


def recheck(cur, mem, repo_id: int, repo: str, facts: dict[str, _Fact]) -> tuple[int, int]:
    """Check each fresh fact's subject against the current index (research R8). Returns (marked stale, re-asked).

    Same code at the same place: nothing. Same code moved: re-pointed. Changed code: every finding is asked again,
    and the fact stays fresh only if the same subject answers. No definition left: stale, a contradiction.
    """
    stale = reasked = 0
    for fact in [f for f in facts.values() if f.meta["state"] == "fresh"]:
        meta = fact.meta
        ref = meta["refs"][0]
        if ref["kind"] == "page":
            now = findings._page(cur, repo_id, ref["name"])
        else:
            now = findings._symbol(cur, repo_id, ref["name"], ref["kind"], ref["path"])
            if now and now["path"] != ref["path"] and now["content_hash"] != ref["content_hash"]:
                now = next((r for r in _definitions(cur, repo_id, ref) if r["content_hash"] == ref["content_hash"]),
                           now)  # the same code moved beats another definition of the name
        if now is None:
            _stale(fact, f"`{ref['name']}` was removed")
            stale += 1
            continue
        if now["content_hash"] == ref["content_hash"]:
            if now["path"] != ref["path"]:  # moved, unchanged: re-point only
                meta["refs"][0], meta["path"] = findings._ref(now, "subject"), now["path"]
                _rekey(facts, fact, findings._key(now))
                fact.changed = True
            continue
        reasked += 1
        answered = []
        for aspect, found in meta["findings"].items():
            run = {"id": found["run"], "tool": found["tool"], "arguments": found["arguments"], "status": "ok",
                   "question": next((found["arguments"][k] for k in runs.QUESTION if found["arguments"].get(k)), None),
                   "results": _ask_again(cur.connection, repo, found["tool"], found["arguments"])}
            answered.append((aspect, run, findings.finding(cur, repo_id, repo, run)))
        # only the fact's own subject confirms it: changed code somewhere else is other code (clarification Q1)
        wrong = next(((run, f) for _, run, f in answered if f is None or f.subject_key != meta["subject_key"]), None)
        if wrong:
            run, f = wrong
            other = f"now answered by `{f.subject}` in `{f.path}`" if f else "no longer answered"
            _stale(fact, f're-asked "{run["question"]}": {other}')
            stale += 1
            continue
        for aspect, _, f in answered:
            meta["findings"][aspect] = dict(f.value) | {k: meta["findings"][aspect][k]
                                                        for k in ("tool", "arguments", "run")}
            if aspect == "defined" and meta["findings"][aspect].get("definitions") is None:
                meta["findings"][aspect].pop("definitions", None)
        meta["refs"] = answered[0][2].refs + [r for _, _, f in answered[1:] for r in f.refs[1:]]
        meta["path"], meta["language"] = now["path"], now["language"]
        _rekey(facts, fact, findings._key(now))
        fact.changed = True
    return stale, reasked


def _definitions(cur, repo_id: int, ref: dict) -> list[dict]:
    """Every current definition with the reference's name and kind."""
    keys = ("name", "kind", "path", "language", "content_hash", "start_line", "end_line")
    cur.execute("""select s.name, s.kind, f.path, f.language, s.content_hash, s.start_line, s.end_line
                     from ccctx_symbols s join ccctx_files f on f.id = s.file_id
                    where f.repo_id = :r and s.name = :n and s.kind = :k""", r=repo_id, n=ref["name"], k=ref["kind"])
    return [dict(zip(keys, row)) for row in cur.fetchall()]
