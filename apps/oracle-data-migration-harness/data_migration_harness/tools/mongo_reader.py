"""Layer 3 tool: MongoDB source reader."""

from data_migration_harness import source_config


def list_collections() -> list[str]:
    return source_config.database().list_collection_names()


def describe_collection(name: str) -> dict:
    db = source_config.database()
    col = db[name]
    sample_doc = col.find_one()
    if not sample_doc:
        return {"name": name, "fields": {}, "count": 0}
    return {"name": name, "count": col.count_documents({}), "fields": _shape(sample_doc)}


def _shape(doc: dict) -> dict:
    out = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        if isinstance(v, dict):
            out[k] = {"type": "object", "shape": _shape(v)}
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            out[k] = {"type": "array<object>", "shape": _shape(v[0])}
        elif isinstance(v, list):
            out[k] = {"type": f"array<{type(v[0]).__name__}>" if v else "array"}
        else:
            out[k] = {"type": type(v).__name__}
    return out


def sample(collection: str, n: int = 5) -> list[dict]:
    return list(source_config.database()[collection].aggregate([{"$sample": {"size": n}}]))


def vector_search_mongo(collection: str, query_vector: list[float], k: int = 5) -> list[dict]:
    """Vector search via Atlas Vector Search index, with local cosine fallback.

    Atlas Vector Search requires MongoDB Atlas or a self-hosted enterprise build
    with the search index plugin. The local mongo:7 podman image does NOT have
    it. Local cosine fallback is what runs in dev and on the demo machine; the
    Atlas path stays for production deployments.

    Args:
        collection: Name of the MongoDB collection to search.
        query_vector: The embedding vector to search against.
        k: Number of results to return.

    Returns:
        A list of dicts with name, category, review_text, and score fields.

    Example:
        >>> results = vector_search_mongo("products", [0.1, 0.2, ...], k=3)
    """
    db = source_config.database()
    col = db[collection]
    pipeline = [
        {
            "$vectorSearch": {
                "index": "review_vec",
                "path": "review_embedding",
                "queryVector": query_vector,
                "numCandidates": k * 10,
                "limit": k,
            }
        },
        {
            "$project": {
                "_id": 0,
                "name": 1,
                "category": 1,
                "review_text": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    try:
        return list(col.aggregate(pipeline))
    except Exception:
        return _local_cosine_search(col, query_vector, k)


def _local_cosine_search(col, qv, k):
    import numpy as np

    docs = list(
        col.find(
            {"review_embedding": {"$exists": True}},
            {"name": 1, "category": 1, "review_text": 1, "review_embedding": 1},
        )
    )
    if not docs:
        return []
    qv = np.array(qv)
    scored = []
    for d in docs:
        ev = np.array(d["review_embedding"])
        denom = np.linalg.norm(qv) * np.linalg.norm(ev)
        score = float(np.dot(qv, ev) / denom) if denom else 0.0
        out = {
            col_name: d[col_name]
            for col_name in ("name", "category", "review_text")
            if col_name in d
        }
        out["score"] = score
        scored.append(out)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]


def aggregate_mongo(collection: str, pipeline: list) -> list[dict]:
    """Deliberately exposes aggregation; the demo shows this struggles for SQL-like questions.

    Args:
        collection: Name of the MongoDB collection to run the pipeline against.
        pipeline: A list of aggregation stage dicts.

    Returns:
        A list of result dicts from the aggregation pipeline.

    Example:
        >>> aggregate_mongo("products", [{"$group": {"_id": "$category", "count": {"$sum": 1}}}])
    """
    return list(source_config.database()[collection].aggregate(pipeline))
