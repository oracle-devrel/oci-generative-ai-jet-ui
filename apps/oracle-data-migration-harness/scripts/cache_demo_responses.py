"""Generate a local runtime cache for the two preset demo questions."""

import os

from data_migration_harness.app import save_demo_cache
from data_migration_harness.tools import mongo_reader
from data_migration_harness.tools.duality import DEMO_AGGREGATION, run_sql_aggregation
from data_migration_harness.tools.vector_oracle import vector_search_oracle
from sentence_transformers import SentenceTransformer

PRESETS = [
    "What do customers say about wireless headphones?",
    "Average rating by category for products under £50, verified buyers only, last 90 days",
]


def main():
    model_name = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    print(f"Embedding with {model_name}")
    model = SentenceTransformer(model_name)

    for q in PRESETS:
        qv = model.encode([q], normalize_embeddings=True)[0].tolist()
        if "average" in q.lower():
            rows = run_sql_aggregation(DEMO_AGGREGATION, {"max_price": 50.0})
            mongo_payload = {
                "text": "MongoDB cannot easily aggregate this kind of question across documents."
            }
            oracle_payload = {
                "text": "Here is the breakdown by category.",
                "chart": {"type": "bar", "x": "category", "y": "avg_rating", "data": rows},
            }
        else:
            m = mongo_reader.vector_search_mongo("products", qv, k=5)
            o = vector_search_oracle(qv, k=5)
            mongo_payload = {
                "text": "Customers say: "
                + " ".join((r.get("review_text") or r.get("text", "")) for r in m[:3])[:400]
            }
            oracle_payload = {
                "text": "Customers say: "
                + " ".join((r.get("review_text") or r.get("text", "")) for r in o[:3])[:400]
            }
        save_demo_cache("mongo", q, mongo_payload)
        save_demo_cache("oracle", q, oracle_payload)

    print("Demo cache written to .cache/demo_cache.json (or DEMO_CACHE_PATH if set)")


if __name__ == "__main__":
    main()
