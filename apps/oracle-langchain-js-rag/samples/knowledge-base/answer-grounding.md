---
title: Grounded answers and source citations
source: answer-grounding
category: generation
product: LangChain.js
priority: high
audience: developer
tags: llm, grounding, citations, prompt
---

# Grounded answers and source citations

RAG applications should explain where an answer came from. The assistant should answer only from retrieved OracleVS context and show source chunks beside the response.

## Prompting

The system instruction should tell the chat model to answer only from retrieved context. If the context is insufficient, the model should say what is missing instead of guessing.

## Citations

Each retrieved chunk has metadata such as source, section, category, product, and audience. The UI can show those fields as citations and let readers verify the answer.

## Extractive fallback

When no LLM API key is configured, the app can still return an extractive grounded answer. This keeps the local tutorial runnable while making the LLM integration optional.

## Developer-friendly answers

A developer assistant should provide short explanations, concrete fix steps, TypeScript snippets when relevant, and the source chunks used to form the answer.
