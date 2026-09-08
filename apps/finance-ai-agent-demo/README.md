# Agentic Financial Service Assistant (AFSA)

A full-stack application showcasing **Oracle AI Database** as a **unified memory core for AI agents**. A financial services AI agent answers employee questions by executing vector similarity search, JSON/document lookups, graph traversals, spatial proximity queries, relational queries, convergent multi-paradigm queries, and hybrid retrieval -- all against a single Oracle AI Database instance.

## Architecture

```
Browser (React SPA)
  |-- Chat Interface       -- conversational AI with streaming + tool-call bubbles
  |-- Right Pane (tabbed)  -- Database queries | Application logs | Context window
  |-- Nav Pane             -- thread management, about modal, starter queries
        |
   WebSocket + REST (Socket.IO)
        |
Flask API (Python / eventlet)
  |-- Agent Harness       -- turn-level agent loop with streaming tool calling
  |-- Memory Manager      -- 6+1 memory types, thread-isolated
  |-- Retrieval Engine    -- text, vector, hybrid, graph, spatial, relational, JSON, convergent
  |-- Context Engineering -- token tracking, conversation compaction, JIT summary expansion
  |-- Query Logger        -- intercepts all DB queries for real-time streaming
  |-- File Ingestor       -- PDF/TXT/CSV upload -> chunk -> embed -> store pipeline
        |
   python-oracledb (thin mode)
        |
Oracle AI Database 26ai (Docker)
  |-- Relational Tables (SQL)
  |-- Vector Indexes (HNSW, 768-dim cosine)
  |-- Property Graph (SQL Property Graph)
  |-- JSON/Document Storage (CLOB + JSON_VALUE)
  |-- Spatial Indexes (SDO_GEOMETRY, R-tree)
  |-- Oracle Text (Full-Text Search with CONTAINS)
```

## Key Message

> Oracle AI Database eliminates the need for a fragmented data architecture. Vector store + document store + graph database + spatial engine + relational database all converge into **one unified memory core** for AI agents.

## Prerequisites

- Docker (for Oracle Database)
- Python 3.11+
- Node.js 18+
- OpenAI API key

## Quick Start

All commands below assume you are in the `apps/finance-ai-agent-demo/` directory.

### 1. Start Oracle Database

```bash
bash scripts/setup_db.sh
```

This pulls the Oracle Free image, starts the container, fixes the listener for ARM Macs, and configures 512MB of vector memory for HNSW indexes. The first run takes 2-3 minutes while Oracle initializes.

### 2. Setup Environment

```bash
cp .env.example .env
# Edit .env with your OpenAI API key and Tavily key
```

### 3. Install Dependencies

```bash
# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### 4. Setup Database & Seed Data

```bash
python scripts/seed_data.py
```

This creates the VECTOR user, tables, HNSW vector indexes, Oracle Text index, property graph, spatial indexes, and seeds 25 accounts with geospatial coordinates, 273 holdings, 52 knowledge base documents, and 35 graph edges.

### 5. Run the Application

```bash
# Terminal 1: Backend
cd backend && python app.py

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open http://localhost:3000

## Features

### Three-Pane UI

- **Chat pane** -- streaming LLM responses with tool-call bubbles, starter query buttons for new threads
- **Right pane** -- tabbed between Database (live SQL queries), Application (agent loop logs), and Context (memory breakdown)
- **Nav pane** -- thread history, about modal with demo guide

### Agent Tools

Tools are stored in the database (TOOLBOX_MEMORY) with LLM-augmented descriptions and synthetic activation queries. At inference time, the agent assembles its toolset from two sources:

- **Preloaded** -- hardcoded in the agent harness, always available regardless of query or DB state
- **Dynamic** -- retrieved via hybrid search (vector + Oracle Text RRF) from TOOLBOX_MEMORY based on the user's query

