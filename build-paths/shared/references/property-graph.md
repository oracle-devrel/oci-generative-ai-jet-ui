# Property graph

Graph features for the advanced path: knowledge graphs, agent reasoning over entity relationships, "more like this through these edges."

Oracle has SQL/PGQ for in-DB graph queries. **For bidirectional graphs, prefer Python BFS over an adjacency table** to the recursive-WITH approach — Oracle's recursive CTE has a cycle-detection bug on bidirectional edges that's more pain than the perf win is worth at the scale advanced projects run at.

## When to use

| Use it when | Don't use it when |
| --- | --- |
| You have entities + edges and want n-hop neighborhoods. | You only need flat similarity — that's vector search territory. |
| Edges carry typed semantics ("cites", "depends-on", "co-occurs-with"). | Edges are just "any-relationship" — overkill. |
| You want to combine vector recall with graph hops ("things 2 hops away from X, ranked by similarity to Y"). | You don't have explicit edges yet. |

## Schema pattern

Two tables: vertices and edges. Both are normal tables; the graph-ness is in how you query.

```sql
CREATE TABLE entity (
    entity_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind        VARCHAR2(40) NOT NULL,    -- 'person', 'paper', 'tool', ...
    name        VARCHAR2(200) NOT NULL,
    embedding   VECTOR(768, FLOAT32),     -- so we can do vector + graph
    metadata    JSON
);

CREATE TABLE edge (
    edge_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    src_id      NUMBER NOT NULL REFERENCES entity(entity_id),
    dst_id      NUMBER NOT NULL REFERENCES entity(entity_id),
    rel         VARCHAR2(40) NOT NULL,    -- 'cites', 'co-author-with', ...
    weight      NUMBER DEFAULT 1.0,
    UNIQUE(src_id, dst_id, rel)
);

CREATE INDEX edge_src_idx ON edge(src_id, rel);
CREATE INDEX edge_dst_idx ON edge(dst_id, rel);
```

For undirected graphs, insert both directions or treat the index lookups as bidirectional.

## Why Python BFS, not recursive WITH

Oracle's `WITH ... RECURSIVE` chokes on bidirectional graphs (A↔B↔A) — you get either an infinite loop or wrong cycle detection depending on how you arrange the predicates. The exemplar at `~/git/work/demoapp/api/app/routers/graph.py:1-80` proves this empirically. Python BFS over a small adjacency map is ~5 lines, terminates correctly, and is fast enough for the scale advanced projects run at (10s of thousands of nodes, not 10s of millions).

```python
def n_hop_neighbors(conn, start_id: int, n: int = 2) -> set[int]:
    # Load adjacency once for the n-hop frontier.
    with conn.cursor() as cur:
        cur.execute("SELECT src_id, dst_id FROM edge")
        adj: dict[int, set[int]] = {}
        for src, dst in cur.fetchall():
            adj.setdefault(src, set()).add(dst)
            adj.setdefault(dst, set()).add(src)  # bidirectional

    visited = {start_id}
    frontier = {start_id}
    for _ in range(n):
        nxt = set()
        for node in frontier:
            nxt |= adj.get(node, set()) - visited
        visited |= nxt
        frontier = nxt
        if not frontier:
            break
    return visited - {start_id}
```

For graphs that don't fit in memory, do a per-step `SELECT dst_id FROM edge WHERE src_id IN (:frontier)` lookup — bind the frontier, get the next layer, repeat. Pattern from `_load_adjacency()` + `_build_id_binds()` in the exemplar.

## Combining vector with graph

The advanced sweet spot. "Find papers similar to X, but only among papers cited by authors I follow":

```python
# Step 1: graph — collect candidate paper IDs.
candidates = papers_cited_by_authors_followed(conn, user_id)

# Step 2: vector — rank inside the candidate set.
qv = array.array("f", embedder.embed_query(query))
with conn.cursor() as cur:
    cur.execute(f"""
        SELECT entity_id
        FROM entity
        WHERE entity_id IN ({','.join('?'*len(candidates))})
        ORDER BY VECTOR_DISTANCE(embedding, :qv, COSINE)
        FETCH FIRST :k ROWS ONLY
    """, [*candidates, qv, 5])
```

The graph step shrinks the candidate set; the vector step ranks inside it. Best of both.

## When SQL/PGQ does help

For fixed-shape pattern matching ("find triangles", "find paths of length 3 with edge labels A→B→C"), SQL/PGQ is genuinely cleaner than BFS. The advanced skill mentions it but doesn't scaffold it by default — adds complexity, narrow payoff for the project shapes we're targeting.

## Don't do these

- Don't model "any-relationship" with one edge type and a free-text `rel`. That's just a table. Add typed edges or skip graph entirely.
- Don't try to do graph traversal in the agent's reasoning loop — pre-compute neighborhoods, hand them to the LLM as context.
- Don't store edge weights as strings. Make them `NUMBER` and let the DB do arithmetic.
- Don't build a graph and then ignore the vector column. The whole point at the advanced tier is to combine signals.

## Exemplar

`~/git/work/demoapp/api/app/routers/graph.py:1-80` — adjacency table + BFS + bind-variable handling for the n-hop case.

## Canonical doc

https://docs.oracle.com/en/database/oracle/oracle-database/26/spgdg/
