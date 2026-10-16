# Git Second Brain

A RAG (Retrieval-Augmented Generation) application that lets you ask
natural-language questions about **any Git repository** by analysing its
commit history. The included example uses the **FastAPI** open-source project.

Commits are embedded as vectors and stored in **Oracle AI Database 26ai**.
At query time the most relevant commits are retrieved via `VECTOR_DISTANCE`
and passed as context to an OpenAI model through **LangChain**, producing
grounded answers with commit citations.

## Project structure

```
git-second-brain/
├── database/      # SQL scripts: user creation + schema setup
├── data-loader/   # One-time ETL: parse commits, embed, load into Oracle 26ai
├── app/           # Streamlit chat UI + LangChain RAG chain
├── diffs/         # Pre-extracted per-commit diff files
└── fastapi_commits.txt  # Delimited commit metadata
```

| Folder           | Purpose                                                                                                                                                                                      | Details                                        |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **database/**    | SQL scripts to create the Oracle user, table, indexes, and (optionally) the vector index.                                                                                                    | [database/README.md](database/README.md)       |
| **data-loader/** | Reads the extracted commit metadata and diff files, generates 384-dim vector embeddings with `sentence-transformers`, and bulk-inserts everything into Oracle 26ai.                          | [data-loader/README.md](data-loader/README.md) |
| **app/**         | Streamlit chat interface where users ask questions. A custom LangChain retriever queries Oracle 26ai vector search, and the retrieved commits are sent to OpenAI to generate a cited answer. | [app/README.md](app/README.md)                 |

## Extracting repo data

The examples below use **FastAPI**, but this works with **any Git repository**.

```bash
# Clone the target repo
git clone https://github.com/tiangolo/fastapi.git
mkdir diffs
cd fastapi

# Extract commit metadata with safe delimiters
git log --all --no-merges \
  --pretty=format:"<<<COMMIT>>>%n%H%n%an%n%aI%n%s%n<<<BODY>>>%n%b%n<<<END>>>%n" \
  > ../fastapi_commits.txt

# Extract diff stats as a single file
git log --all --no-merges \
  --pretty=format:"===SHA:%H===" --stat \
  > ../diffs/all_diffs.txt

cd ..
```

> **Tip:** The data loader caps at 3 000 commits by default, which keeps
> indexing time under 10 minutes and covers roughly 2015–today for FastAPI.

## Prerequisites

- Python 3.10+
- Oracle AI Database 26ai (running and accessible)
- OpenAI API key (for the chat app)

## Quick start

> **Important:** Load the environment variables from each folder's `.env` file
> before running Python scripts. See each folder's README for details.

```bash
# 0. Set up the database
cd database
sqlplus system/Welcome_123@//localhost:1521/FREEPDB1 @01_create_user.sql
sqlplus system/Welcome_123@//localhost:1521/FREEPDB1 @02_create_schema.sql
cd ..

# 1. Extract repo data (see "Extracting repo data" above)

# 2. Load data into Oracle 26ai
cd data-loader
python -m venv .venv && .venv\Scripts\activate   # or source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your Oracle credentials
# load env vars, then:
python load_data.py
cd ..

# 3. Run the app
cd app
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in Oracle + OpenAI credentials
# load env vars, then:
streamlit run app.py
```

See each folder's README for full setup and configuration details.
