# Semantic Search over GitHub Issues Workshop

**Build a working semantic search engine over real GitHub issues with Oracle AI Database 26ai and `langchain-oracledb` in 10 minutes**

---

## What You Will Build

Starting from a public GitHub repository, you will build a semantic search engine that finds bug reports by **meaning** rather than keywords. You'll pull 15 issues from the `oracle/python-oracledb` repo via the GitHub REST API, store them as vector embeddings in Oracle AI Database 26ai using `langchain-oracledb`, and run similarity queries with metadata filters. By the end you'll see why keyword search fails on the same query, how hybrid filtering combines vector ranking with structured WHERE clauses, and what the underlying `VECTOR_DISTANCE` SQL looks like.

The workshop runs entirely against [FreeSQL](https://freesql.com), Oracle's free browser-based AI Database sandbox.

## Getting Started

This workshop lives inside the [oracle-ai-developer-hub](https://github.com/oracle-devrel/oracle-ai-developer-hub) repository. Use **git sparse-checkout** to pull just this workshop without cloning the rest of the hub:

```bash
# Clone the hub with no files and no blobs
git clone --filter=blob:none --no-checkout https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub

# Enable sparse-checkout and select only this workshop
git sparse-checkout init --cone
git sparse-checkout set workshops/semantic_search_github_issues

# Materialise the files and move into the workshop
git checkout main
cd workshops/semantic_search_github_issues

# Install dependencies
pip install -r .devcontainer/requirements.txt

# Set up your FreeSQL credentials
cp .env.example .env
# Edit .env with credentials from freesql.com → Connect → Python tab

# Launch Jupyter
jupyter lab notebook.ipynb
```

> **Updating later:** `git pull` from inside `oracle-ai-developer-hub` refreshes only the paths you've selected with sparse-checkout.

## Workshop Files

```
semantic_search_github_issues/
├── .devcontainer/
│   ├── devcontainer.json       Dev container configuration
│   ├── requirements.txt        Python dependencies (pinned minimums)
│   └── cache_model.py          Pre-caches embedding model during build
├── .env.example                Credential template
├── .gitignore                  Excludes .env from commits
├── notebook.ipynb              Workshop notebook (10 cells)
└── README.md
```

## Stack

- **Oracle AI Database 26ai** via [FreeSQL](https://freesql.com) — vector storage and search, no local install
- `langchain-oracledb` — Python vector store integration
- `sentence-transformers` — local embedding model (`all-MiniLM-L6-v2`, 384-dim), no API key needed
- `python-oracledb` thin mode — pure Python Oracle driver, no client libraries to install

## What the Notebook Covers

| Cell | What it does                                                                |
| ---- | --------------------------------------------------------------------------- |
| 1    | Connect to FreeSQL via `python-oracledb` thin mode, credentials from `.env` |
| 2    | Pull 15 recent issues from `oracle/python-oracledb` via GitHub REST API     |
| 3    | Shape issues into LangChain `Document` objects with metadata                |
| 4    | Load the `all-MiniLM-L6-v2` embedding model                                 |
| 5    | `OracleVS.from_documents()` (creates table, embeds, inserts in one call)    |
| 6    | Similarity search for "connection pool errors"                              |
| 7    | Same query as a SQL `LIKE` (returns zero matches)                           |
| 8    | Hybrid filter: vector similarity + `state=open`                             |
| 9    | Behind the abstraction: raw SQL with `VECTOR_DISTANCE` and `JSON_VALUE`     |
| 10   | Cleanup (drop the demo table)                                               |

## Where to Next?

- **[Oracle AI Developer Hub](https://github.com/oracle-devrel/oracle-ai-developer-hub)** — More technical assets, samples, and projects with Oracle AI
- **[Oracle AI Vector Search docs](https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/)** — Full reference for the `VECTOR` data type, distance functions, and index types
- **[Oracle Developer Resource](https://www.oracle.com/developer/)** — Documentation, tools, and community for Oracle developers

---

Built in partnership with Oracle
