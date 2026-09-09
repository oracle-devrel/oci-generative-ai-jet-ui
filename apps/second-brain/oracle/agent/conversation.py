"""Conversational / working memory — the running dialogue of a session.

Best practice: persist the FULL history (durable, resumable), but load only a bounded
RECENT WINDOW into the model's context (working memory). This is what lets the agent handle
follow-ups like "which of those would be the best one?".
"""
import uuid


def new_session():
    return "sess-" + uuid.uuid4().hex[:10]


def record_turn(conn, session_id, role, content):
    """Persist one dialogue turn. Structural privacy: a turn whose text trips the deterministic
    deny-list (deal/fee/contract terms) is tagged visibility='business' so it never re-enters the
    working-memory window or the Memory view. Same contract as posts.visibility."""
    from oamp_memory import violates_privacy   # deterministic deny-list; lazy import keeps this cheap
    visibility = "business" if violates_privacy(content) else "content"
    with conn.cursor() as cur:
        cur.execute("SELECT NVL(MAX(seq), 0) + 1 FROM conversations WHERE session_id = :s",
                    s=session_id)
        seq = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO conversations (session_id, seq, role, content, visibility) "
            "VALUES (:s, :q, :r, :c, :v)",
            s=session_id, q=seq, r=role, c=content, v=visibility,
        )
    conn.commit()


def recent_turns(conn, session_id, n=12):
    """The last n turns of the session, in chronological order (the working-memory window).
    Content-scope only: business-tagged turns never re-enter the model's context."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT role, content FROM (
              SELECT role, content, seq FROM conversations
              WHERE session_id = :s AND NVL(visibility,'content') = 'content'
              ORDER BY seq DESC FETCH FIRST :n ROWS ONLY
            ) ORDER BY seq
            """,
            s=session_id, n=n,
        )
        return [{"role": role, "content": content} for role, content in cur.fetchall()]


def list_recent_turns(conn, k=20):
    """Recent dialogue turns across sessions (content-scope), newest first — for the Memory view."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT role, content, session_id,
                   TO_CHAR(created_at,'YYYY-MM-DD HH24:MI') AS created_at
            FROM   conversations
            WHERE  NVL(visibility,'content') = 'content'
            ORDER  BY created_at DESC, seq DESC
            FETCH  FIRST :k ROWS ONLY
            """,
            k=int(k),
        )
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
