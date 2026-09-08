# Workshops

Hands-on workshops and guided learning experiences that take developers from fundamentals to production patterns with Oracle AI Database. Each workshop is self-contained: a student notebook (TODO gaps to fill in), a complete reference notebook, step-by-step part guides, and an environment configuration that pre-bootstraps Oracle AI Database. Workshops progress from information retrieval and RAG, through agentic systems and orchestration, to memory-augmented agents — together they cover the full stack for building AI applications on Oracle.

> **Pull a single workshop without cloning the whole hub.** Each workshop README includes `git sparse-checkout` instructions so you can fetch only the folder you need.

## All workshops

| Name                               | Description                                                                                                                                                                                                                                                                                                                                                       | Stack                                                                                                                                     | Link                                                                                                                                |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Information Retrieval to RAG       | Build a Research Paper Assistant over 200 ArXiv papers by implementing five retrieval strategies (keyword, vector, hybrid, graph) and a full RAG pipeline wired to OCI GenAI.                                                                                                                                                                                     | Oracle AI Database, sentence-transformers, oracledb, OCI GenAI (xAI Grok 3 Fast)                                                          | [![View Workshop](https://img.shields.io/badge/View%20Workshop-purple?style=flat-square)](./information_retrieval_to_RAG)           |
| From RAG to Agents                 | Pick up where Information Retrieval to RAG leaves off — wrap the same Oracle-backed retrieval in an agentic loop (planning, tool use, reflection) using the OpenAI Agents SDK.                                                                                                                                                                                    | Oracle AI Database, OpenAI Agents SDK, OpenAI                                                                                             | [![View Workshop](https://img.shields.io/badge/View%20Workshop-purple?style=flat-square)](./from_rag_to_agents_workshop)            |
| Agent Memory                       | Build memory-aware AI agents on Oracle AI Database with LangChain and Tavily — short-term session memory, durable semantic memory, and live web search threaded through a single agent loop.                                                                                                                                                                      | Oracle AI Database, LangChain, Tavily                                                                                                     | [![View Workshop](https://img.shields.io/badge/View%20Workshop-purple?style=flat-square)](./agent_memory_workshop)                  |
| Enterprise Data Agent Harness      | Build a memory-aware enterprise data agent on Oracle AI Database 26ai with OAMP, hybrid vector + Oracle Text retrieval, JSON Relational Duality Views, Deep Data Security, and `DBMS_SCHEDULER` — then see it running in a live Flask + React chat UI.                                                                                                            | Oracle AI Database 26ai, OAMP, langchain-oracledb, OCI GenAI, Flask, React                                                                | [![View Workshop](https://img.shields.io/badge/View%20Workshop-purple?style=flat-square)](./enterprise-data-agent-harness-workshop) |
| Soccer Analytics Agent             | Build a FIFA World Cup analytics agent that combines Oracle-backed working/episodic/semantic memory, LangChain OracleVS hybrid retrieval, LangGraph OracleDB observability, and a 92-feature XGBoost prediction pipeline exposed through FastAPI + React.                                        | Oracle AI Database, langchain-oracledb, langgraph-oracledb, XGBoost, FastAPI, React, OCI GenAI (Grok 4)                                  | [![View Workshop](https://img.shields.io/badge/View%20Workshop-purple?style=flat-square)](./soccer-analytics-agent)                |
| Supply-Chain Demand Planning Agent | Build a multi-agent demand-planning assistant on Oracle AI Database with a LangGraph supervisor over two specialists; vector knowledge, long-term cross-thread memory, per-thread checkpoints, semantic LLM cache, and chat history all share one Oracle. In-database ONNX embeddings, plus a live chat app with per-agent context and an animated topology view. | Oracle AI Database, langchain-oracledb, langgraph-oracledb, langgraph-supervisor, FastAPI, React, OCI GenAI (xAI Grok 4.1 Fast Reasoning) | [![View Workshop](https://img.shields.io/badge/View%20Workshop-purple?style=flat-square)](./supplychain_demand_agent_workshop)      |

## How a workshop is organised

Each workshop folder typically contains:

```
workshops/<workshop-name>/
├── README.md                       sparse-checkout snippet, parts table, getting started
├── workshop/                       student + complete notebooks
│   ├── notebook_student.ipynb         TODO stubs + hard-stop asserts
│   └── notebook_complete.ipynb        reference solutions
├── docs/                           per-part guides + TODO checklist + troubleshooting
├── images/                         architecture diagrams + screenshots
├── app/                            (some workshops) a chat app that demos the wired primitives
└── requirements.txt                Python deps for the workshop
```

## Recommended reading order

If you're new to Oracle AI Database, work through these in order:

1. **Information Retrieval to RAG** — foundational retrieval strategies + your first RAG pipeline
2. **From RAG to Agents** — wrap the same retrieval in an agentic loop
3. **Agent Memory** — durable memory layers that outlive a single conversation
4. **Enterprise Data Agent Harness** — production-shape harness with identity-aware access, duality views, and a live UI
5. **Supply-Chain Demand Planning Agent** — multi-agent orchestration with a supervisor + specialists, every primitive in one database
6. **Soccer Analytics Agent** — end-to-end sports analytics agent with Oracle memory, hybrid retrieval, observability, and ML predictions

Each workshop is independent — feel free to jump to whichever one matches the pattern you're building right now.
