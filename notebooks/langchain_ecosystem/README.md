# LangChain Ecosystem

[![LangChain](https://img.shields.io/badge/Built%20with-LangChain%20%2B%20LangGraph-1C3C3C?style=flat-square)](https://www.langchain.com/) [![Oracle AI Database](https://img.shields.io/badge/Oracle-AI%20Database%2026ai-C74634?style=flat-square&logo=oracle)](https://www.oracle.com/database/)

A collection of notebooks that build AI applications and agents with the **LangChain ecosystem** — LangChain, LangGraph, Deep Agents, and Oracle's first-party integrations (`langchain-oracledb`, `langgraph-oracledb`, `langchain-oci`) — using **Oracle AI Database** as the single backend for vectors, agent memory, checkpoints, the LLM cache, and chat history.

The theme of the folder is convergence: instead of stitching a vector database, a key-value store, a checkpoint file, and a chat log into one agent, every notebook here keeps all of that state in **one converged database**.

## The stack

Every notebook follows the same shape:

| Layer                     | Typical component                                                                                   | Role                                                                                            |
| ------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| **Python**                | the notebook runtime                                                                                | the glue                                                                                        |
| **LLM provider**          | `ChatAnthropic` (Claude) or an OpenAI chat model                                                    | the reasoning engine that plans, calls tools, and synthesizes answers                           |
| **LangChain / LangGraph** | `langchain`, `langgraph`, `deepagents`, `langchain-oracledb`, `langgraph-oracledb`, `langchain-oci` | the orchestration fabric and the Oracle-backed persistence primitives                           |
| **Oracle**                | Oracle AI Database 23ai / 26ai                                                                      | one converged store for vectors, long-term memory, checkpoints, the LLM cache, and chat history |

Embeddings are a **pluggable vectorizer** — **OpenAI** `text-embedding-3-small` or a local **HuggingFace** model, depending on the notebook. Each notebook names its own model choices.

## The Oracle × LangChain primitives these notebooks use

| Primitive                          | Package              | What it does                                                           |
| ---------------------------------- | -------------------- | ---------------------------------------------------------------------- |
| `OracleVS`                         | `langchain-oracledb` | LangChain vector store backed by Oracle AI Vector Search               |
| `OracleEmbeddings`                 | `langchain-oracledb` | generate embeddings **inside** the database from an ONNX model         |
| `create_text_index`                | `langchain-oracledb` | Oracle **Text** keyword index for hybrid (vector + lexical) search     |
| `OracleSemanticCache`              | `langchain-oracledb` | reuse an LLM answer when a new prompt is _semantically_ equivalent     |
| `OracleChatMessageHistory`         | `langchain-oracledb` | durable, `session_id`-scoped chat transcripts                          |
| `OracleStore` / `AsyncOracleStore` | `langgraph-oracledb` | long-term, cross-thread agent memory                                   |
| `OracleSaver` / `AsyncOracleSaver` | `langgraph-oracledb` | per-thread short-term checkpoints (resume a conversation)              |
| `create_deepagents_agent`          | `langchain-oci`      | Deep Agents factory that auto-wires Oracle datastores into agent tools |

## Notebooks

| #   | Name                                | Description                                                                                                                                                                                                                                                                                                                                                                                     | Stack                                                                                                                         | Open Notebook                                                                                                                                   | Open in Colab                                                                                                                                                                                                                                           |
| --- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 01  | **RAG with Oracle & LangChain**     | The starter: build a minimal RAG application on Oracle AI Vector Search with `OracleVS` and LangChain — ingest documents, embed them, and answer questions grounded in the retrieved chunks.                                                                                                                                                                                                    | Oracle AI Database · langchain-oracledb · HuggingFace                                                                         | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./oracle_langchain_example.ipynb)                     | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/langchain_ecosystem/oracle_langchain_example.ipynb)                     |
| 02  | **Semantic Cache + Chat History**   | Two `langchain-oracledb` primitives for cheaper, coherent apps: `OracleSemanticCache` reuses an answer when a new question _means_ the same as a past one, and `OracleChatMessageHistory` persists durable, session-scoped transcripts. Includes calibrating the cache's distance threshold to the embedding model.                                                                             | langchain-oracledb · OpenAI (embeddings) · Anthropic                                                                          | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./langchain_oracle_semantic_cache_chat_history.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/langchain_ecosystem/langchain_oracle_semantic_cache_chat_history.ipynb) |
| 03  | **Research Agent with Deep Agents** | A durable research agent built with the released `langchain_oci.create_deepagents_agent` factory. Oracle backs the hybrid-search corpus (`ADB`), per-thread checkpoints (`OracleSaver`), long-term notes (`OracleStore`), and the agent's virtual filesystem (`StoreBackend`) — while Claude reasons and plans.                                                                                 | langchain-oci (deepagents) · Anthropic · HuggingFace · langgraph-oracledb · Oracle AI Database                                | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./research_agent_with_deepagents_oracle.ipynb)        | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/langchain_ecosystem/research_agent_with_deepagents_oracle.ipynb)        |
| 04  | **AI On-Call Triage Assistant**     | The capstone: a LangGraph **supervisor** orchestrates two specialists (`issue_analyst`, `policy_agent`) to triage incoming issues. Vector knowledge (`OracleVS`), long-term memory (`AsyncOracleStore`), checkpoints (`AsyncOracleSaver`), a semantic LLM cache (`OracleSemanticCache`), and chat history all share **one** Oracle AI Database. Runs on Claude Opus 4.8 with adaptive thinking. | langchain · langgraph · langgraph-supervisor · langchain-oracledb · langgraph-oracledb · Anthropic (Claude Opus 4.8) · OpenAI | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./ai_oncall_triage_langchain.ipynb)                   | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/langchain_ecosystem/ai_oncall_triage_langchain.ipynb)                   |

## Recommended reading order

The notebooks build on each other from a starter app to a full multi-agent system:

1. **RAG with Oracle & LangChain (01)** — learn the base pattern: `OracleVS`, embeddings, retrieval.
2. **Semantic Cache + Chat History (02)** — add the two primitives that make an app cheap to run and coherent over time.
3. **Research Agent with Deep Agents (03)** — graduate to an autonomous, planning agent whose memory lives in Oracle.
4. **AI On-Call Triage Assistant (04)** — put it all together: a multi-agent supervisor over five kinds of Oracle-backed state.

## Prerequisites

- An **Oracle AI Database** instance (23ai / 26ai) — either local (each notebook pins a `gvenzl/oracle-free` Docker image and includes the `docker run` command) or reachable over the network.
- **Python 3.11+** and Jupyter / JupyterLab (or open any notebook directly in Colab via the badge above).
- **API keys**, depending on the notebook: an **Anthropic** key for Claude, and/or an **OpenAI** key for `text-embedding-3-small` embeddings. Notebook 01 runs entirely on a local HuggingFace embedding model and needs no API key.
- Each notebook starts with a **single `pip install`** of the latest packages and lists exactly what it needs.