| Tool                         | Loading   | DB Paradigm                                 | Purpose                                                              |
| ---------------------------- | --------- | ------------------------------------------- | -------------------------------------------------------------------- |
| `expand_summary`             | Preloaded | --                                          | Expand a compressed summary reference to full content (JIT)          |
| `summarize_conversation`     | Preloaded | --                                          | Compact conversation history to reduce context window size           |
| `search_tavily`              | Preloaded | --                                          | Web search fallback for real-time market data or news                |
| `get_account_details`        | Dynamic   | SQL + JSON                                  | Account lookup with client name, risk profile, AUM, JSON metadata    |
| `get_portfolio_risk`         | Dynamic   | SQL                                         | Portfolio holdings analysis, asset allocation, risk ratings          |
| `check_compliance`           | Dynamic   | SQL                                         | Check portfolio against active FCA/SEC/MiFID II compliance rules     |
| `find_similar_accounts`      | Dynamic   | Graph                                       | Graph traversal to find related accounts via property graph          |
| `search_knowledge_base`      | Dynamic   | Vector                                      | Semantic vector search over financial research and regulatory docs   |
| `get_investment_preferences` | Dynamic   | JSON                                        | Extract investment preferences from account metadata CLOB            |
| `search_compliance_rules`    | Dynamic   | Hybrid (Text + Vector)                      | Combined keyword and semantic search over compliance rules           |
| `find_nearby_clients`        | Dynamic   | Spatial                                     | Find geographically nearby accounts using SDO_GEOMETRY               |
| `convergent_search`          | Dynamic   | Convergent (SQL + Graph + Vector + Spatial) | Single query combining relational, graph, vector, and spatial search |

### Memory System (Thread-Isolated)

All memory types are scoped to the active thread to prevent cross-thread contamination:

| Type           | Storage             | Purpose                                             |
| -------------- | ------------------- | --------------------------------------------------- |
| Conversational | SQL Table           | Chat history per thread (with compaction)           |
| Knowledge Base | Vector Table (HNSW) | Financial research, regulatory docs, user uploads   |
| Workflow       | Vector Table        | Learned action patterns from prior queries          |
| Toolbox        | Vector Table        | Semantic tool discovery                             |
| Entity         | Vector Table        | People, accounts, instruments mentioned             |
| Summary        | Vector Table        | Compressed context snapshots (JIT expansion)        |
| Tool Log       | SQL Table           | Full tool output offloading with compact references |

### Context Engineering

- Real-time token usage bar with per-memory-type breakdown
- One-click **Compact** button to summarize older conversation turns, reducing token usage
- Summary IDs can be expanded on-demand via `expand_summary` tool
- Context window viewer shows the exact content injected into each LLM call

### Document Ingestion

- Drag-and-drop or click-to-upload PDF, TXT, CSV files
- Automatic chunking (1000 char / 200 overlap) and embedding with `paraphrase-mpnet-base-v2`
- Ingestion progress streamed via WebSocket; ingestion queries logged in the Database pane

### Query Visualization

- Every database query is intercepted, classified, and streamed to the frontend in real-time
- Type badges: `SQL` `VEC` `TXT` `HYB` `GRF` `JSON` `SPA` `CONVERGENT`
- Expandable SQL with bind parameters and latency timing
- Query summary footer with counts by type

## Demo Script

The primary demo question:

> **"What is the risk exposure on the Smith portfolio, and are there any compliance concerns?"**

This single question triggers ALL retrieval types:

1. **Relational** -- Account details and holdings lookup
2. **Vector** -- Semantic search for risk methodology research
3. **Graph** -- Find similar accounts via property graph traversal
4. **Hybrid** -- Combined text + vector search for compliance rules
5. **JSON** -- Extract investment preferences from metadata CLOB
6. **Text** -- Keyword search in compliance documentation

For a spatial proximity query, try:

> **"Which clients are within 500km of ACC-001?"**

This uses Oracle Spatial's SDO_WITHIN_DISTANCE with an R-tree spatial index to find geographically nearby accounts.

For a convergent query, try:

> **"Run a convergent search for ACC-003 to find connected accounts and relevant risk research"**

This executes a single SQL statement with CTEs that combines relational data, graph traversal (GRAPH_TABLE), vector search (VECTOR_DISTANCE), and spatial proximity (SDO_WITHIN_DISTANCE) in one query.

