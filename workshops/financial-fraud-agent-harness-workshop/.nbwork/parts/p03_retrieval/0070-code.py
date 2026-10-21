# TODO 4: implement retrieve_knowledge
from workshop.retrieval import to_hit

def retrieve_knowledge(query: str, k: int = 5,
                       kinds: list[str] | None = None) -> list[dict]:
    """Vector search over AML_KNOWLEDGE_VS, reranked."""
    if isinstance(kinds, str):  # an LLM may pass "a,b" as one string
        kinds = [s.strip() for s in kinds.split(",") if s.strip()]
    # Only facts of these kinds ("$in" = the kind is any one of these); None = search every kind.
    flt = {"kind": {"$in": kinds}} if kinds else None

    hits = knowledge_vs.similarity_search_with_score(query, k=k * 4, filter=flt)

    candidates = [to_hit(doc, distance=float(dist)) for doc, dist in hits]
    return rerank(query, candidates, top_k=k, content_key="body")   # keep the best k
