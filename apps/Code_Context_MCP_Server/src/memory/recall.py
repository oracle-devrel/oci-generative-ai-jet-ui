"""Agent memory recall: list facts, recall them for a repository, forget them, and find them for a search."""

from dataclasses import dataclass

from golestan_code_mcp import registry
from golestan_code_mcp.memory import findings, store
from golestan_code_mcp.memory import runs as memory_runs
from golestan_code_mcp.memory.runs import RunView
from golestan_code_mcp.search import candidates, ranking
from golestan_code_mcp.search import model as search_model


@dataclass(frozen=True)
class FactView:
    id: str
    repo: str
    subject: str
    kind: str
    text: str
    confidence: float
    state: str
    stale_reason: str | None
    distiller: str
    consolidator: str
    runs: list[int]
    questions: list[str]
    sources: list[dict]
    language: str
    updated_at: str


def _sources(cur, repo_id: int, repo: str, refs: list[dict]) -> list[dict]:
    out = []
    for ref in refs:
        rec = (findings._page(cur, repo_id, ref["name"]) if ref["kind"] == "page"
               else findings._symbol(cur, repo_id, ref["name"], ref["kind"], ref["path"]))
        out.append({"role": ref["role"], "name": ref["name"], "kind": ref["kind"], "repo": repo,
                    "path": rec["path"] if rec else None, "start_line": rec["start_line"] if rec else None,
                    "end_line": rec["end_line"] if rec else None})
    return out


def _records(conn, mem, repo: str | None) -> list:
    """The fact records of a repository, or of every registered one."""
    with conn.cursor() as cur:
        known = {n for (n,) in cur.execute("select name from ccctx_repos")}
    scope = {"user_id": repo} if repo else {}
    return [r for r in mem.list_memories(agent_id=store.AGENT, limit=None, **scope)
            if r.record_type == "fact" and r.metadata and "subject_key" in r.metadata and r.user_id in known]


def _ordered(records: list) -> list:
    """Fresh first, then by confidence, then the most recently updated."""
    records = sorted(records, key=lambda r: r.metadata["updated_at"], reverse=True)
    return sorted(records, key=lambda r: (r.metadata["state"] != "fresh", -r.metadata["confidence"]))


def _views(conn, records) -> list[FactView]:
    """The records as views, each source located where it is now. Only call it on what will be returned."""
    with conn.cursor() as cur:
        ids = dict(cur.execute("select name, id from ccctx_repos").fetchall())
        return [FactView(r.id, r.user_id, m["subject"], m["kind"], r.content or "", m["confidence"], m["state"],
                         m.get("stale_reason"), m["distiller"], m["consolidator"], m["runs"], m["questions"],
                         _sources(cur, ids[r.user_id], r.user_id, m["refs"]), m.get("language", ""), m["updated_at"])
                for r in records for m in [findings._plain(r.metadata)]]


def facts(conn, repo: str | None = None, limit: int = 20) -> list[FactView]:
    """Facts, fresh first, then by confidence, then the most recently updated."""
    if repo is not None:
        registry.repo_id(conn, repo)
    return _views(conn, _ordered(_records(conn, store.client(conn), repo))[:limit])


@dataclass(frozen=True)
class Recall:
    facts: list[FactView]
    runs: list[RunView]
    total: int


RECALL_RUNS = 10


def recall(conn, repo: str | None = None, topic: str | None = None, limit: int = 20) -> Recall:
    """What earlier sessions worked out (research R10): facts, by topic when one is given, and the newest runs."""
    if repo is not None:
        registry.repo_id(conn, repo)
    mem = store.client(conn)
    records = _records(conn, mem, repo)
    if topic:
        by_id = {r.id: r for r in records}
        ranks: dict[str, int] = {}
        for name in ([repo] if repo else sorted({r.user_id for r in records})):
            hits = mem.search(topic, user_id=name, agent_id=store.AGENT, record_types=["fact"],
                              include_invalid_results=True, max_results=limit)
            for i, hit in enumerate(h for h in hits if h.id in by_id):  # repositories interleave rank by rank
                ranks.setdefault(hit.id, i)
        ranked = sorted((by_id[i] for i in ranks), key=lambda r: ranks[r.id])
        rest = [r for r in _ordered(records) if r.id not in ranks]
        chosen = sorted(ranked + rest, key=lambda r: r.metadata["state"] != "fresh")  # stable: fresh first
    else:
        chosen = _ordered(records)
    return Recall(_views(conn, chosen[:limit]), memory_runs.runs(conn, repo, RECALL_RUNS, skip_tool="recall"),
                  len(records))


def forget(conn, repo: str) -> None:
    """Remove a repository's facts. A future `repo remove` must call this (FR-018)."""
    mem = store.client(conn)
    mem.delete_user(repo, cascade=True)
    for r in mem.list_memories(user_id=repo, limit=None):
        mem.delete_memory(r.id)


# --- facts in search (research R14, FR-021) ---

FACT_CANDIDATES = 5
SIMILARITY_SQL = (f"select 1 - vector_distance(vector_embedding({search_model.MODEL} using :q as data),"
                  f" vector_embedding({search_model.MODEL} using :t as data), cosine) from dual")


def search_facts(conn, question: str, repos: list[str] | None = None, language: str | None = None,
                 k: int = FACT_CANDIDATES) -> list[dict]:
    """Fresh facts matching the question, each with its similarity to it, its subject's location and its text.

    Repositories with nothing consolidated are skipped without touching the memory package.
    """
    with conn.cursor() as cur:
        names = [n for (n,) in cur.execute("""select distinct r.name from ccctx_memory_run_repos l
                                                 join ccctx_repos r on r.id = l.repo_id where l.consolidated""")]
    names = sorted(n for n in names if repos is None or n in repos)
    if not names:
        return []
    mem = store.client(conn)
    records = []
    for name in names:
        for hit in mem.search(question, user_id=name, agent_id=store.AGENT, record_types=["fact"],
                              include_invalid_results=False, max_results=k):
            r, m = hit.record, hit.record.metadata or {}
            if r.record_type == "fact" and m.get("state") == "fresh" and language in (None, m.get("language")):
                records.append(r)
    hits = []
    with conn.cursor() as cur:
        for view in _views(conn, records):
            similarity = cur.execute(SIMILARITY_SQL, q=question, t=view.text).fetchone()[0]
            subject = view.sources[0]
            if similarity < ranking.FLOOR or subject["path"] is None:
                continue  # a weak match is worse than none, like a meaning-only symbol hit
            hits.append({"similarity": float(similarity), "repo": view.repo, "name": view.subject,
                         "path": subject["path"], "start_line": subject["start_line"],
                         "end_line": subject["end_line"], "language": view.language,
                         "snippet": view.text[:candidates.SNIPPET_CHARS]})
    return sorted(hits, key=lambda h: -h["similarity"])
