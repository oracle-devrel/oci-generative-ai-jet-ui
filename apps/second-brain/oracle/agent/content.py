"""Semantic search over YOUR content (posts), powered by in-DB embeddings.

This is the 'knowledge' the research agent reasons over — distinct from agent_memory
(its 'experience'). Both live in the same Oracle database.
"""

import re

EMBED_MODEL = "MINILM"


def search_content(conn, query, k=5):
    """Return the k most semantically relevant matches, by meaning — across THREE levels,
    ranked together by distance:
      - 'wiki'    : a compiled topic page (synthesized knowledge over your content)
      - 'item'    : a post overview
      - 'passage' : a specific chunk inside a long chat/transcript
    So a query can land on the synthesized page, the right post, AND the exact passage.
    Wiki hits carry the topic in `title` (and post_id IS NULL) — fetch the full page with
    get_wiki_page(topic)."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT * FROM (
              SELECT post_id, platform_id, kind, title, SUBSTR(caption, 1, 400) AS snippet, url,
                     series, 'item' AS lvl,
                     VECTOR_DISTANCE(content_embedding,
                                     VECTOR_EMBEDDING({EMBED_MODEL} USING :q AS DATA), COSINE) AS dist
              FROM   posts
              WHERE  content_embedding IS NOT NULL AND NVL(visibility,'content') = 'content'
              UNION ALL
              SELECT p.post_id, p.platform_id, p.kind, p.title, SUBSTR(ch.chunk, 1, 400) AS snippet,
                     p.url, p.series, 'passage' AS lvl,
                     VECTOR_DISTANCE(ch.embedding,
                                     VECTOR_EMBEDDING({EMBED_MODEL} USING :q AS DATA), COSINE) AS dist
              FROM   content_chunks ch JOIN posts p ON p.post_id = ch.post_id
              WHERE  NVL(p.visibility,'content') = 'content'
              UNION ALL
              SELECT NULL AS post_id, 'wiki' AS platform_id, 'page' AS kind, topic AS title,
                     SUBSTR(body, 1, 400) AS snippet, NULL AS url, NULL AS series, 'wiki' AS lvl,
                     VECTOR_DISTANCE(embedding,
                                     VECTOR_EMBEDDING({EMBED_MODEL} USING :q AS DATA), COSINE) AS dist
              FROM   wiki_pages
              WHERE  embedding IS NOT NULL
            )
            ORDER BY dist
            FETCH FIRST {int(k)} ROWS ONLY
            """,
            q=query,
        )
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _terms(query):
    return [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2][:8]


def _lexical_posts(conn, terms, k):
    """Keyword search over posts (title + caption), ranked by how many query terms match.
    Catches exact names/handles/error codes that pure-vector search can miss."""
    if not terms:
        return []
    score = " + ".join(f"(CASE WHEN UPPER(NVL(title,' ')||' '||caption) LIKE :t{i} "
                       f"THEN 1 ELSE 0 END)" for i in range(len(terms)))
    where = " OR ".join(f"UPPER(NVL(title,' ')||' '||caption) LIKE :t{i}" for i in range(len(terms)))
    sql = (f"SELECT post_id, platform_id, kind, title, SUBSTR(caption,1,400) AS snippet, url, "
           f"series, 'item' AS lvl FROM posts WHERE caption IS NOT NULL "
           f"AND NVL(visibility,'content') = 'content' AND ({where}) "
           f"ORDER BY ({score}) DESC, post_id FETCH FIRST {int(k)} ROWS ONLY")
    binds = {f"t{i}": f"%{terms[i].upper()}%" for i in range(len(terms))}
    with conn.cursor() as cur:
        cur.execute(sql, **binds)
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def doc_chunks(text, size=1600, max_chunks=500):
    """Chunks for LONG documents (e-books, imported PDFs): pack paragraphs into
    ~size-char blocks so a whole book stays searchable, not just its opening.
    note_chunks' 40-paragraph cap is right for notes; books need the full text."""
    paras = []
    for p in re.split(r"\n\s*\n|\n", text or ""):
        p = p.strip()
        if not p:
            continue
        while len(p) > size:                      # a wall-of-text "paragraph": split on
            cut = p.rfind(". ", 0, size) + 1      # the last sentence end before the limit
            if cut <= 0:
                cut = size
            paras.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            paras.append(p)
    blocks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) > size and buf:
            blocks.append(buf)
            buf = p
        else:
            buf = f"{buf}\n{p}" if buf else p
        if len(blocks) >= max_chunks:
            break
    if buf and len(blocks) < max_chunks:
        blocks.append(buf)
    return [b[:2000] for b in blocks]


