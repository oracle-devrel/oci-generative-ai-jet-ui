"""Layer 3 agent tool surface.

The LLM sees four tools per side: vector_search, count_products, top_products,
group_by. Each has a Mongo implementation and an Oracle implementation.
The agent's experience of which tools exist is identical on both sides -- that's
the migration story Layer 3 tells when the substrate flips.

All tool functions take ``side`` as their first argument so the dispatch table
can route them without knowing which database is live. The LLM never sees
``side`` in the schema; it's injected by the agent loop in model.py.
"""

from __future__ import annotations

# ── Vector search ─────────────────────────────────────────────────────────────

_embedding_model = None


def _embed(text: str) -> list[float]:
    """Lazy-load the sentence-transformer embedding model (shared singleton)."""
    global _embedding_model
    if _embedding_model is None:
        import os

        from sentence_transformers import SentenceTransformer

        model_name = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model.encode([text], normalize_embeddings=True)[0].tolist()


def vector_search(side: str, query: str, k: int = 5) -> list[dict]:
    """Search reviews semantically. Use for 'what do people say' questions.

    Args:
        side: 'mongo' or 'oracle'.
        query: The natural-language question to embed and search for.
        k: Number of results to return (default 5).

    Returns:
        List of dicts with name, category, review_text, score keys.

    Example:
        >>> vector_search("mongo", "wireless headphones noise cancelling", k=3)
    """
    from data_migration_harness import source_config
    from data_migration_harness.tools import mongo_reader
    from data_migration_harness.tools.vector_oracle import vector_search_oracle

    qv = _embed(query)
    if side == "mongo":
        results = mongo_reader.vector_search_mongo(source_config.collection_name(), qv, k=k)
    else:
        results = vector_search_oracle(qv, k=k)
    return [
        {
            "name": r.get("name"),
            "category": r.get("category"),
            "review_text": r.get("review_text") or r.get("text", ""),
            "score": round(float(r.get("score", r.get("distance", 0))), 4),
        }
        for r in results
    ]


# ── Count ─────────────────────────────────────────────────────────────────────


def count_products(
    side: str,
    category: str | None = None,
    min_rating: int | None = None,
    verified_only: bool = False,
) -> dict:
    """Count products matching optional filters.

    Args:
        side: 'mongo' or 'oracle'.
        category: Optional category name filter (Audio, Wearables, Home, etc.).
        min_rating: Only count products with at least one review at or above this rating.
        verified_only: Restrict to products with verified-buyer reviews only.

    Returns:
        Dict with a single 'count' key.

    Example:
        >>> count_products("oracle", category="Audio", min_rating=4)
    """
    if side == "mongo":
        return _count_products_mongo(
            category=category, min_rating=min_rating, verified_only=verified_only
        )
    return _count_products_oracle(
        category=category, min_rating=min_rating, verified_only=verified_only
    )


def _count_products_mongo(
    category: str | None,
    min_rating: int | None,
    verified_only: bool,
) -> dict:
    from data_migration_harness import source_config

    match: dict = {}
    if category:
        match["category"] = category
    if min_rating is not None:
        review_filter: dict = {"rating": {"$gte": min_rating}}
        if verified_only:
            review_filter["verified_buyer"] = True
        match["reviews"] = {"$elemMatch": review_filter}
    elif verified_only:
        match["reviews"] = {"$elemMatch": {"verified_buyer": True}}
    pipeline = [{"$match": match}, {"$count": "n"}]
    result = list(source_config.collection().aggregate(pipeline))
    return {"count": result[0]["n"] if result else 0}


def _count_products_oracle(
    category: str | None,
    min_rating: int | None,
    verified_only: bool,
) -> dict:
    from data_migration_harness.environment import oracle_pool

    pool = oracle_pool()
    params: dict = {}
    clauses: list[str] = []

    if min_rating is not None or verified_only:
        # Need a join with reviews
        sql = "SELECT COUNT(DISTINCT p.product_id) FROM products p JOIN reviews r ON r.product_id = p.product_id"
        if category:
            clauses.append("p.category = :cat")
            params["cat"] = category
        if min_rating is not None:
            clauses.append("r.rating >= :min_rating")
            params["min_rating"] = min_rating
        if verified_only:
            clauses.append("r.verified_buyer = 1")
    else:
        sql = "SELECT COUNT(*) FROM products p"
        if category:
            clauses.append("p.category = :cat")
            params["cat"] = category

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)

    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        (n,) = cur.fetchone()
    return {"count": int(n)}


# ── Top products ──────────────────────────────────────────────────────────────


