# Notebooks

This folder contains Jupyter notebooks that demonstrate how to build AI applications, agents, and systems using Oracle AI Database and OCI services. These notebooks provide hands-on tutorials, examples, and best practices for developers working with Oracle's AI capabilities.

## Contents

The notebooks cover various aspects of AI development including:

- **Memory Engineering**: Building persistent memory systems for AI agents
- **Context Engineering**: Managing LLM context windows efficiently
- **RAG (Retrieval Augmented Generation)**: Building semantic search and RAG applications
- **AI Agents**: Creating intelligent agents that interact with Oracle AI Database
- **Vector Search**: Implementing vector similarity search and embeddings
- **Evaluation & Metrics**: Measuring and evaluating AI system performance

## Notebooks

| Title                                      | Stack                                                                   | Use Case                                                                                                                                                                                                                                                                                                                | Notebook                                                                                                                                                                                                                 |
| ------------------------------------------ | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Memory & Context Engineering for AI Agents | LangChain, Oracle AI Database, OpenAI, Tavily                           | Build AI agents with 6 types of persistent memory. Covers memory engineering, context window management, and just-in-time retrieval patterns.                                                                                                                                                                           | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/memory_context_engineering_agents.ipynb) |
| Oracle RAG Agents: Zero to Hero            | Oracle AI Database, OpenAI, OpenAI Agents SDK                           | Learn to build RAG agents from scratch using Oracle AI Database.                                                                                                                                                                                                                                                        | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./oracle_rag_agents_zero_to_hero.ipynb)                                                                                        |
| Oracle RAG with Evaluations                | Oracle AI Database, OpenAI, BEIR, Galileo                               | Build RAG systems with comprehensive evaluation metrics.                                                                                                                                                                                                                                                                | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./oracle_rag_with_evals.ipynb)                                                                                                 |
| Oracle Data Migration Harness Walkthrough  | Oracle AI Database 26ai, MongoDB, FastAPI, React, sentence-transformers | Walk through a MongoDB-to-Oracle AI Database migration harness with vector parity, verification, and JSON Relational Duality.                                                                                                                                                                                           | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./oracle_data_migration_harness_walkthrough.ipynb)                                                                             |
| Memory Loop Deep Dive                      | Oracle AI Database 26ai, ONNX (all-MiniLM-L12-v2), python-oracledb      | Dissect every query the memory-system CLI app issues — hybrid vector + lexical retrieval, the promotion gate, and the full turn loop. Imports the `memory/` package from `apps/rag-to-memory-systems-demo/`; run that app's setup (`memory.ddl setup`, `memory.onnx_loader`, `data.seed`) from the app directory first. | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./memory_loop_deep_dive.ipynb)                                                                                                 |

## Subfolders

Related notebooks are grouped into their own folders, each with a dedicated README:

| Folder                                          | What's inside                                                                                                                                                                                                                                                                                  |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`agent_memory/`](./agent_memory)               | Notebooks built on the **[Oracle AI Agent Memory](https://www.oracle.com/database/ai-agent-memory/)** package (`oracleagentmemory`) — the developer guide, benchmarks vs. naive memory, and framework examples (OpenAI Agents SDK, Claude Agent SDK, LangGraph).                               |
| [`langchain_ecosystem/`](./langchain_ecosystem) | Notebooks built on the **LangChain ecosystem** (LangChain, LangGraph, Deep Agents) with Oracle's `langchain-oracledb` / `langgraph-oracledb` / `langchain-oci` integrations — a RAG starter, semantic cache + chat history, a Deep Agents research agent, and a multi-agent triage supervisor. |
| [`multicloud/`](./multicloud)                   | AWS, Azure, Google Cloud, and MongoDB API samples running Oracle AI Database outside OCI.                                                                                                                                                                                                      |
| [`vecdb/`](./vecdb)                             | AI Database vector development notebooks, including auto-embedding, BYOV, semantic search, indexing, bulk loading, OCI embeddings, Gemini RAG, parks search, and Private AI Services Container integration.                                                                                 |

## Getting Started

1. Ensure you have Jupyter Notebook or JupyterLab installed
2. Install required dependencies (each notebook includes installation instructions)
3. Set up Oracle AI Database (local Docker installation or cloud instance)
4. Open the notebook and follow along with the tutorial

## Prerequisites

- Python 3.8+
- Oracle AI Database (26ai) - Free tier available via Docker
- Jupyter Notebook or JupyterLab
- Required Python packages (specified in each notebook)

## Contributing

If you'd like to contribute a notebook, please ensure it:

- Includes clear documentation and explanations
- Uses Oracle AI Database or OCI services
- Follows best practices for AI/ML development
- Includes installation and setup instructions
