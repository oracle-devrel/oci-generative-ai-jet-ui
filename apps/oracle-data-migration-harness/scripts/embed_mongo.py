"""Add review embeddings to the Mongo corpus.

For each product, pick the highest-rated review, encode it locally with
sentence-transformers (no API call, no data leaves the machine), and write
the embedding plus the chosen review text back to the product document.
"""

import os

from data_migration_harness.environment import mongo_db
from pymongo import UpdateOne
from sentence_transformers import SentenceTransformer


def main():
    model_name = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    print(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    db = mongo_db()
    docs = list(db.products.find({}))
    print(f"Embedding {len(docs)} products...")
    texts: list[str] = []
    review_texts: list[str] = []
    ids = []
    for doc in docs:
        if not doc.get("reviews"):
            continue
        review = max(doc["reviews"], key=lambda r: r.get("rating", 0))
        texts.append(f"{doc['name']}: {review['text']}")
        review_texts.append(review["text"])
        ids.append(doc["_id"])
    embeddings = model.encode(
        texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True
    )
    bulk = []
    for _id, rt, emb in zip(ids, review_texts, embeddings, strict=False):
        bulk.append(
            UpdateOne(
                {"_id": _id},
                {"$set": {"review_text": rt, "review_embedding": emb.tolist()}},
            )
        )
    if bulk:
        result = db.products.bulk_write(bulk, ordered=False)
        print(f"Modified {result.modified_count} documents")
    sample = db.products.find_one(
        {"review_embedding": {"$exists": True}},
        {"name": 1, "review_text": 1, "review_embedding": 1},
    )
    if sample:
        emb = sample["review_embedding"]
        print(f"Sample embedded doc: {sample['name']}")
        print(f"  review_text: {sample['review_text'][:80]}")
        print(f"  embedding dim: {len(emb)} (first 4 values: {[round(v, 4) for v in emb[:4]]})")


if __name__ == "__main__":
    main()