def note_chunks(text, max_chunks=40):
    """Paragraph-level chunks for a note body, so notes get passage-level search like
    chats and transcripts do. A note saved as prose would otherwise exist only as one
    diluted post-level embedding and lose to chunked sources on specific queries."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return [p[:2000] for p in paras[:max_chunks]]


def _rid(r):
    return f"wiki:{r['title']}" if r.get("lvl") == "wiki" else f"{r['lvl']}:{r.get('post_id')}"


CHAT_PLATFORMS = {"chatgpt", "claude", "claude_code"}
# Workflow/AI-chat items carry dense summary text that over-ranks against the published
# content it summarizes. A gentle fusion weight (<1) makes published work win close calls
# while chats still surface whenever they're genuinely the best match. 1.0 disables.
CHAT_SOURCE_WEIGHT = float(__import__("os").environ.get("CHAT_SOURCE_WEIGHT", "0.75"))


def _src_weight(r):
    return CHAT_SOURCE_WEIGHT if r.get("platform_id") in CHAT_PLATFORMS else 1.0


def _collapse(rows):
    """One entry per document, keeping its BEST-ranked row — the guard against length bias.

    A long chat or transcript is chunked into many passages, and every chunk is a separate
    candidate that maps to the same fusion id. Scored as-is, RRF would add one increment PER
    CHUNK, so a 9-chunk build log accumulates ~9x the score of a tight, single-shot item and
    wins for being long rather than for being right. Rank-ordered in, so the first row a
    document contributes is its best; the rest are dropped before scoring."""
    out, seen = [], set()
    for r in rows:
        rid = _rid(r)
        if rid not in seen:
            seen.add(rid)
            out.append((rid, r))
    return out


def search_hybrid(conn, query, k=8, C=60):
    """Hybrid retrieval: fuse semantic (vector) and keyword (lexical) results with Reciprocal
    Rank Fusion. Vector handles meaning; lexical rescues exact tokens; a source-type weight
    keeps published content ahead of workflow chats on close calls. Returns the same row
    shape as search_content.

    Each retriever is collapsed to one entry per document FIRST (see _collapse), then the two
    are summed: a document is rewarded for being found by BOTH retrievers, never for being
    chopped into more chunks than its neighbours."""
    pool = max(k * 3, 20)
    vec = search_content(conn, query, pool)
    lex = _lexical_posts(conn, _terms(query), pool)
    scores, meta, retr = {}, {}, {}
    for rank, (rid, r) in enumerate(_collapse(vec)):
        scores[rid] = scores.get(rid, 0.0) + _src_weight(r) / (C + rank)
        meta[rid] = r
        retr.setdefault(rid, set()).add("semantic")
    for rank, (rid, r) in enumerate(_collapse(lex)):
        scores[rid] = scores.get(rid, 0.0) + _src_weight(r) / (C + rank)
        meta.setdefault(rid, r)
        retr.setdefault(rid, set()).add("keyword")
    ranked = sorted(scores, key=lambda x: scores[x], reverse=True)[:k]
    out = []
    for i, rid in enumerate(ranked, 1):
        row = dict(meta[rid])          # attach the fusion trace (educational + honest)
        row["rank"] = i
        row["rrf_score"] = round(scores[rid], 4)
        row["retrievers"] = sorted(retr[rid])   # ['semantic'], ['keyword'], or both
        out.append(row)
    return out


def get_wiki_page(conn, topic):
    """Full compiled wiki page for a topic, with its citations back to your content.
    Reads the JSON Relational Duality view — ONE query returns the page as a single JSON
    document with the citations already nested (wiki_pages + page_sources + posts, no manual
    joins; the Duality view does the assembly).
    Returns {topic, body, citations:[{post_id,title,platform,url}]} or None."""
    import json as _json
    with conn.cursor() as cur:
        cur.execute("SELECT data FROM wiki_page_dv WHERE JSON_VALUE(data, '$.topic') = :t",
                    t=topic)
        row = cur.fetchone()
        if not row:
            return None
        doc = _json.loads(row[0]) if isinstance(row[0], (str, bytes)) else row[0]
        cites = [{"post_id": s["post"]["postId"], "title": s["post"]["title"],
                  "platform": s["post"]["platform"], "url": s["post"]["url"]}
                 for s in doc.get("sources", [])]
        # READ-TIME visibility guard: the Duality view nests posts unfiltered, and a post
        # can be retagged private AFTER the page was compiled (classify_private runs post-
        # ingestion). Between that retag and the next wiki refresh, its title/url would
        # still leak here as a citation — so re-check scope now, the same rule graph_data
        # applies at read time.
        if cites:
            ids = [c["post_id"] for c in cites]
            binds = ",".join(f":i{n}" for n in range(len(ids)))
            cur.execute(f"SELECT post_id FROM posts WHERE post_id IN ({binds}) "
                        "AND NVL(visibility,'content')='content'",
                        {f"i{n}": v for n, v in enumerate(ids)})
            ok = {r[0] for r in cur.fetchall()}
            cites = [c for c in cites if c["post_id"] in ok]
        return {"topic": doc["topic"], "body": doc["body"], "citations": cites}


def list_topics(conn):
    """The compiled wiki topics (titles only)."""
    with conn.cursor() as cur:
        cur.execute("SELECT topic FROM wiki_pages ORDER BY topic")
        return [r[0] for r in cur.fetchall()]


def list_series(conn):
    """The content series present in the brain (e.g. 'tech_walk') with a count each."""
    with conn.cursor() as cur:
        cur.execute("SELECT series, COUNT(*) AS n FROM posts WHERE series IS NOT NULL "
                    "AND NVL(visibility,'content')='content' GROUP BY series ORDER BY n DESC")
        return [{"series": r[0], "count": int(r[1])} for r in cur.fetchall()]


def list_by_series(conn, series, k=25):
    """List items in a content series (e.g. 'tech_walk'), most recent first."""
    with conn.cursor() as cur:
        cur.execute("SELECT post_id, platform_id, kind, title, url, "
                    "TO_CHAR(published_at,'YYYY-MM-DD') AS published FROM posts "
                    "WHERE series = :s AND NVL(visibility,'content')='content' "
                    "ORDER BY published_at DESC NULLS LAST FETCH FIRST :k ROWS ONLY",
                    s=series, k=int(k))
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def stats(conn):
    """A high-level map of the brain (content scope only): total items, per-platform counts,
    per-kind counts, per-series counts, wiki topic count, and the published date range. Cheap
    orientation for a demo, the overview dashboard, or the agent sizing up what's here."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), TO_CHAR(MIN(published_at),'YYYY-MM-DD'), "
                    "TO_CHAR(MAX(published_at),'YYYY-MM-DD') FROM posts "
                    "WHERE NVL(visibility,'content')='content'")
        total, first, last = cur.fetchone()
        cur.execute("SELECT platform_id, COUNT(*) AS n FROM posts "
                    "WHERE NVL(visibility,'content')='content' "
                    "GROUP BY platform_id ORDER BY n DESC")
        by_platform = [{"platform": r[0], "count": int(r[1])} for r in cur.fetchall()]
        cur.execute("SELECT kind, COUNT(*) AS n FROM posts "
                    "WHERE NVL(visibility,'content')='content' AND kind IS NOT NULL "
                    "GROUP BY kind ORDER BY n DESC")
        by_kind = [{"kind": r[0], "count": int(r[1])} for r in cur.fetchall()]
    return {"total_items": int(total or 0), "by_platform": by_platform, "by_kind": by_kind,
            "series": list_series(conn), "wiki_topics": len(list_topics(conn)),
            "published_range": {"from": first, "to": last}}


