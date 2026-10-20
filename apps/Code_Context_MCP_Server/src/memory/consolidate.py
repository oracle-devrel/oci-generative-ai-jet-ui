"""Agent memory consolidation: turn a repository's pending runs into facts, merging, weakening or replacing them.

A repository has one fact per subject (specs/010-agent-memory, research R6, R7).
"""

import json
import logging
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

import oracledb

from golestan_code_mcp import db, registry
from golestan_code_mcp.config import load
from golestan_code_mcp.memory import distill, findings, store
from golestan_code_mcp.memory import recheck as memory_recheck
from golestan_code_mcp.memory.distill import _Fact
from golestan_code_mcp.memory.findings import Finding
from golestan_code_mcp.memory.store import MemoryStoreError

log = logging.getLogger("golestan_code_mcp.memory")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(question: str) -> str:
    return re.sub(r"\s+", " ", question.lower()).strip().rstrip("?.! ")


def confidence(agree: int, contradict: int) -> float:
    return round((1 - 0.5 ** agree) * 0.5 ** contradict, 3)


def _same(aspect: str, old: dict, new: dict) -> bool:
    """Whether a newer finding for an aspect says what the fact already holds."""
    if aspect == "defined":
        return old.get("path") == new.get("path")
    if aspect == "module" or (aspect == "impact" and old.get("depth") != new.get("depth")):
        return True
    return (old.get("count"), old.get("names")) == (new.get("count"), new.get("names"))


@dataclass
class Consolidation:
    repo: str
    runs: int = 0
    created: int = 0
    merged: int = 0
    weakened: int = 0
    stale: int = 0
    reasked: int = 0
    distillers: dict = field(default_factory=dict)
    seconds: float = 0.0


def _new_meta(f: Finding) -> dict:
    now = _now()
    return {"subject_key": f.subject_key, "subject": f.subject, "kind": f.kind, "path": f.path,
            "language": f.language, "findings": {}, "questions": [], "runs": [], "refs": f.refs, "agree": 0,
            "contradict": 0, "confidence": 0.0, "state": "fresh", "stale_reason": None, "distiller": distill.TEMPLATE,
            "consolidator": distill.CONSOLIDATOR, "created_at": now, "updated_at": now}


def _merge(facts: dict[str, _Fact], f: Finding, links: list[tuple[str, str]], c: Consolidation) -> None:
    fact = facts.get(f.subject_key)
    if fact is not None and f.run_id in fact.meta["runs"]:
        return  # counted before a crash between writing facts and flagging links (research R9)
    if fact is None:
        fact = facts[f.subject_key] = _Fact(None, _new_meta(f))
        c.created += 1
    else:
        c.merged += 1
    meta = fact.meta
    old = meta["findings"].get(f.aspect)
    value = dict(f.value)
    if f.aspect == "defined" and old and value.get("definitions") is None and old.get("definitions"):
        value["definitions"] = old["definitions"]
    if old is not None and not _same(f.aspect, old, value):
        distill._contradict(fact)
    meta["findings"][f.aspect] = value | {"tool": f.tool, "arguments": f.arguments, "run": f.run_id}
    if f.question:
        # the same call answered by other code is a contradiction; the same words to another tool are not
        # (get_symbol and find_callers resolve a bare name to different definitions, both correctly)
        asked = [f.tool, _norm(f.question)]
        for other in facts.values():
            if other is not fact and asked in other.meta.setdefault("asked", []):
                other.meta["asked"].remove(asked)
                if not any(a[1] == asked[1] for a in other.meta["asked"]):
                    other.meta["questions"] = [q for q in other.meta["questions"] if _norm(q) != asked[1]]
                distill._contradict(other)
                links.append((meta["subject_key"], other.meta["subject_key"]))
        meta["asked"] = ([asked] + [a for a in meta.setdefault("asked", []) if a != asked])[:20]
        kept = [q for q in meta["questions"] if _norm(q) != asked[1]]
        meta["questions"] = ([f.question] + kept)[:20]
    meta["runs"].append(f.run_id)
    meta["agree"] += 1
    refs = {(r["role"], r["kind"], r["name"]): r for r in meta["refs"]}
    refs.update({(r["role"], r["kind"], r["name"]): r for r in f.refs})
    meta["refs"] = [r for r in refs.values() if r["role"] == "subject"] + [
        r for r in refs.values() if r["role"] == "related"]
    meta["path"], meta["language"] = f.path, f.language
    if meta["state"] == "stale":  # a new run confirms it (FR-015)
        meta["state"] = "fresh"
    fact.changed = True


