---
title: Developer assistant architecture
source: assistant-architecture
category: application
product: Node.js TypeScript
priority: high
audience: architect
tags: react, hono, rag, assistant
---

# Developer assistant architecture

The assistant is a runnable Node.js and TypeScript application. The browser UI calls a Hono API, the API runs a LangChain.js retrieval workflow, and Oracle AI Database stores the vector table.

## Frontend

The React UI lets a developer ask a question, choose top K, select a metadata category, compare retrieval modes, and inspect the chunks used to build the answer.

## API

The Hono API exposes status, corpus, inspect, seed, reset, and ask endpoints. It loads `.env` from the project root so the API works when started from a pnpm workspace package.

## Core workflow

The core package creates LangChain `Document` objects from markdown knowledge-base files, embeds chunks, stores them with OracleVS, retrieves relevant chunks, and builds a grounded answer.

## Oracle inspector

The inspector connects the LangChain.js workflow to Oracle AI Database by showing table name, row count, columns, indexes, and representative vector-search SQL.
