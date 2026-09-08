# Agent Communication Matrix - Jupyter Notebooks

Interactive notebooks for demonstrating the agent communication patterns and benchmarks.

## Quick Start

1. **Install dependencies** (add to your requirements.txt):

   ```bash
   pip install jupyter ipykernel scikit-learn matplotlib
   ```

2. **Start Jupyter**:

   ```bash
   jupyter notebook
   ```

3. **Ensure services are running**:
   - Oracle database: `docker compose up -d`
   - Ollama: Running on `http://localhost:11434`

## Notebooks Overview

### [01-setup-and-data-loading.ipynb](01-setup-and-data-loading.ipynb)

**Purpose**: Initialize the demo environment and verify all connections.

**What you'll do**:

- Connect to Oracle database
- Verify vector table schema
- Load sample chunks from `data/chunks.txt`
- Display schema and record counts

**Prerequisites**: Oracle running, .env configured

**Run this first** to confirm everything is set up.

---

### [02-embedding-pipeline.ipynb](02-embedding-pipeline.ipynb)

**Purpose**: Demonstrate the embedding generation process (Pattern 1 core).

**What you'll do**:

- Connect to Ollama
- Generate embeddings for sample texts
- Measure embedding latency
- Analyze embedding statistics
- Demonstrate batch processing

**Key metrics**:

- Single embedding: ~14ms
- Batch efficiency: Demonstrates scaling

---

### [03-vector-search-demo.ipynb](03-vector-search-demo.ipynb)

**Purpose**: Show end-to-end vector search workflow.

**What you'll do**:

- Run semantic queries
- Measure embedding + search time breakdown
- Display matched results
- Visualize latency analysis

**Key insight**: Embedding dominates (14ms) vs search (0.9ms)

---

### [04-pattern-comparison.ipynb](04-pattern-comparison.ipynb)

**Purpose**: Compare token efficiency between Pattern 1 and Pattern 2.

**What you'll do**:

- Count tokens for naive payload approach
- Count tokens for payload-by-reference approach
- Calculate reduction factors
- Visualize savings across payload sizes

**Key result**: 22.9x reduction at 3KB payloads

---

### [05-benchmarks-visualization.ipynb](05-benchmarks-visualization.ipynb)

**Purpose**: Visualize all benchmark results from `benchmarks.md`.

**What you'll do**:

- Display latency breakdown (embedding vs search)
- Show token reduction curve
- Provide recommendations for pattern usage
- Interactive charts and analysis

**Best for**: Presenting findings to others

---

## Workflow Suggestions

### Demo Flow (30 minutes)

1. **[01]** Show setup works (2 min)
2. **[02]** Run embedding demo (5 min)
3. **[03]** Run vector search (5 min)
4. **[04]** Show token comparison (10 min)
5. **[05]** Present benchmarks (8 min)

### Development Flow

1. **[01]** Verify setup before any changes
2. **[02]** Test embedding performance after Ollama updates
3. **[03]** Validate vector search accuracy
4. **[04]** Compare token efficiency of changes
5. **[05]** Document results

### Benchmarking Flow

1. Run all notebooks in sequence
2. Run `pattern1/benchmark.py` and `pattern2/measure_tokens.py` separately
3. Update `benchmarks.md` with new results
4. Re-run [05] to visualize new data

## Environment Setup

Create a `.env` file in the project root:

```bash
# Oracle Database
DB_USER=admin
DB_PASSWORD=<your_password>
DB_HOST=localhost
DB_PORT=1521
DB_SERVICE=FREEPDB1

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text
```

## Dependencies

These notebooks require:

- `oracledb` - Oracle database driver
- `tiktoken` - Token counting (cl100k_base for GPT-4)
- `requests` - HTTP calls to Ollama
- `scikit-learn` - Cosine similarity calculation
- `pandas` - Data manipulation
- `matplotlib` - Visualization
- `numpy` - Numerical operations

All are in `requirements.txt` except `jupyter` and `scikit-learn` (add these).

## Troubleshooting

**Oracle Connection Failed**

- Verify `docker compose` is running
- Check `.env` credentials
- Look at `docker compose logs oracle-db`

**Ollama Connection Failed**

- Verify Ollama is running locally
- Check port is 11434 (or update .env)
- Verify model exists: `curl http://localhost:11434/api/tags`

**Embedding Generation Slow**

- Check if GPU is being used (watch `nvidia-smi`)
- On CPU-only, expect 5-20x slower latency
- Consider using a smaller model

**Token Counting Off**

- Verify you're using `cl100k_base` tokenizer
- Check tiktoken version matches GPT-4
- Alternative tokenizers: `o200k_base` (GPT-4o)

## Customization

### Add More Queries

Edit `03-vector-search-demo.ipynb`:

```python
queries = [
    "your custom query 1",
    "your custom query 2",
]
```

### Change Payload Sizes

Edit `04-pattern-comparison.ipynb`:

```python
payload_sizes = {
    '100 chars': sample_finding[:100],
    '5K chars': sample_finding * 10,
}
```

### Adjust Benchmark Parameters

Edit visualization notebooks to use different metrics from `benchmarks.md`.

## Next Steps

1. Run through all notebooks in order
2. Modify queries and payloads to match your use cases
3. Share results/visualizations from [05]
4. Use as foundation for your own analysis

## Integration with Scripts

These notebooks complement:

- `pattern1/benchmark.py` - Raw latency measurements
- `pattern2/measure_tokens.py` - Token counting
- `scripts/generate_synthetic_corpus.py` - Data generation
- `scripts/load_corpus.py` - Database loading

Run these scripts first, then visualize results in notebooks.