def get_post(conn, post_id):
    """Full content of one post (for the agent to read in detail)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT post_id, platform_id, kind, title, caption, url, published_at, views "
            "FROM posts WHERE post_id = :id AND NVL(visibility,'content') = 'content'", id=post_id)
        row = cur.fetchone()
        if not row:
            return None
        cols = [c[0].lower() for c in cur.description]
        return dict(zip(cols, row))


def related_posts(conn, post_id, k=8):
    """Semantic neighbors of one post — "what else have I made like this?" — by cosine
    distance between STORED embeddings (no re-embedding; the vectors are already in the rows).
    This is the edge a manual-links tool can't draw: items connect by meaning, not by
    hand-typed links. Visibility is filtered on BOTH sides: a private anchor returns []
    (it must not act as a query vector), and private items never appear as neighbors.
    An anchor with no embedding also returns [] — absence of neighbors, not an error."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p2.post_id, p2.platform_id, p2.kind, p2.title, p2.url, p2.series,
                   VECTOR_DISTANCE(p2.content_embedding, p1.content_embedding, COSINE) AS dist
            FROM   posts p1 JOIN posts p2 ON p2.post_id <> p1.post_id
            WHERE  p1.post_id = :id
              AND  p1.content_embedding IS NOT NULL AND p2.content_embedding IS NOT NULL
              AND  NVL(p1.visibility,'content') = 'content'
              AND  NVL(p2.visibility,'content') = 'content'
            ORDER  BY dist
            FETCH FIRST :k ROWS ONLY
            """, id=int(post_id), k=int(k))
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def related_topics(conn, topic, k=8):
    """Content items semantically nearest to a wiki TOPIC page's own embedding — reaches
    beyond the page's citations to items the compiler hasn't linked (yet). Same visibility
    rule as everywhere: only content-scope posts can surface."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.post_id, p.platform_id, p.kind, p.title, p.url, p.series,
                   VECTOR_DISTANCE(p.content_embedding, w.embedding, COSINE) AS dist
            FROM   wiki_pages w, posts p
            WHERE  w.topic = :t AND w.embedding IS NOT NULL
              AND  p.content_embedding IS NOT NULL
              AND  NVL(p.visibility,'content') = 'content'
            ORDER  BY dist
            FETCH FIRST :k ROWS ONLY
            """, t=topic, k=int(k))
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def graph_data(conn):
    """Everything a knowledge-graph view needs, in one payload: wiki topics as hub nodes,
    the content items they cite as leaf nodes, topic->topic cross-links (page_links), and
    citation edges (page_sources). Only CITED posts become nodes, so the payload stays
    bounded however large the brain grows. The citation join filters visibility — a private
    item cited by a page must not leak through the graph."""
    nodes, links = [], []
    with conn.cursor() as cur:
        cur.execute("SELECT page_id, topic FROM wiki_pages ORDER BY topic")
        by_pid = {int(pid): t for pid, t in cur.fetchall()}
        nodes += [{"id": f"wiki:{t}", "type": "topic", "label": t}
                  for t in sorted(by_pid.values())]
        cur.execute("SELECT from_page_id, to_page_id FROM page_links")
        for f, t in cur.fetchall():
            if int(f) in by_pid and int(t) in by_pid:
                links.append({"source": f"wiki:{by_pid[int(f)]}",
                              "target": f"wiki:{by_pid[int(t)]}", "type": "topic"})
        cur.execute(
            "SELECT ps.page_id, p.post_id, p.title, p.platform_id, p.kind, p.series "
            "FROM page_sources ps JOIN posts p ON p.post_id = ps.post_id "
            "WHERE NVL(p.visibility,'content') = 'content'")
        seen = set()
        for page_id, pid, title, platform, kind, series in cur.fetchall():
            if int(page_id) not in by_pid:
                continue
            if pid not in seen:
                seen.add(pid)
                node = {"id": f"item:{pid}", "type": "item",
                        "label": title or f"item {pid}", "platform": platform, "kind": kind}
                if series:
                    node["series"] = series
                nodes.append(node)
            links.append({"source": f"wiki:{by_pid[int(page_id)]}",
                          "target": f"item:{pid}", "type": "citation"})
    return {"nodes": nodes, "links": links}
