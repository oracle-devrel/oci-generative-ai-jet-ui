"""Agent memory: write experiences + recall them by meaning.

The embedding is generated INSIDE Oracle via VECTOR_EMBEDDING(MINILM ...) — no
external embedding API. Relational columns make outcomes auditable with plain SQL.
"""

EMBED_MODEL = "MINILM"  # the in-DB ONNX model loaded by setup/01_load_onnx_model.sql


def record(conn, run_id, task, action, tool, outcome, reward=None, detail=None):
    """Write one episodic memory row, embedding the experience text in-DB.

    Values are clamped to their column sizes so a long question can never
    crash the save step after an expensive run (ORA-12899).

    Structural privacy: if the experience text trips the deterministic deny-list
    (deal/fee/contract terms), the row is written visibility='business' so it never
    surfaces in recall(), the Memory view, or the agent's own reasoning. Same contract
    as posts.visibility — private memory exists but is unreachable from any read path.
    """
    from oamp_memory import violates_privacy   # deterministic deny-list; lazy import keeps this cheap
    experience = f"{task} | {action} | {detail or ''}"
    visibility = "business" if violates_privacy(experience) else "content"
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO agent_memory
                  (run_id, task, action, tool, outcome, reward, detail, visibility, embedding)
            VALUES (:run_id, :task, :action, :tool, :outcome, :reward, :detail, :visibility,
                    VECTOR_EMBEDDING({EMBED_MODEL} USING :exp AS DATA))
            """,
            run_id=(run_id or "")[:40], task=(task or "")[:500],
            action=action, tool=tool[:80] if tool else None,
            outcome=(outcome or "")[:10], reward=reward, detail=detail,
            visibility=visibility, exp=experience,
        )
    conn.commit()


def recall(conn, query, k=5):
    """Return the k most semantically-relevant past experiences for `query`.
    Content-scope only: business-tagged memories never resurface (in the agent's
    reasoning or anywhere), same filter as the content layer."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT task, action, outcome, reward, detail,
                   VECTOR_DISTANCE(embedding,
                                   VECTOR_EMBEDDING({EMBED_MODEL} USING :q AS DATA),
                                   COSINE) AS dist
            FROM   agent_memory
            WHERE  NVL(visibility,'content') = 'content'
            ORDER  BY dist
            FETCH  FIRST {int(k)} ROWS ONLY
            """,
            q=query,
        )
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def list_recent(conn, k=20):
    """Recent episodic memories (content-scope), newest first — for the Memory view.
    Not a query-recall; a straight timeline of what the agent did and how it turned out."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT task, action, tool, outcome, reward,
                   TO_CHAR(created_at,'YYYY-MM-DD HH24:MI') AS created_at
            FROM   agent_memory
            WHERE  NVL(visibility,'content') = 'content'
            ORDER  BY created_at DESC
            FETCH  FIRST :k ROWS ONLY
            """,
            k=int(k),
        )
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _count(cur, sql):
    cur.execute(sql)
    return int(cur.fetchone()[0])


def memory_counts(conn):
    """Counts of each memory kind (content-scope) for the overview tiles. Episodic and
    conversational are visibility-filtered; semantic is already privacy-safe by construction
    (consolidated only from content); procedural holds tool definitions (no private data)."""
    with conn.cursor() as cur:
        return {
            "episodic": _count(cur, "SELECT COUNT(*) FROM agent_memory "
                                    "WHERE NVL(visibility,'content')='content'"),
            "semantic": _count(cur, "SELECT COUNT(*) FROM semantic_memory"),
            "conversational": _count(cur, "SELECT COUNT(*) FROM conversations "
                                          "WHERE NVL(visibility,'content')='content'"),
            "procedural": _count(cur, "SELECT COUNT(*) FROM procedural_memory"),
        }


def tool_stats(conn):
    """The auditable flex: the agent's track record per tool, plain SQL."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT tool, attempts, successes, success_rate "
            "FROM tool_stats ORDER BY success_rate DESC"
        )
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
