# Oracle Agent Memory Workshop

**Build memory-aware AI agents with Oracle AI Database, LangChain, and Tavily**

---

## What You Will Build

A **Research Paper Assistant** — an AI agent that searches, retrieves, and reasons over arxiv papers stored as vectors in Oracle AI Database. Along the way you'll implement a `MemoryManager` with six memory types, context engineering techniques that prevent context window overflow, and a turn-level agent harness — finishing with a before/after comparison that makes the impact of memory engineering visible.

## Workshop Parts

| Part | Topic                                              | Guide                                              |
| ---- | -------------------------------------------------- | -------------------------------------------------- |
| 1    | Oracle AI Database setup and connection            | [Part 1 Guide](docs/part-1-oracle-setup.md)        |
| 2    | Vector search with LangChain OracleVS              | [Part 2 Guide](docs/part-2-vector-search.md)       |
| 3    | Memory engineering: 6 memory types in Oracle       | [Part 3 Guide](docs/part-3-memory-engineering.md)  |
| 4    | Context engineering: summarisation and offloading  | [Part 4 Guide](docs/part-4-context-engineering.md) |
| 5    | Web access with Tavily                             | [Part 5 Guide](docs/part-5-web-search.md)          |
| 6    | Agent execution and memory vs no-memory comparison | [Part 6 Guide](docs/part-6-agent-execution.md)     |

> **[TODO Checklist](docs/TODO-checklist.md)** — all 16 tasks at a glance with links to their guide sections.

## Getting Started

This workshop lives inside the [oracle-ai-developer-hub](https://github.com/oracle-devrel/oracle-ai-developer-hub) repository. Use **git sparse-checkout** to pull just this workshop without cloning the rest of the hub:

```bash
# Clone the hub with no files and no blobs
git clone --filter=blob:none --no-checkout https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub

# Enable sparse-checkout and select only this workshop
git sparse-checkout init --cone
git sparse-checkout set workshops/agent_memory_workshop

# Materialise the files and move into the workshop
git checkout main
cd workshops/agent_memory_workshop

# Start Oracle AI Database
docker compose -f .devcontainer/docker-compose.yml up -d oracle

# Install dependencies
pip install -r requirements.txt

# Launch Jupyter
jupyter lab workshop/notebook_student.ipynb
```

Wait approximately 2 minutes for Oracle to initialise before running notebook cells.

> **Updating later:** `git pull` from inside `oracle-ai-developer-hub` refreshes only the paths you've selected with sparse-checkout.

## Workshop Files

```
agent-memory-workshop/
├── .devcontainer/
│   ├── devcontainer.json        Codespaces configuration
│   ├── docker-compose.yml       Oracle AI Database + workshop container
│   ├── setup_build.sh           Build-time dependency installation
│   ├── setup_runtime.sh         Runtime Oracle health check and setup
│   ├── start_oracle.sh          Oracle startup script
│   └── oracle-init/
│       └── 01_vector_memory.sql Vector memory schema init
├── workshop/
│   ├── notebook_student.ipynb   Your working notebook (contains TODO gaps)
│   └── notebook_complete.ipynb  Complete reference (do not open until done)
├── docs/
│   ├── part-1-oracle-setup.md
│   ├── part-2-vector-search.md
│   ├── part-3-memory-engineering.md
│   ├── part-4-context-engineering.md
│   ├── part-5-web-search.md
│   ├── part-6-agent-execution.md
│   ├── TODO-checklist.md        All 16 tasks at a glance
│   └── troubleshooting.md       Common issues and solutions
├── images/                      Screenshots and architecture diagrams
└── README.md
```

## Stack

- Oracle AI Database via `gvenzl/oracle-free`
- `langchain-oracledb` — LangChain integration for Oracle vector store
- `sentence-transformers` — local embedding model, no API key needed
- `openai` — OCI GenAI (xAI Grok 3 Fast) via OpenAI-compatible endpoint
- `tavily-python` — web search for agents
- `oracledb` — Python Oracle driver

## Where to Next?

- **[Agent Memory: Building Memory-Aware Agents](https://www.deeplearning.ai/short-courses/agent-memory-building-memory-aware-agents/)** — DeepLearning.AI short course for deeper exploration of agent memory patterns
- **[Oracle AI Developer Hub](https://github.com/oracle-devrel/oracle-ai-developer-hub)** — More technical assets, samples, and projects with Oracle AI
- **[Oracle Developer Resource](https://www.oracle.com/developer/)** — Documentation, tools, and community for Oracle developers

---

Built for the Oracle AI Developer Experience team.
