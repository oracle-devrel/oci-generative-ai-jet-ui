# Agent Harness

End-to-end notebooks that construct a production-grade agent _harness_ on Oracle AI Database 26ai. An agent harness is everything around the model — memory, retrieval, tool dispatch, identity, budgets — built here from Oracle primitives (OAMP, in-DB ONNX embeddings, HNSW + Oracle Text, MLE, DBFS, Duality Views, DDS) running on a single local container.

## Contents

| Content                                                                              | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Open                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`enterprise_data_agent_heavyweight.ipynb`](enterprise_data_agent_heavyweight.ipynb) | Full build on a local Oracle AI Database 26ai container. Walks through DSN + dedicated `AGENT` user, in-database ONNX embeddings + HNSW indexes, cross-encoder reranking, hybrid vector + Oracle Text retrieval fused via RRF, vector-indexed `toolbox` and `skillbox` registries, a DBFS scratchpad with a `UTL_TO_TEXT` / `UTL_TO_CHUNKS` promotion path to OAMP, sandboxed JavaScript via Oracle MLE, the agent loop, JSON Relational Duality Views, `DBMS_SCHEDULER`-driven re-scans, and identity-aware authorization via Deep Data Security (DDS).                                                                                                                                                                                                                                                            | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_harness/enterprise_data_agent_heavyweight.ipynb) |
| [`total_recall_agent_harness.ipynb`](total_recall_agent_harness.ipynb)               | Self-improving agent harness built layer-by-layer (Parts 0–10) on a single local Oracle AI Database 26ai. Cognitive memory via the Oracle AI Agent Memory package (OAMP) with an in-database ONNX embedder — episodic threads, semantic facts, working summaries, and the **context card**; scratch → long-term promotion on a `DBMS_SCHEDULER` schedule; a schema **semantic layer**; `SKILL.md` skills (continual learning in token space) plus agent-built automations via tool-calling; a typed LangGraph agent loop with durable, resumable state through the langgraph-oracledb `OracleSaver` checkpointer; **flat context** via compaction (the context card) + substrate-aware offloading; and `agent_tools` / `agent_skills` registries searched by **HNSW**. Verified end-to-end against a live database. | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_harness/total_recall_agent_harness.ipynb)        |

## Layout

```
agent_harness/
├── README.md
├── enterprise_data_agent_heavyweight.ipynb
├── total_recall_agent_harness.ipynb   # diagrams embedded inline (base64); no asset folder needed
└── images/        # diagrams referenced inline by enterprise_data_agent_heavyweight.ipynb
    ├── cover-oracle-native-arch.png
    ├── cover-oracle-reference-arch.png
    ├── cover-duality-view.png
    ├── cover-skillbox-flow.png
    ├── cover-toolbox-flow.png
    ├── oamp_memory_discpline.png
    ├── oamp_breakdown.png
    ├── dual_memory_substrate.png
    └── ingestion-pipeline.png
```
