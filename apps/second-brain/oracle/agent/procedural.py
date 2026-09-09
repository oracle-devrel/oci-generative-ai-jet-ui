"""Procedural memory — the agent's tools stored AS memory.

Instead of always loading every tool, we embed each tool's description and semantic-search
for the ones relevant to the query at inference time. With a few tools this just ranks them;
the point is the pattern — it scales when the toolset grows large.
"""
import json

EMBED_MODEL = "MINILM"


def seed_tools(conn, tools):
    """Register/refresh the agent's tools in procedural memory. `tools` = list of dicts with
    name, description, schema (dict|None), kind ('client'|'server')."""
    with conn.cursor() as cur:
        for t in tools:
            emb = f"{t['name']}: {t['description']}"[:2000]
            cur.execute(
                """
                MERGE INTO procedural_memory p USING (SELECT :name AS nm FROM dual) s
                ON (p.name = s.nm)
                WHEN MATCHED THEN UPDATE SET
                    description = :descr, schema_json = :sch, kind = :knd,
                    embedding = VECTOR_EMBEDDING(MINILM USING :emb AS DATA)
                WHEN NOT MATCHED THEN INSERT (name, description, schema_json, kind, embedding)
                    VALUES (:name, :descr, :sch, :knd,
                            VECTOR_EMBEDDING(MINILM USING :emb AS DATA))
                """,
                name=t["name"], descr=t["description"],
                sch=json.dumps(t["schema"]) if t.get("schema") else None,
                knd=t.get("kind", "client"), emb=emb,
            )
    conn.commit()


def list_tools(conn):
    """All registered tools (name, description, kind) — for the Memory view's procedural
    section. Tool definitions carry no private data, so no visibility filter applies."""
    with conn.cursor() as cur:
        cur.execute("SELECT name, description, kind FROM procedural_memory ORDER BY name")
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def select_tools(conn, query, k=3):
    """Return the k tools most relevant to `query`, ranked by meaning (with distance)."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT name, kind, dist FROM (
              SELECT name, kind,
                     VECTOR_DISTANCE(embedding,
                                     VECTOR_EMBEDDING({EMBED_MODEL} USING :q AS DATA), COSINE) AS dist
              FROM procedural_memory ORDER BY dist
            ) WHERE ROWNUM <= {int(k)}
            """,
            q=query,
        )
        return [{"name": n, "kind": kd, "dist": float(d)} for n, kd, d in cur.fetchall()]
