# Agent Memory

[![Documentation](https://img.shields.io/badge/Documentation-Oracle%20AI%20Agent%20Memory-red?style=flat-square)](https://www.oracle.com/database/ai-agent-memory/)

A collection of notebooks demonstrating how to build memory-augmented AI agents on top of **Oracle AI Database** as the **unified memory core** for AI agents.

## What is Agent Memory?

Agent memory is what separates a stateless LLM call from an agent that learns, adapts, and stays coherent across turns, sessions, and runs. It is the substrate that lets an agent:

- **Recall** prior conversations and reuse what was already said or decided
- **Remember** durable facts about users, entities, tools, and the world
- **Reason** over its own past behavior — what it tried, what worked, what failed
- **Resume** workflows after a crash, restart, or hand-off — without losing state

Practical agent memory is rarely a single store. It is a small set of access patterns layered over the same backend:

| Memory type                      | What it holds                                  | Typical access pattern  |
| -------------------------------- | ---------------------------------------------- | ----------------------- |
| **Conversation / thread memory** | Turn-by-turn dialogue history for a single run | Append + ordered read   |
| **Episodic memory**              | Discrete events the agent participated in      | Time-ranged search      |
| **Semantic memory**              | Durable facts and learned knowledge            | Vector + keyword search |
| **Procedural memory**            | How-to knowledge, routines, tool-use patterns  | Lookup by task          |
| **Working memory**               | Scratchpad for the current step                | Read/write within a run |
| **Entity memory**                | Facts scoped to a user, customer, or object    | Scoped queries          |

## Oracle AI Database — the unified memory core

**Oracle AI Database is the unified memory core for AI agents.** Rather than stitching together a vector DB, a key-value store, a graph DB, and a relational store — each with its own client, consistency model, and ops surface — Oracle AI Database serves all of these access patterns from a single converged engine:

- **Vector search** for semantic recall and retrieval-augmented generation
- **Relational queries** for structured agent state and audit trails
- **JSON / document** for flexible message and tool-call payloads
- **Graph** for relationships between entities, sessions, and findings
- **Spatial and full-text** for richer retrieval over the same memories

The notebooks in this folder use the [`oracleagentmemory`](https://www.oracle.com/database/ai-agent-memory/) (OAMP) Python package, which is the AI-Agent Memory Package built on top of Oracle AI Database. OAMP wraps the database as a memory backend with a consistent API for **users / agents**, **memories**, and **threads** — the three primitives behind every notebook in this folder.

## Notebooks

| #   | Name                       | Description                                                                                                                                                                                                                                                                                                                                                                                                                           | Framework                         | Open Notebook                                                                                                                          | Open in Colab                                                                                                                                                                                                                           |
| --- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 01  | Deep Research Agent        | Build a deep research agent for human genome exploration that uses Tavily for live web search and stores running conversation + durable findings in Oracle AI Database. Demonstrates the OpenAI Agents SDK `Session` protocol implemented against an Oracle-backed memory store.                                                                                                                                                      | OpenAI Agents SDK · Tavily · OAMP | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./01_deep_research_openai_agents.ipynb)      | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/01_deep_research_openai_agents.ipynb)      |
| 02  | Supply Chain Assistant     | A supply chain assistant that tracks and updates shipment cargo through in-process tools and an MCP server. Uses Oracle AI Agent Memory to persist shipment records, operational notes, and conversation history across restarts.                                                                                                                                                                                                     | Claude Agent SDK · MCP · OAMP     | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./02_supply_chain_claude_agent_sdk.ipynb)    | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/02_supply_chain_claude_agent_sdk.ipynb)    |
| 03  | Mortgage Approval Workflow | A deterministic mortgage approval workflow modeled as a `StateGraph` with prebuilt `create_agent` nodes. Uses Oracle AI Agent Memory so a workflow that fails mid-stage can resume from the last persisted state instead of restarting.                                                                                                                                                                                               | LangGraph · OAMP                  | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./03_mortgage_workflow_langgraph.ipynb)      | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/03_mortgage_workflow_langgraph.ipynb)      |
| 04  | OAMP Benchmarks            | Quantifies the practical benefits of Oracle AI Agent Memory over naive flat-history memory along three axes: token consumption per turn, wall-clock latency, and response quality (LLM-as-a-judge). Runs the same 80-turn scripted conversation through three agents.                                                                                                                                                                 | OAMP · LiteLLM · OpenAI           | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./oracle_agent_memory_benchmarks.ipynb)      | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/oracle_agent_memory_benchmarks.ipynb)      |
| 05  | OAMP Developer Guide       | A hands-on, step-by-step guide to the `oracleagentmemory` package. Builds an agent memory system from scratch — connection, the three primitives (users/agents, memories, threads), manual vs. automatic LLM-powered extraction, vector search, context cards, and scoping.                                                                                                                                                           | OAMP · LiteLLM                    | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./oracle_agent_memory_developer_guide.ipynb) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/oracle_agent_memory_developer_guide.ipynb) |
| 06  | Support Assistant Copilot  | An end-to-end customer-support copilot that follows one damaged-delivery case from setup through knowledge ingestion, agent tool use, context-card compaction, preference correction, cross-user isolation, TTL/retention, and teardown. Demonstrates background extraction, pluggable embeddings (OpenAI by default or an in-database ONNX model), vector search, metadata inheritance and filtering, and chunked semantic indexing. | OpenAI Agents SDK · OAMP          | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./oamp_support_assistant_example.ipynb)      | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/oamp_support_assistant_example.ipynb)      |

## Getting Started

If you are new to Oracle AI Agent Memory, the recommended order is:

1. **Start with the Developer Guide (05)** — learn the API surface and the three core primitives.
2. **Run the Benchmarks (04)** — see the cost, latency, and quality differences vs. naive memory.
3. **Pick a framework example** — OpenAI Agents SDK (01), Claude Agent SDK (02), or LangGraph (03), depending on your stack.

## Prerequisites

- An **Oracle AI Database** instance — either local (Docker) or reachable over the network
- An LLM provider key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or any LiteLLM-supported provider depending on the notebook)
- Python 3.10+ with the `oracleagentmemory` package installed

## Further Reading

- [Oracle AI Agent Memory product page](https://www.oracle.com/database/ai-agent-memory/)
- [Oracle AI Database](https://www.oracle.com/database/ai-database/)
