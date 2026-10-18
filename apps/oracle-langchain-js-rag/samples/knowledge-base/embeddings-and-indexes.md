---
title: Embeddings and vector indexes
source: embeddings-and-indexes
category: production
product: Oracle AI Database
priority: medium
audience: architect
tags: embeddings, hnsw, ivf, production
---

# Embeddings and vector indexes

The tutorial uses deterministic demo embeddings so the sample is reproducible without paid services. Production applications can swap in OpenAI, OCI Generative AI, Oracle embeddings, or another LangChain.js embeddings implementation.

## Embedding provider choice

LangChain.js keeps the embedding provider behind the `Embeddings` interface. The OracleVS storage and retrieval flow stays the same when you change the embedding model, as long as the stored vector dimensions match the query vectors.

## Vector dimensions

The vector dimension is determined by the embedding model. Demo embeddings use a small dimension for repeatability. Production embeddings commonly use larger dimensions and should be chosen based on quality, latency, and cost.

## HNSW and IVF indexes

Vector indexes such as HNSW or IVF become important when the Oracle AI Database table grows. Small tutorials can run without an index, but larger corpora should create an index to improve retrieval latency.

## Operational note

Do not point a reset or seed script at a production table. The demo seed path can drop and recreate the configured OracleVS table.
