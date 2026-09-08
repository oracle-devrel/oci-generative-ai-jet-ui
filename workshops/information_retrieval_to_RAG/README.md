# Information Retrieval to RAG Workshop

**Build a complete information retrieval and RAG pipeline with Oracle AI Database and OCI GenAI (xAI Grok 3 Fast)**

---

## What You Will Build

Starting from raw data, you will construct a **Research Paper Assistant** — a system that retrieves and reasons over 200 ArXiv papers stored in Oracle AI Database. Along the way you'll implement five retrieval strategies (keyword, vector, hybrid, and graph) and build an end-to-end RAG pipeline that connects Oracle retrieval to OCI GenAI (xAI Grok 3 Fast).

## Workshop Parts

| Part | Topic                                                 | Guide                                       |
| ---- | ----------------------------------------------------- | ------------------------------------------- |
| 1    | Oracle AI Database setup and connection               | [Part 1 Guide](docs/part-1-oracle-setup.md) |
| 2    | Data loading and embedding generation                 | [Part 2 Guide](docs/part-2-data-loading.md) |
| 3    | Database table setup and data ingestion               | [Part 3 Guide](docs/part-3-table-setup.md)  |
| 4    | Retrieval mechanisms (keyword, vector, hybrid, graph) | [Part 4 Guide](docs/part-4-retrieval.md)    |
| 5    | Building a RAG pipeline                               | [Part 5 Guide](docs/part-5-rag-pipeline.md) |

> **[TODO Checklist](docs/TODO-checklist.md)** — all 7 tasks at a glance with links to their guide sections.

## Getting Started

This workshop lives inside the [oracle-ai-developer-hub](https://github.com/oracle-devrel/oracle-ai-developer-hub) repository. Use **git sparse-checkout** to pull just this workshop without cloning the rest of the hub:

```bash
# Clone the hub with no files and no blobs
git clone --filter=blob:none --no-checkout https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub

# Enable sparse-checkout and select only this workshop
git sparse-checkout init --cone
git sparse-checkout set workshops/information_retrieval_to_RAG

# Materialise the files and move into the workshop
git checkout main
cd workshops/information_retrieval_to_RAG

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
information_retrieval_to_RAG/
├── .devcontainer/
│   ├── devcontainer.json       Codespaces configuration
│   ├── docker-compose.yml      Oracle AI Database container
│   ├── setup_build.sh          Dependency installation and kernel registration
│   ├── setup_runtime.sh        Oracle startup and vector memory configuration
│   ├── start_oracle.sh         Oracle health check on Codespace restart
│   └── oracle-init/
│       └── 01_vector_memory.sql  Vector memory pool initialisation
├── workshop/
│   ├── notebook_student.ipynb    Your working notebook (contains TODO gaps)
│   └── notebook_complete.ipynb   Complete reference (do not open until done)
├── docs/
│   ├── part-1-oracle-setup.md
│   ├── part-2-data-loading.md
│   ├── part-3-table-setup.md
│   ├── part-4-retrieval.md
│   ├── part-5-rag-pipeline.md
│   └── TODO-checklist.md
├── images/
├── requirements.txt
└── README.md
```

## Stack

- Oracle AI Database via `gvenzl/oracle-free:23-full`
- `sentence-transformers` — local embedding model (nomic-embed-text-v1.5, 768-dim), no API key needed
- `oracledb` — Python Oracle driver
- `OCI GenAI` — LLM generation (xAI Grok 3 Fast via OpenAI-compatible endpoint)

## Where to Next?

- **[From RAG to Agents Workshop](https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/workshops/from_rag_to_agents_workshop)** — Continue the journey by adding AI agents, multi-agent orchestration, and persistent session memory on top of this RAG pipeline
- **[Oracle AI Developer Hub](https://github.com/oracle-devrel/oracle-ai-developer-hub)** — More technical assets, samples, and projects with Oracle AI
- **[Oracle Developer Resource](https://www.oracle.com/developer/)** — Documentation, tools, and community for Oracle developers

---

Built for the Oracle AI Developer Experience team.
