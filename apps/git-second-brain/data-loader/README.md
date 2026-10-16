# Git Second Brain — Data Loader

Reads a repository's commit history from a plain-text dump, generates vector
embeddings with `sentence-transformers`, and bulk-inserts everything into an
**Oracle AI Database 26ai** table.

## How it works

1. Parses `fastapi_commits.txt` (delimited commit metadata) and
   `diffs/all_diffs.txt` (per-commit file-change stats).
2. For each commit, builds a combined text blob and encodes it with the
   `all-MiniLM-L6-v2` model (384-dimensional vectors).
3. Inserts rows in batches into `FASTAPI_COMMITS`, handling duplicate SHAs
   gracefully.

## Prerequisites

| Requirement             | Version                                                  |
| ----------------------- | -------------------------------------------------------- |
| Python                  | 3.10+                                                    |
| Oracle AI Database 26ai | Running, with the schema created via `database/` scripts |

The following data files must exist relative to this folder:

- `../fastapi_commits.txt` — commit metadata
- `../diffs/all_diffs.txt` — diff / file-change information (optional but recommended)

## Setup

```bash
cd data-loader
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

Load your environment variables before running the script:

```bash
# Load env vars from .env (use your preferred method)
# Windows PowerShell:
Get-Content .env | ForEach-Object { if ($_ -match '^([^#].+?)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2]) } }

# Linux / macOS:
# export $(grep -v '^#' .env | xargs)

python load_data.py
```

Progress is printed to stdout. A full run (~3 000 commits) takes a few minutes
depending on hardware and network latency to the database.

## Environment variables

| Variable          | Required | Default               | Description                                    |
| ----------------- | -------- | --------------------- | ---------------------------------------------- |
| `ORACLE_USER`     | Yes      | —                     | Database username                              |
| `ORACLE_PASSWORD` | Yes      | —                     | Database password                              |
| `ORACLE_DSN`      | Yes      | —                     | Connect string, e.g. `localhost:1521/FREEPDB1` |
| `ORACLE_SCHEMA`   | No       | `GITHUB_SECOND_BRAIN` | Target schema for the table                    |

## Files

| File               | Purpose                                     |
| ------------------ | ------------------------------------------- |
| `load_data.py`     | Main loader script                          |
| `requirements.txt` | Pinned Python dependencies                  |
| `.env.example`     | Template for required environment variables |