## Project Structure

```
finance-ai-agent-demo/
|-- backend/
|   |-- app.py                 # Flask entry point with eventlet
|   |-- config.py              # Configuration from .env
|   |-- database/
|   |   |-- connection.py      # Oracle connection with retry logic
|   |   |-- setup.py           # DDL: tables, indexes, graph, vector stores
|   |   |-- seed.py            # Seed data (accounts, holdings, KB docs, graph edges)
|   |   |-- query_logger.py    # SQL interceptor with type classification
|   |-- memory/
|   |   |-- manager.py         # MemoryManager (6+1 memory types, thread-scoped)
|   |-- retrieval/
|   |   |-- vector_search.py   # VECTOR_DISTANCE similarity search
|   |   |-- text_search.py     # Oracle Text CONTAINS with sanitization
|   |   |-- hybrid_search.py   # Combined text + vector
|   |   |-- graph_search.py    # SQL Property Graph traversal
|   |   |-- spatial_search.py  # Oracle Spatial SDO_GEOMETRY proximity search
|   |-- ingestion/
|   |   |-- file_processor.py  # PDF/TXT/CSV text extraction
|   |   |-- chunker.py         # Fixed-size chunking with overlap
|   |   |-- ingestor.py        # Full extract -> chunk -> embed -> store pipeline
|   |-- agent/
|   |   |-- harness.py         # Agent loop: context build -> LLM -> tool calls -> save
|   |   |-- tools.py           # Tool schemas + executors (12 tools incl. spatial + convergent)
|   |   |-- system_prompt.py   # Agent system instructions
|   |   |-- context_engineering.py  # Token tracking, compaction, summarization
|   |-- api/
|       |-- routes.py          # REST endpoints (health, threads, upload, context)
|       |-- events.py          # WebSocket event handlers (chat, compaction, context)
|
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |   |-- Layout.jsx         # Three-pane layout with resizable right pane
|   |   |   |-- ChatPane.jsx       # Chat interface with starter queries
|   |   |   |-- ChatMessage.jsx    # Markdown rendering + tool call bubbles
|   |   |   |-- ChatInput.jsx      # Input with file upload
|   |   |   |-- QueryStream.jsx    # Real-time database query cards
|   |   |   |-- QueryBadge.jsx     # SQL/VEC/GRF/TXT/HYB/JSON/SPA/CONVERGENT badges
|   |   |   |-- AppLogs.jsx        # Agent application log viewer
|   |   |   |-- ContextActivity.jsx # Context window breakdown viewer
|   |   |   |-- TokenUsageBar.jsx  # Token bar with compact button
|   |   |   |-- NavPane.jsx        # Thread list, about modal
|   |   |-- hooks/
|   |   |   |-- useChat.js         # Chat state machine (useReducer)
|   |   |   |-- useWebSocket.js    # Socket.IO connection
|   |   |-- styles/
|   |       |-- glow.css           # Tailwind layers + badge styles
|   |-- index.html
|
|-- scripts/
|   |-- setup_db.sh            # Docker setup for Oracle Database
|   |-- seed_data.py           # Database schema + seed runner
|-- docker-compose.yml
|-- .env.example
```

## Technology Stack

| Layer                  | Technology                                               |
| ---------------------- | -------------------------------------------------------- |
| Frontend               | React 18, Tailwind CSS, Socket.IO Client, React Markdown |
| Backend                | Flask, Flask-SocketIO, eventlet                          |
| Memory Core (Database) | Oracle AI Database 26ai                                  |
| DB Driver              | python-oracledb (thin mode)                              |
| Orchestrator           | langchain-oracledb (OracleVS with HNSW)                  |
| Embeddings             | sentence-transformers/paraphrase-mpnet-base-v2 (768-dim) |
| LLM                    | OpenAI GPT-5 (configurable via OPENAI_MODEL env var)     |
| Real-time              | WebSocket (Socket.IO with eventlet async)                |
| Search                 | Tavily API (web search fallback)                         |

## Sprawl Architecture (Multi-Database Alternative)

