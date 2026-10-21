from langchain_oracledb import OracleTextSearchRetriever
from workshop.retrieval import keyword_terms

def hybrid_search_knowledge(query: str, k: int = 5, rrf_k: int = 60) -> list[dict]:
    """Vector search + keyword search over AML_KNOWLEDGE_VS, fused with Reciprocal Rank Fusion."""
    vec = [doc for doc, _ in knowledge_vs.similarity_search_with_score(query, k=30)]                # search by meaning
    txt = OracleTextSearchRetriever(vector_store=knowledge_vs, k=30).invoke(keyword_terms(query))  # search by keywords
    fused = {}   # one entry per result, shared by both searches
    for leg, docs in (("vec_rank", vec), ("txt_rank", txt)):
        for rank, doc in enumerate(docs, start=1):
            hit = fused.setdefault(doc.id, to_hit(doc, rrf_score=0.0, vec_rank=None, txt_rank=None))
            hit[leg] = rank                          # where this result ranked in this search
            hit["rrf_score"] += 1 / (rrf_k + rank)   # its points for that rank: 1/61, 1/62, ...
    return sorted(fused.values(), key=lambda h: h["rrf_score"], reverse=True)[:k]   # best total first
