---
title: Retrieval patterns with OracleVS
source: retrieval-patterns
category: retrieval
product: OracleVS
priority: high
audience: developer
tags: similarity, score, mmr, metadata
---

# Retrieval patterns with OracleVS

LangChain.js can retrieve from OracleVS using similarity search, similarity search with scores, metadata filters, and maximal marginal relevance.

## Similarity search with score

Use `similaritySearchWithScore(question, k, filter)` when the application should show the top chunks and their vector distances. This is useful for debugging, screenshots, and explaining why a chunk was selected.

## Metadata filters

Metadata filters restrict retrieval before ranking. A developer assistant can filter by category such as `setup`, `troubleshooting`, `retrieval`, or `production` so the answer is grounded in the right part of the knowledge base.

## Maximal marginal relevance

Use `maxMarginalRelevanceSearch` when the answer benefits from diverse context. MMR fetches more candidates, then balances relevance and diversity so the final context is less repetitive.

## Retriever transparency

A good tutorial UI should show the retrieval mode, top K, filter, source chunks, distances when available, and the final context sent into the answer step.