### Overview

The sprawl architecture is an alternative deployment mode that replaces Oracle's converged database with four separate, purpose-built databases:

- **PostgreSQL + PostGIS** -- relational queries and spatial/geospatial operations
- **Neo4j Community Edition** -- graph traversal and relationship queries
- **MongoDB Community Edition** -- JSON/document storage and retrieval
- **Qdrant** -- vector similarity search (HNSW indexes)

This mode exists to demonstrate the operational and architectural trade-offs of a fragmented data layer versus a single converged database. The same frontend and agent harness work in both modes; only the backend retrieval and memory layers differ.

### Architecture Comparison

| Capability             | Converged (Oracle)                    | Sprawl                              |
| ---------------------- | ------------------------------------- | ----------------------------------- |
| Relational             | Oracle SQL                            | PostgreSQL                          |
| Vector Search          | Oracle AI Vector Search (HNSW)        | Qdrant                              |
| Graph                  | SQL Property Graph (GRAPH_TABLE)      | Neo4j (Cypher)                      |
| JSON/Document          | JSON/CLOB with JSON_VALUE             | MongoDB                             |
| Spatial                | Oracle Spatial (SDO_GEOMETRY, R-tree) | PostGIS                             |
| Full-Text Search       | Oracle Text (CONTAINS)                | PostgreSQL tsvector / ts_query      |
| Connections needed     | 1                                     | 4                                   |
| Docker containers      | 1                                     | 4                                   |
| Cross-paradigm queries | Yes (single SQL with CTEs)            | No (application-level joins)        |
| Consistency model      | ACID (single engine)                  | Eventually consistent across stores |

### Sprawl Quick Start

```bash
docker-compose -f docker-compose.sprawl.yml up -d
# or
bash scripts/setup_sprawl.sh
```

Then set `ARCH_MODE=sprawl` in your `.env` file and run the same backend/frontend commands as the standard quick start:

```bash
# Terminal 1: Backend
cd backend && python app.py

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Environment Variables

Set the following in `.env` when running in sprawl mode:

| Variable            | Example Value               | Purpose                                     |
| ------------------- | --------------------------- | ------------------------------------------- |
| `ARCH_MODE`         | `sprawl`                    | Switches the backend to multi-database mode |
| `POSTGRES_HOST`     | `127.0.0.1`                 | PostgreSQL host                             |
| `POSTGRES_PORT`     | `5432`                      | PostgreSQL port                             |
| `POSTGRES_USER`     | `sprawl`                    | PostgreSQL user                             |
| `POSTGRES_PASSWORD` | `sprawl_pwd`                | PostgreSQL password                         |
| `POSTGRES_DB`       | `finance`                   | PostgreSQL database name                    |
| `NEO4J_URI`         | `bolt://localhost:7687`     | Neo4j Bolt protocol URI                     |
| `NEO4J_USER`        | `neo4j`                     | Neo4j user                                  |
| `NEO4J_PASSWORD`    | `neo4j_pwd`                 | Neo4j password                              |
| `MONGO_URI`         | `mongodb://localhost:27017` | MongoDB connection string                   |
| `MONGO_DB`          | `finance`                   | MongoDB database name                       |
| `QDRANT_HOST`       | `127.0.0.1`                 | Qdrant host                                 |
| `QDRANT_PORT`       | `6333`                      | Qdrant REST API port                        |

### Trade-offs

What you lose compared to the converged architecture:

- **No single-query convergent search** -- the converged demo's `convergent_search` tool issues one SQL statement that combines relational, graph, vector, and spatial results via CTEs. In sprawl mode this requires four separate network calls and application-level merging.
- **Multiple failure domains** -- each database can fail independently, requiring separate health checks and failover strategies.
- **Network latency between services** -- every cross-paradigm operation adds at least one extra network hop.
- **Separate backup, security, and monitoring** -- four databases means four sets of credentials, four backup schedules, four audit logs, and four monitoring dashboards.
- **No ACID guarantees across stores** -- transactions that span PostgreSQL and MongoDB (or any two engines) cannot be atomic without an external coordinator.
