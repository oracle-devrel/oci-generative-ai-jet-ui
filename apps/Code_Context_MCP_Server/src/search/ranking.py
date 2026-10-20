"""Code search, ranking: fuse keyword and semantic scores, apply the usage boost, and place wiki pages.

Wiki pages have their own hybrid index (wiki.store.INDEX), searched with the same request and placed among the
symbols by semantic similarity.
"""

import re
from collections.abc import Mapping

from golestan_code_mcp.config import feedback_cap, feedback_half_life
from golestan_code_mcp.search import feedback

FLOOR = 0.3


def _boosts(conn, rows: dict[str, tuple], env: Mapping[str, str]) -> dict[str, float]:
    """rowid -> boost for the candidates with uses, by identity (repo id, path, name). Empty with a cap of 0."""
    cap = feedback_cap(env)
    if not cap or not rows:
        return {}
    with conn.cursor() as cur:
        weights = feedback.weights(cur, {r[0] for r in rows.values()}, feedback_half_life(env))
    return {rowid: feedback.boost(weights[key][1], cap) for rowid, r in rows.items()
            if (key := (r[0], r[4], r[3])) in weights}


def _boost(entries: list[dict], boosts: dict[str, float]) -> None:
    """Raise each entry's score by its boost, and a page's similarity for placing it (at most 1)."""
    for f in entries:
        b = boosts.get(f["rowid"], 0.0)
        if b:
            f["feedback"], f["score"] = b, f["relevance"] * (1 + b)
            if f["similarity"] is not None:
                f["placed"] = min(1.0, f["similarity"] * (1 + b))


def _fuse(hits: list[dict], rows: dict[str, tuple], in_scope) -> list[dict]:
    """One entry per row (its best chunk), in fused order, inside the scope, ranked among the rows kept.

    Fallback windows of one file overlap and look alike (a lockfile has dozens), so only a file's best window is kept.
    """
    fused, seen = [], set()
    for h in hits:
        rowid = h["rowid"]
        if rowid in seen or rowid not in rows or not in_scope(rows[rowid]):
            continue
        seen.add(rowid)
        rid, _, kind, _, path, *_ = rows[rowid]
        if kind == "chunk":
            if (rid, path) in seen:
                continue
            seen.add((rid, path))
        # vector_score is the index's cosine similarity mapped to 0-100: (1 + cosine) / 2 * 100
        similarity = h["vector_score"] / 50 - 1 if h.get("vector_score") else None
        keyword_hit = bool(h.get("text_score"))
        if not keyword_hit and (similarity is None or similarity < FLOOR):
            continue  # a weak meaning-only match is worse than none; keyword matches always count
        fused.append({"rowid": rowid, "score": float(h["score"]), "relevance": float(h["score"]), "feedback": 0.0,
                      "similarity": similarity,
                      "text": h["text_rank"] if h.get("text_score") else None,
                      "vector": h["vector_rank"] if h.get("vector_score") else None})
    for side in ("text", "vector"):  # ranks among the rows searched, not across the whole index
        for n, f in enumerate(sorted((f for f in fused if f[side]), key=lambda f: f[side]), 1):
            f[side] = n
    return fused


MODULE_WORDS = r"(?:module|package|directory)"


def names_module(question: str, page: str) -> bool:
    """Whether the question names the page's module as one: `the json module`, `package binding`.

    Similarity alone ranked a docs chunk about JSON above the flask/json page (research R8's fallback). A bare
    mention is not enough: every question about Flask would put the root `flask` page first.
    """
    word = re.escape(page.rpartition("/")[2])
    return bool(re.search(rf"\b{word}\s+{MODULE_WORDS}\b|\b{MODULE_WORDS}\s+{word}\b", question, re.IGNORECASE))


def _place(hits: list[dict], pages: list[dict]) -> list[dict]:
    """Each page above the first hit whose semantic similarity is lower; a page without one goes last.

    The two indexes' fused scores do not compare, but their similarities come from one model (research R8).
    """
    placed = list(hits)
    for page in pages:
        similarity = page.get("placed", page["similarity"])  # a used page's similarity, boosted (011 R5)
        if similarity is None:
            placed.append(page)
            continue
        at = next((i for i, h in enumerate(placed)
                   if h["similarity"] is None or h["similarity"] < similarity), len(placed))
        placed.insert(at, page)
    return placed
