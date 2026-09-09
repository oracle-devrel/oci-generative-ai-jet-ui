"""Semantic memory: consolidate EPISODIC memory (past research runs) into durable,
reusable FACTS, and recall them by meaning.

This is the DeepLearning.AI "memory-aware agents" move: an LLM pipeline that reads what
happened (episodic) and extracts consolidated knowledge (semantic) the agent can reuse
without re-deriving it. Facts are embedded in-DB and retrieved with vector search.
"""
import json

import llm

EMBED_MODEL = "MINILM"

_SYS = (
    "You maintain a durable, reusable set of FACTS about a creator's content library. You are given "
    "(a) the facts you already distilled last time, (b) a sample of their content, and (c) a log of "
    "recent research over it. UPDATE the fact set: KEEP the existing facts that still hold, REVISE "
    "any that are now more precise, ADD genuinely new ones from the recent runs, and DROP duplicates "
    "or anything contradicted. This is cumulative — do NOT discard prior knowledge just because it "
    "isn't in the recent runs. Return the FULL updated set (concise, standalone facts an assistant "
    "could reuse) — themes, recurring audience questions, formats, tools, notable gaps — deduplicated "
    "and capped at the ~40 most useful. Categories: theme | audience | format | tool | gap.\n"
    "PRIVACY GUARD: never record financial or private business facts — no earnings, rates, fees, "
    "pricing, invoices, payments, banking, budgets, taxes, contracts, or deal terms. Knowing a "
    "post is a brand collaboration (and its reach/engagement) is fine; the money and terms are not.\n"
    "EVIDENCE GUARD: every fact must be directly supported by the inputs you were given — the "
    "titles, the runs, or a prior fact that still holds. Never generalize beyond the evidence; "
    "when recent evidence contradicts a prior fact, revise toward the newer evidence; and when a "
    "run's answer marks a claim '(unverified)', do NOT promote it to a fact. A smaller, solid "
    "fact set beats a larger speculative one."
)

_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"facts": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {"fact": {"type": "string"}, "category": {"type": "string"}},
        "required": ["fact", "category"],
    }}},
    "required": ["facts"],
}


def consolidate(client, conn, limit=30, title_sample=80):
    """Cumulatively update semantic_memory from episodic memory + content. Feeds the EXISTING facts
    back in so prior knowledge is preserved (merge, not rolling-window rebuild), and samples titles
    instead of dumping the whole library so it scales to thousands of posts. Returns the facts."""
    cur = conn.cursor()
    # self-improving guard: consolidate ONLY from content, never from private/business items,
    # so financials can't be distilled into durable semantic memory.
    cur.execute("select count(*) from posts where nvl(visibility,'content') = 'content'")
    total = cur.fetchone()[0]
    # a representative SAMPLE (most recent), not every title — keeps the prompt bounded as the
    # library grows into the thousands.
    cur.execute("select title from posts where title is not null "
                "and nvl(visibility,'content') = 'content' "
                f"order by published_at desc nulls last fetch first {int(title_sample)} rows only")
    titles = [r[0] for r in cur.fetchall()]
    # the facts distilled last time — fed back so consolidation ACCUMULATES instead of forgetting.
    cur.execute("select category, fact from semantic_memory where source = 'consolidation' "
                "order by category")
    prior = cur.fetchall()
    cur.execute("select task, action, detail from agent_memory order by created_at desc "
                f"fetch first {int(limit)} rows only")
    runs = cur.fetchall()

    prompt = (
        "EXISTING FACTS (from last consolidation — keep/revise/dedupe these):\n" +
        ("\n".join(f"- [{c}] {f}" for c, f in prior) if prior else "(none yet)") +
        f"\n\nCONTENT LIBRARY — sample of {len(titles)} most-recent titles (of {total} total):\n" +
        "\n".join(f"- {t}" for t in titles) +
        "\n\nRECENT RESEARCH RUNS (question | answer-summary | notes):\n" +
        "\n".join(f"- {q} | {(a or '')[:160]} | {d or ''}" for q, a, d in runs) +
        "\n\nReturn the full updated fact set."
    )
    facts = llm.structured(_SYS, prompt, _SCHEMA, max_tokens=8192)["facts"]

    # rebuild the consolidation snapshot in ONE transaction; roll back on ANY failure
    # so a half-done rebuild can never leave a pending DELETE of all facts that a
    # later, unrelated commit() on this shared connection would silently finalize.
    try:
        cur.execute("delete from semantic_memory where source = 'consolidation'")
        for f in facts:
            fact = _clamp_bytes(f["fact"], 1000)          # fact VARCHAR2(1000) is BYTES
            cat = _clamp_bytes(f.get("category", ""), 60)   # category VARCHAR2(60)
            cur.execute(
                "insert into semantic_memory (fact, category, source, embedding) "
                "values (:f, :c, 'consolidation', vector_embedding(" + EMBED_MODEL + " using :f as data))",
                f=fact, c=cat,
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return facts


def _clamp_bytes(s, limit):
    """Truncate to a byte budget (VARCHAR2 byte semantics) without splitting a character."""
    b = (s or "").encode("utf-8")
    return s if len(b) <= limit else b[:limit].decode("utf-8", errors="ignore")


def list_facts(conn, k=200):
    """All consolidated facts (fact, category, when), grouped-friendly for the Memory view.
    Semantic memory is privacy-safe by construction: consolidate() distills ONLY from
    content-scope posts and drops financial/deal facts, so no visibility filter is needed here."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT fact, category, TO_CHAR(created_at,'YYYY-MM-DD') AS created_at "
            "FROM semantic_memory ORDER BY category, created_at DESC "
            "FETCH FIRST :k ROWS ONLY",
            k=int(k),
        )
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def semantic_recall(conn, query, k=5):
    """Return the k most relevant consolidated facts for `query`."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT fact, category,
                   VECTOR_DISTANCE(embedding,
                                   VECTOR_EMBEDDING({EMBED_MODEL} USING :q AS DATA),
                                   COSINE) AS dist
            FROM   semantic_memory
            ORDER  BY dist
            FETCH  FIRST {int(k)} ROWS ONLY
            """,
            q=query,
        )
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
