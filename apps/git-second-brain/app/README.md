# Git Second Brain — App

Streamlit chat UI that lets you ask natural-language questions about a
repository's commit history, powered by **Oracle AI Database 26ai Vector Search**,
LangChain, and OpenAI.

## Architecture

```
User question
    │
    ▼
┌────────────────────┐      ┌──────────────────────────┐
│  Streamlit (app.py)│─────▶│  OracleCommitRetriever   │
│  Chat interface    │      │  sentence-transformers    │
└────────┬───────────┘      │  + Oracle 26ai vector     │
         │                  │    VECTOR_DISTANCE search │
         │ context docs     └──────────────────────────┘
         ▼
┌────────────────────┐
│  LangChain RAG     │
│  ChatOpenAI (GPT)  │
└────────────────────┘
```

## Prerequisites

| Requirement             | Version                       |
| ----------------------- | ----------------------------- |
| Python                  | 3.10+                         |
| Oracle AI Database 26ai | Running and accessible        |
| OpenAI API key          | Any `gpt-4o-mini` capable key |

The `data-loader/` must have been run first so the `FASTAPI_COMMITS` table is
populated with embeddings.

## Setup

```bash
cd app
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

## Running

The app reads Oracle credentials from environment variables. Load them before
starting Streamlit:

```bash
# Load env vars from .env (use your preferred method)
# Windows PowerShell:
Get-Content .env | ForEach-Object { if ($_ -match '^([^#].+?)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2]) } }

# Linux / macOS:
# export $(grep -v '^#' .env | xargs)

streamlit run app.py
```

The app opens at <http://localhost:8501>.

## Smoke test

A standalone script that verifies the vector-search round trip without
Streamlit or OpenAI. Requires the same environment variables:

```bash
python smoke_test.py
```

## Files

| File               | Purpose                                                       |
| ------------------ | ------------------------------------------------------------- |
| `app.py`           | Streamlit chat UI + LangChain RAG chain                       |
| `retriever.py`     | LangChain `BaseRetriever` backed by Oracle 26ai vector search |
| `smoke_test.py`    | Minimal end-to-end connectivity & vector-search test          |
| `requirements.txt` | Pinned Python dependencies                                    |
| `.env.example`     | Template for required environment variables                   |

## Environment variables

| Variable          | Required | Default | Description                                    |
| ----------------- | -------- | ------- | ---------------------------------------------- |
| `ORACLE_USER`     | Yes      | —       | Database username                              |
| `ORACLE_PASSWORD` | Yes      | —       | Database password                              |
| `ORACLE_DSN`      | Yes      | —       | Connect string, e.g. `localhost:1521/FREEPDB1` |
| `OPENAI_API_KEY`  | No       | —       | Can also be entered in the Streamlit sidebar   |
