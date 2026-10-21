from functools import partial

# Closest skills first (same idea as _TOOL_SQL): :q is the search text, :k how many rows to return.
_SKILL_SQL = ("SELECT name, category, description FROM skillbox ORDER BY VECTOR_DISTANCE(embedding, "
              f"VECTOR_EMBEDDING({ONNX_EMBED_MODEL} USING :q AS DATA), COSINE) FETCH FIRST :k ROWS ONLY")

@register
def tool_list_skills(query: str, k: int = 5) -> str:
    """Search the skillbox semantically. Returns top-k skills (name + description)."""
    with agent_conn.cursor() as cur:
        # TODO 7 (one line): run the skill search, like you did for tools in TODO 5. Write this line, filling in the two < >:
        #     cur.execute(_SKILL_SQL, q=<the question>, k=<how many>)
        #   <the question>  query   (the text to compare each skill against)
        #   <how many>      k       (how many skills to return)
        raise NotImplementedError("TODO 7: write the cur.execute(_SKILL_SQL, q=..., k=...) line")
        hits = [{"name": n, "category": c, "description": wt.lob_text(d)} for n, c, d in cur]   # one dict per skill
    return json.dumps(hits)   # JSON text of the list, best match first

build_skill_manifest = partial(wt.skill_manifest, agent_conn, ONNX_EMBED_MODEL)   # build_skill_manifest(query, k=3)
