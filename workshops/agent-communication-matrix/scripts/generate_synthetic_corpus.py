"""Generate a synthetic corpus for benchmarking.

Latency benchmarks don't care about content quality, just volume and shape.
Produces 10,000 chunks of plausible-length text suitable for embedding
and indexing in Oracle AI Database.

Usage:
    python scripts/generate_synthetic_corpus.py
"""
import random

random.seed(42)  # reproducible across runs

TOPICS = [
    "vector search",
    "database transactions",
    "agent memory",
    "tool calling",
    "embedding models",
    "queue semantics",
    "distributed systems",
    "API design",
    "machine learning",
    "natural language processing",
    "retrieval augmented generation",
    "multi-agent coordination",
    "observability",
    "request tracing",
]

TEMPLATES = [
    "When working with {topic}, engineers must consider {a} and {b}.",
    "The relationship between {topic} and {a} affects {b} significantly.",
    "Modern systems implementing {topic} often rely on {a} for {b}.",
    "Understanding {topic} requires deep knowledge of {a} and {b}.",
    "Production deployments of {topic} need careful attention to {a}, particularly when {b} is involved.",
    "Teams adopting {topic} typically encounter trade-offs between {a} and {b} during initial rollout.",
    "The {topic} pattern works best when {a} is acceptable but {b} is the primary concern.",
]

CONCEPTS = [
    "latency",
    "throughput",
    "consistency",
    "availability",
    "partition tolerance",
    "idempotency",
    "ordering guarantees",
    "back-pressure",
    "fan-out",
    "caching",
    "schema design",
    "index selection",
    "query planning",
    "memory management",
    "garbage collection",
    "connection pooling",
    "batch processing",
    "retry semantics",
    "dead-letter handling",
    "audit trails",
    "tenant",
]