def top_products(
    side: str,
    by: str = "price",
    order: str = "desc",
    limit: int = 5,
    max_price: float | None = None,
) -> list[dict]:
    """Get top-N products by price or average rating.

    Args:
        side: 'mongo' or 'oracle'.
        by: 'price' or 'rating' -- the field to rank by.
        order: 'desc' (highest first) or 'asc' (lowest first).
        limit: Number of results to return (default 5).
        max_price: Optional upper price ceiling.

    Returns:
        List of dicts with name, category, price, avg_rating keys.

    Example:
        >>> top_products("oracle", by="rating", order="desc", limit=3)
    """
    if side == "mongo":
        return _top_products_mongo(by=by, order=order, limit=limit, max_price=max_price)
    return _top_products_oracle(by=by, order=order, limit=limit, max_price=max_price)


def _top_products_mongo(
    by: str,
    order: str,
    limit: int,
    max_price: float | None,
) -> list[dict]:
    from data_migration_harness import source_config

    sort_dir = -1 if order == "desc" else 1

    match_stage: dict = {}
    if max_price is not None:
        match_stage["price"] = {"$lte": max_price}

    if by == "price":
        pipeline: list = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        pipeline += [
            {"$sort": {"price": sort_dir}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "name": 1,
                    "category": 1,
                    "price": 1,
                    "avg_rating": {"$avg": "$reviews.rating"},
                }
            },
        ]
    else:
        # Sort by computed average rating
        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        pipeline += [
            {"$addFields": {"avg_rating": {"$avg": "$reviews.rating"}}},
            {"$sort": {"avg_rating": sort_dir}},
            {"$limit": limit},
            {"$project": {"_id": 0, "name": 1, "category": 1, "price": 1, "avg_rating": 1}},
        ]

    results = list(source_config.collection().aggregate(pipeline))
    return [
        {
            "name": r.get("name"),
            "category": r.get("category"),
            "price": r.get("price"),
            "avg_rating": round(float(r["avg_rating"]), 2)
            if r.get("avg_rating") is not None
            else None,
        }
        for r in results
    ]


def _top_products_oracle(
    by: str,
    order: str,
    limit: int,
    max_price: float | None,
) -> list[dict]:
    from data_migration_harness.environment import oracle_pool

    pool = oracle_pool()
    params: dict = {"lim": limit}
    where_clauses: list[str] = []

    if max_price is not None:
        where_clauses.append("p.price <= :max_price")
        params["max_price"] = max_price

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    order_dir = "DESC" if order == "desc" else "ASC"

    if by == "price":
        sort_col = "p.price"
    else:
        sort_col = "avg_rating"

    sql = f"""
        SELECT p.name, p.category, p.price,
               ROUND(AVG(r.rating), 2) AS avg_rating
        FROM products p
        LEFT JOIN reviews r ON r.product_id = p.product_id
        {where_sql}
        GROUP BY p.product_id, p.name, p.category, p.price
        ORDER BY {sort_col} {order_dir} NULLS LAST
        FETCH FIRST :lim ROWS ONLY
    """
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


# ── Group by ──────────────────────────────────────────────────────────────────


def group_by(
    side: str,
    group_field: str = "category",
    metric_field: str = "rating",
    agg: str = "avg",
) -> dict:
    """Group products by a field and compute an aggregate over a metric.

    When group_field='category', metric_field='rating', and agg='avg', the
    response sets is_chart=True so the orchestrator emits a bar chart to the
    frontend rather than embedding the data in the text response.

    Args:
        side: 'mongo' or 'oracle'.
        group_field: 'category' or 'vendor' -- the field to group by.
        metric_field: 'rating', 'price', or 'review_count' -- the metric to aggregate.
        agg: 'avg', 'sum', 'count', 'max', or 'min'.

    Returns:
        Dict with is_chart (bool) and rows (list of {group, value, count}).

    Example:
        >>> group_by("oracle", group_field="category", metric_field="rating", agg="avg")
    """
    if side == "mongo":
        rows = _group_by_mongo(group_field=group_field, metric_field=metric_field, agg=agg)
    else:
        rows = _group_by_oracle(group_field=group_field, metric_field=metric_field, agg=agg)

    is_chart = group_field == "category" and metric_field == "rating" and agg == "avg"
    return {"is_chart": is_chart, "rows": rows}


