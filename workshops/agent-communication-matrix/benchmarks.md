# Benchmark Results

Measurements captured during article reconciliation. Re-run the benchmark scripts
to verify results on your own hardware.

## Test Environment

- Hardware: Workstation with NVIDIA RTX 4090
- OS: Arch Linux
- Date: 5/18/2026
- Ollama: nomic-embed-text, 768-dim, GPU-accelerated
- Oracle: AI Database Free 26ai (23.26.1.0.0)
- Corpus: 1,000 synthetic chunks
- Index: HNSW (ORGANIZATION INMEMORY NEIGHBOR GRAPH), cosine distance

## Pattern 1: MCP Tool-Call Latency

100 measurements (20 queries × 5 runs), 3 warmup queries discarded.

| Stage                | Median  | p95     | Min     | Max     |
| -------------------- | ------- | ------- | ------- | ------- |
| Embedding (Ollama)   | 14.1 ms | 15.2 ms | 13.0 ms | 15.6 ms |
| Oracle vector search | 0.9 ms  | 0.9 ms  | 0.8 ms  | 1.0 ms  |
| Total round-trip     | 15.3 ms | 16.3 ms | --      | --      |

Embedding cost dominates: roughly 16x the vector search cost. On CPU-only
hardware, embedding typically runs 5-20x slower; vector search latency
does not change meaningfully with embedding hardware.
Ye

## Pattern 2: Token Reduction Through Payload-by-Reference

Tokenizer: cl100k_base (GPT-4 family; Anthropic and Google tokenizers
produce comparable counts for English text).

Single-message comparison at 3KB findings (typical research-agent output):

| Approach                   | Tokens | Notes                              |
| -------------------------- | ------ | ---------------------------------- |
| Naive (payload in message) | 1,394  | Findings + source refs serialized  |
| Payload-by-reference       | 61     | Memory ID only; findings in Oracle |
| Reduction                  | 22.9x  |                                    |

Size-dependency (single hop):

| Findings size | Naive tokens | By-ref tokens | Reduction |
| ------------- | ------------ | ------------- | --------- |
| 500 chars     | 341          | 61            | 5.6x      |
| 1,000 chars   | 498          | 61            | 8.2x      |
| 2,000 chars   | 919          | 61            | 15.1x     |
| 3,000 chars   | 1,355        | 61            | 22.2x     |
| 5,000 chars   | 2,237        | 61            | 36.7x     |
| 8,000 chars   | 3,591        | 61            | 58.9x     |

Compounding across mesh hops at 3KB findings:

| Hops | Naive cumulative | By-ref cumulative | Gap   |
| ---- | ---------------- | ----------------- | ----- |
| 1    | 1,394            | 61                | 1,333 |
| 2    | 2,788            | 122               | 2,666 |
| 3    | 4,182            | 183               | 3,999 |
| 5    | 6,970            | 305               | 6,665 |

The architectural claim ("the protocol carries coordination; the database
carries state") is sharpest at typical findings sizes (1KB+) and grows
with mesh depth. At small findings (<500 chars) the ratio is still
meaningful but the architectural urgency is lower.

## Pattern 3: Worker Throughput

[Optional — run pattern3/load_test.py if quantified throughput is desired]

## Reproducing These Numbers

```bash
# After docker compose up and schema initialization:
python scripts/generate_synthetic_corpus.py
python scripts/load_corpus.py
python pattern1/benchmark.py
```

Numbers will vary by hardware. The article's architectural claim
("database-fast, not LLM-fast") is robust across hardware configurations
because the embedding/search ratio is consistent — only the absolute
embedding number moves.