def _load(mem, repo: str) -> dict[str, _Fact]:
    records = mem.list_memories(user_id=repo, agent_id=store.AGENT, limit=None)
    return {r.metadata["subject_key"]: _Fact(r.id, findings._plain(dict(r.metadata)), r.content or "")
            for r in records if r.record_type == "fact" and r.metadata and "subject_key" in r.metadata}


def _status(meta: dict):
    from oracleagentmemory.apis.records import RecordStatus

    return RecordStatus.VALID if meta["state"] == "fresh" else RecordStatus.INVALID


def _write(cur, mem, repo_id: int, repo: str, facts: dict[str, _Fact], llm, c: Consolidation) -> None:
    for fact in facts.values():
        if not fact.changed:
            continue
        meta = fact.meta
        meta["confidence"] = confidence(meta["agree"], meta["contradict"])
        meta["updated_at"], meta["consolidator"] = _now(), distill.CONSOLIDATOR
        fact.text, meta["distiller"] = distill._distill(cur, repo_id, repo, meta, llm)
        c.distillers[meta["distiller"]] = c.distillers.get(meta["distiller"], 0) + 1
        if fact.id is None:
            fact.id = mem.add_memory(fact.text, memory_type="fact", user_id=repo, agent_id=store.AGENT, metadata=meta,
                                     ttl_days=None, status=_status(meta), autonomous_linking=False)
        else:
            mem.update_memory(fact.id, content=fact.text, metadata=meta, status=_status(meta))
        c.weakened += fact.weakened


def _lock(repo_id: int, repo: str):
    """Hold the repository row on a second connection: the package commits the main one (research R9)."""
    lock = db.connect(load())
    try:
        lock.cursor().execute("select id from ccctx_repos where id = :r for update wait 60", r=repo_id)
    except oracledb.DatabaseError as e:
        lock.close()
        if getattr(e.args[0], "full_code", "") == "ORA-30006":
            raise MemoryStoreError(f"another consolidation of {repo} is running") from None
        raise
    return lock


def _consolidate(conn, mem, repo: str, llm) -> Consolidation:
    started, repo_id = time.monotonic(), registry.repo_id(conn, repo)
    c = Consolidation(repo)
    lock = _lock(repo_id, repo)
    try:
        facts = _load(mem, repo)
        with conn.cursor() as cur:
            c.stale, c.reasked = memory_recheck.recheck(cur, mem, repo_id, repo, facts)
            runs_ = findings.pending(cur, repo_id)
            links: list[tuple[str, str]] = []
            for run in runs_:
                if (f := findings.finding(cur, repo_id, repo, run)) is not None:
                    _merge(facts, f, links, c)
            c.runs = len(runs_)
            _write(cur, mem, repo_id, repo, facts, llm, c)
            for new, old in dict.fromkeys(links):
                try:
                    mem.link_records(facts[new].id, "fact", facts[old].id, "fact", "contradicts")
                except (KeyError, ValueError, RuntimeError):  # already linked, in either orientation
                    pass
            cur.executemany("update ccctx_memory_run_repos set consolidated = true where run_id = :r and repo_id = :p",
                            [{"r": run["id"], "p": repo_id} for run in runs_])
            cur.execute("""delete from ccctx_memory_runs r where r.scoped
                             and not exists (select 1 from ccctx_memory_run_repos l where l.run_id = r.id)""")
        conn.commit()
    finally:
        lock.rollback()
        lock.close()
    c.seconds = round(time.monotonic() - started, 1)
    log.info(json.dumps({"event": "consolidate", "repo": repo, "runs": c.runs, "created": c.created,
                         "merged": c.merged, "weakened": c.weakened, "stale": c.stale, "reasked": c.reasked,
                         "distillers": c.distillers, "seconds": c.seconds}))
    return c


def consolidate(conn, repo: str | None = None, env: Mapping[str, str] | None = None) -> list[Consolidation]:
    """Distil the runs not yet consolidated into facts, for one repository or every one with runs or facts."""
    if repo is not None:
        registry.repo_id(conn, repo)
    mem, llm = store.client(conn), store.model(env)
    if repo is None:
        with conn.cursor() as cur:
            names = {n for (n,) in cur.execute("select distinct r.name from ccctx_memory_run_repos l"
                                               " join ccctx_repos r on r.id = l.repo_id")}
            known = {n for (n,) in cur.execute("select name from ccctx_repos")}
        names |= {r.user_id for r in mem.list_memories(agent_id=store.AGENT, limit=None)} & known
    return [_consolidate(conn, mem, name, llm) for name in ([repo] if repo else sorted(names))]
