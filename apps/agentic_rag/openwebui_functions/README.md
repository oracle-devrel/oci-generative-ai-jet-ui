# Open WebUI Functions for Oracle AI Database Integration

These functions integrate Open WebUI with Oracle AI Database via langchain-oracledb, enabling unified vector storage and retrieval across both systems.

## Overview

| Function | Type | Description |
|----------|------|-------------|
| `oracle_rag_filter.py` | Filter | Auto-retrieves context from Oracle DB before LLM calls, syncs documents automatically |
| `oracle_rag_pipe.py` | Pipe | Creates "Oracle RAG" models with different reasoning strategies |
| `oracle_document_sync.py` | Action | Manual document sync to Oracle AI Database |

## Installation

### Prerequisites

1. The agentic_rag API server must be running:
   ```bash
   cd apps/agentic_rag
   python openwebui_app.py
   ```

2. Oracle AI Database must be configured with vector storage enabled.

### Installing Functions in Open WebUI

1. Open WebUI at http://localhost:3000
2. Go to **Workspace** > **Functions**
3. Click the **+** button to create a new function
4. Copy and paste the code from each `.py` file
5. Save the function

## Function Details

### 1. Oracle RAG Filter (`oracle_rag_filter.py`)

**Type:** Filter (inlet/outlet)

This filter intercepts all chat requests and:
- **Inlet:** Queries Oracle AI Database for relevant context and injects it into the prompt
- **Outlet:** Can sync responses back to Oracle for future retrieval

**Configuration Valves:**

| Valve | Default | Description |
|-------|---------|-------------|
| `api_base_url` | `http://localhost:8000` | Agentic RAG API URL |
| `enable_rag_retrieval` | `true` | Enable RAG context retrieval |
| `enable_document_sync` | `true` | Enable auto document sync |
| `top_k_results` | `5` | Number of results to retrieve |
| `min_query_length` | `10` | Min query length to trigger RAG |
| `inject_sources_in_response` | `true` | Show retrieved sources |

**Usage:**
- Enable the filter for your models in Open WebUI settings
- The filter will automatically enhance your queries with Oracle DB context

### 2. Oracle RAG Pipe (`oracle_rag_pipe.py`)

**Type:** Pipe (manifold)

Creates dedicated Oracle RAG models in Open WebUI's model dropdown:

| Model | Strategy | Description |
|-------|----------|-------------|
| Oracle RAG (Chain of Thought) | `cot-rag` | Step-by-step reasoning |
| Oracle RAG (Tree of Thoughts) | `tot-rag` | Multi-path exploration |
| Oracle RAG (ReAct) | `react-rag` | Reasoning and acting |
| Oracle RAG (Standard) | `standard-rag` | Simple RAG |
| Oracle RAG (Decomposed) | `decomposed-rag` | Problem decomposition |
| Oracle RAG (Self-Consistency) | `consistency-rag` | Multiple samples with voting |

**Usage:**
1. After installing, the Oracle RAG models appear in the model dropdown
2. Select any Oracle RAG model for your chat
3. Queries are automatically routed through Oracle AI Database

### 3. Oracle Document Sync (`oracle_document_sync.py`)

**Type:** Action

Manual action to sync documents to Oracle AI Database.

**Usage:**
1. In a chat, click the action button
2. The current context will be synced to Oracle AI Database
3. Status is shown in the chat

## Automatic Content Persistence

The API server automatically persists content to Oracle AI Database:

### Attach Webpage (`<source>` tags)
When you use Open WebUI's "Attach Webpage" feature, the embedded content is automatically:
1. Detected in the message (via `<source>` tags)
2. Chunked into 800-character segments
3. Persisted to **WEBCOLLECTION** as `openwebui_webpage`
4. Logged to Oracle DOCUMENT_EVENTS table

### Upload Link (URL files)
When you use Open WebUI's "Upload Link" feature, the URL is automatically:
1. Detected in the `files` array of the request
2. Fetched using WebProcessor (trafilatura)
3. Chunked and persisted to **WEBCOLLECTION** as `openwebui_url`
4. Logged to Oracle DOCUMENT_EVENTS table

**Supported URL types:**
- Standard web pages (HTML)
- Documentation sites
- Blog posts
- News articles

**Special handling:**
- Twitter/X: Returns placeholder (API access required)
- GitHub repos: Returns summary with link to README

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Open WebUI                                │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ RAG Filter   │  │ RAG Pipe     │  │ Document Sync Action   │ │
│  │ (inlet/      │  │ (manifold)   │  │                        │ │
│  │  outlet)     │  │              │  │                        │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘ │
└─────────┼─────────────────┼──────────────────────┼──────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agentic RAG API Server                        │
│                    (http://localhost:8000)                       │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │ /v1/chat/      │  │ /sync/         │  │ /query           │   │
│  │ completions    │  │ embeddings     │  │                  │   │
│  └───────┬────────┘  └───────┬────────┘  └────────┬─────────┘   │
└──────────┼───────────────────┼─────────────────────┼────────────┘
           │                   │                     │
           ▼                   ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Oracle AI Database                            │
│                    (langchain-oracledb)                          │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │ PDFCOLLECTION  │  │ WEBCOLLECTION  │  │ GENERALCOLLECTION│   │
│  └────────────────┘  └────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | OpenAI-compatible chat with RAG |
| `/v1/models` | GET | List available reasoning strategies |
| `/sync/embeddings` | POST | Sync documents to Oracle |
| `/sync/status` | GET | Get sync status |
| `/query` | POST | Query with RAG context |

## Troubleshooting

### Filter not retrieving context
1. Check that the API server is running: `curl http://localhost:8000/v1/health`
2. Verify Oracle DB connection in API logs
3. Ensure documents are indexed in Oracle collections

### Pipe models not appearing
1. Refresh the Open WebUI page
2. Check browser console for errors
3. Verify the function is saved correctly

### Sync failures
1. Check API server logs: `tail -f /tmp/api_server.log`
2. Verify Oracle DB connectivity
3. Check document format matches expected schema

## Development

To modify these functions:
1. Edit the `.py` files in this directory
2. Copy updated code to Open WebUI function editor
3. Save and test

For local development, you can also use the Pipelines server:
```bash
pip install open-webui-pipelines
PIPELINES_URLS="file:///path/to/oracle_rag_filter.py" pipelines
```