def _group_by_mongo(group_field: str, metric_field: str, agg: str) -> list[dict]:
    from data_migration_harness import source_config

    # Resolve the grouping key path in the Mongo document
    if group_field == "vendor":
        group_id_expr = "$vendor.name"
    else:
        group_id_expr = f"${group_field}"

    # Resolve the metric accumulator
    agg_ops = {"avg": "$avg", "sum": "$sum", "count": "$sum", "max": "$max", "min": "$min"}
    agg_op = agg_ops.get(agg, "$avg")

    if metric_field == "review_count":
        # Count of review sub-documents per product, then sum/avg across groups
        pass
    elif metric_field == "rating":
        # Reviews are embedded: unwind first, then aggregate rating
        pass
    else:
        pass

    if metric_field in ("rating", "review_count"):
        pipeline = [
            {"$unwind": "$reviews"},
            {
                "$group": {
                    "_id": group_id_expr,
                    "value": (
                        {"$sum": 1}
                        if metric_field == "review_count" and agg in ("count", "sum")
                        else {agg_op: "$reviews.rating"}
                    ),
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"value": -1}},
            {"$project": {"_id": 0, "group": "$_id", "value": 1, "count": 1}},
        ]
    else:
        pipeline = [
            {
                "$group": {
                    "_id": group_id_expr,
                    "value": {agg_op: f"${metric_field}"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"value": -1}},
            {"$project": {"_id": 0, "group": "$_id", "value": 1, "count": 1}},
        ]

    results = list(source_config.collection().aggregate(pipeline))
    return [
        {
            "group": r.get("group", "Unknown"),
            "value": round(float(r["value"]), 2) if r.get("value") is not None else 0,
            "count": int(r.get("count", 0)),
        }
        for r in results
    ]


def _group_by_oracle(group_field: str, metric_field: str, agg: str) -> list[dict]:
    from data_migration_harness.environment import oracle_pool

    pool = oracle_pool()

    agg_sql = agg.upper()
    # Map group_field to the SQL column name
    group_col = "p.vendor_name" if group_field == "vendor" else "p.category"

    if metric_field == "review_count":
        metric_expr = "COUNT(r.review_id)"
        join_type = "LEFT JOIN"
    elif metric_field == "rating":
        metric_expr = f"ROUND({agg_sql}(r.rating), 2)"
        join_type = "LEFT JOIN"
    else:
        # price: no join needed
        metric_expr = f"ROUND({agg_sql}(p.price), 2)"
        join_type = "LEFT JOIN"

    sql = f"""
        SELECT {group_col} AS grp,
               {metric_expr} AS val,
               COUNT(DISTINCT p.product_id) AS cnt
        FROM products p
        {join_type} reviews r ON r.product_id = p.product_id
        GROUP BY {group_col}
        ORDER BY val DESC NULLS LAST
    """
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        return [
            {
                "group": row[0] or "Unknown",
                "value": round(float(row[1]), 2) if row[1] is not None else 0,
                "count": int(row[2]),
            }
            for row in cur.fetchall()
        ]


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, object] = {
    "vector_search": vector_search,
    "count_products": count_products,
    "top_products": top_products,
    "group_by": group_by,
}

# ── JSON Schema for the LLM ───────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "FUNCTION",
        "function": {
            "name": "vector_search",
            "description": (
                "Search the product reviews for reviews semantically similar to the query. "
                "Use for open-ended questions like 'what do people say about X' or "
                "'tell me about Y' or 'what are customers saying'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The semantic question to search for in the reviews",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of results to return (default 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "FUNCTION",
        "function": {
            "name": "count_products",
            "description": (
                "Count products in the database, optionally filtered by category, "
                "minimum rating, or verified-buyer reviews. "
                "Use for 'how many products', 'how many items', 'how many reviews' questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category: Audio, Wearables, Home, Kitchen, Outdoor, or Office",
                    },
                    "min_rating": {
                        "type": "integer",
                        "description": "Only count products with at least one review at or above this star rating (1-5)",
                    },
                    "verified_only": {
                        "type": "boolean",
                        "description": "Only count products that have verified-buyer reviews",
                    },
                },
            },
        },
    },
    {
        "type": "FUNCTION",
        "function": {
            "name": "top_products",
            "description": (
                "List products ranked by price or average rating. "
                "Use for 'most expensive', 'cheapest', 'lowest price', 'highest rated', 'best rated' questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "by": {
                        "type": "string",
                        "enum": ["price", "rating"],
                        "description": "Which field to rank by: 'price' or 'rating'",
                    },
                    "order": {
                        "type": "string",
                        "enum": ["desc", "asc"],
                        "description": "Sort order: 'desc' for highest first, 'asc' for lowest first (default: desc)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (default 5)",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Optional upper price ceiling to filter products",
                    },
                },
                "required": ["by"],
            },
        },
    },
    {
        "type": "FUNCTION",
        "function": {
            "name": "group_by",
            "description": (
                "Group products by a field and compute an aggregate metric. "
                "Use for 'average rating by category', 'most popular brand', "
                "'which vendor has the highest price', 'breakdown by category' questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "group_field": {
                        "type": "string",
                        "enum": ["category", "vendor"],
                        "description": "The field to group by",
                    },
                    "metric_field": {
                        "type": "string",
                        "enum": ["rating", "price", "review_count"],
                        "description": "The metric to aggregate",
                    },
                    "agg": {
                        "type": "string",
                        "enum": ["avg", "sum", "count", "max", "min"],
                        "description": "The aggregation function to apply",
                    },
                },
                "required": ["group_field", "metric_field", "agg"],
            },
        },
    },
]
