---
title: OracleVS setup in a TypeScript RAG application
source: oraclevs-setup
category: setup
product: LangChain.js
priority: high
audience: developer
tags: oraclevs, setup, typescript, nodejs
---

# OracleVS setup in a TypeScript RAG application

OracleVS is the LangChain.js vector store integration for Oracle AI Database. A TypeScript application can create LangChain `Document` objects, embed them, store them in Oracle AI Database, and retrieve relevant chunks with vector search.

## Install packages

Use `@oracle/langchain-oracledb` for the Oracle vector store, `oracledb` for the database driver, `@langchain/core` for the LangChain primitives, and a model package such as `@langchain/openai` when you want generated answers.

## Configure the database

The application needs an Oracle schema with permission to create, insert, select, and drop the demo vector table. Local development can use Oracle Database Free or Oracle AI Database in a container. Autonomous Database can be used with wallet settings.

## Seed vectors

Use `OracleVS.fromDocuments(documents, embeddings, config)` to insert document text, embedding vectors, and JSON metadata into Oracle AI Database. This keeps retrieval data in the same database that can also hold operational records.

## Run retrieval

Use `similaritySearchWithScore` when the UI should show the nearest chunks and their distance values. Use metadata filters to narrow the search by category, source, audience, tenant, or product.
