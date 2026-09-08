"""Routes queries to appropriate retrieval strategy."""

from retrieval.graph_search import find_similar_accounts
from retrieval.hybrid_search import hybrid_rrf
from retrieval.spatial_search import find_nearby_clients
from retrieval.text_search import keyword_search
from retrieval.vector_search import vector_search


def route_and_retrieve(conn, embedding_model, query, strategy="auto", query_logger=None, **kwargs):
    """Route a query to the best retrieval strategy.

    Strategies: 'vector', 'text', 'hybrid', 'graph', 'spatial', 'auto'
    """
    top_k = kwargs.get("top_k", 5)

    if strategy == "vector":
        return vector_search(conn, embedding_model, query, top_k=top_k, query_logger=query_logger)
    elif strategy == "text":
        return keyword_search(conn, query, top_k=top_k, query_logger=query_logger)
    elif strategy == "hybrid":
        return hybrid_rrf(conn, embedding_model, query, top_k=top_k, query_logger=query_logger)
    elif strategy == "graph":
        account_id = kwargs.get("account_id")
        if account_id:
            return find_similar_accounts(conn, account_id, top_k=top_k, query_logger=query_logger)
        return [], []
    elif strategy == "spatial":
        account_id = kwargs.get("account_id")
        radius_km = kwargs.get("radius_km", 500)
        if account_id:
            return find_nearby_clients(
                conn, account_id, radius_km=radius_km, top_k=top_k, query_logger=query_logger
            )
        return [], []
    else:
        # Auto: use vector by default
        return vector_search(conn, embedding_model, query, top_k=top_k, query_logger=query_logger)
