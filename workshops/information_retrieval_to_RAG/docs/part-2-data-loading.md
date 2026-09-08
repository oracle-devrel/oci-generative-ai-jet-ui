# Part 2: Data Loading, Preparation & Embedding Generation [Data Pipeline]

## What You Are Building

Before you can search anything, you need data in a searchable form. In this part, 200 ArXiv research papers flow through a three-stage pipeline:

1. **Stream** papers from Hugging Face without downloading the full dataset
2. **Clean** and structure the data into a DataFrame
3. **Embed** each paper into a 768-dimensional vector using a local model

The output is a DataFrame with one row per paper, each carrying its text, metadata, and a vector embedding ready for Oracle ingestion in Part 3.

## Data Loading From Hugging Face

We use `load_dataset` from the `datasets` library with `streaming=True` to avoid downloading the entire dataset into memory. This lets you work with large datasets efficiently — you pull only what you need.

**Key points:**

- The dataset is `nick007x/arxiv-papers`
- We extract: `arxiv_id`, `title`, `abstract`, `authors`, and a combined `text` field
- Authors are normalised to a list of strings regardless of input format

**Why streaming?** The full ArXiv dataset is large. Streaming lets you iterate through records one at a time and stop after 200 — no disk space wasted, no memory pressure.

## The Embedding Model

We use the **nomic-ai/nomic-embed-text-v1.5** model from sentence-transformers. This is a 768-dimensional model that runs locally — no API key required.

**Important detail — the prefix scheme:** Nomic embeddings use asymmetric prefixes:

- `search_document:` for documents being indexed
- `search_query:` for queries at retrieval time

This asymmetric prefixing improves retrieval quality by signalling intent to the model. A document prefix tells the model "this is content to be found", while a query prefix tells it "this is a question seeking content". Mixing them up degrades results.

**What happens during embedding:**

1. Each document text gets prefixed with `search_document:`
2. The model encodes each text into a 768-dimensional normalised vector
3. Embeddings are stored as `float32` lists in the DataFrame

The resulting dimension (768) determines the `VECTOR` column size in Oracle.

> **The first time this cell runs it downloads the model weights (~550MB).** This can take 2-5 minutes in Codespaces. The model is cached after the first download so subsequent runs are instant.

## No TODOs in This Part

This section is pre-built. Read through the code to understand how data flows from Hugging Face through embedding and into a DataFrame ready for Oracle ingestion.
