"""
Pre-cache the embedding model during Codespace build.
"""
from sentence_transformers import SentenceTransformer

MODEL = "sentence-transformers/all-MiniLM-L6-v2"

print(f"Pre-caching {MODEL}...")
SentenceTransformer(MODEL)
print("Done. Model is cached and ready.")
