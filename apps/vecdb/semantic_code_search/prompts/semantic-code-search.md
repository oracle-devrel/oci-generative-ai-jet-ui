# Run the Oracle VecDB Semantic Code Search Sample

Help the user run the existing public Oracle AI Developer Hub
`semantic_code_search` sample. This is an existing full-stack application, not
an application to build from scratch. Use the sample README as the source of
truth for installation, configuration, indexing, and usage. Preserve its
FastAPI backend, React frontend, AST-based Python snippet extraction, Jina code
embeddings, and Oracle VecDB retrieval flow.

Use an existing Oracle AI Database deployment with an existing Oracle VecDB
SDK REST endpoint. The sample also needs a local Python codebase containing
Python files to index; the README uses the LangChain repository as an example.
Ask the user for a codebase path if they do not already have one. Ask for
existing VecDB connection details only when needed, and never print, copy, or
commit those values.

Do not provision or create a database instance, tenancy, ORDS deployment,
schema, user, or credentials. Do not change the sample to use another vector
store, embedding model, or application architecture.

From the intended working directory, use a Git sparse checkout so only the
mapped application is fetched:

```bash
git clone --depth 1 --filter=blob:none --sparse --branch main \
  https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub
git sparse-checkout set apps/vecdb/semantic_code_search
cd apps/vecdb/semantic_code_search
```

Read `README.md`, `backend/requirements.txt`, and the frontend package files
before taking setup or runtime actions. From the sample directory, create and
activate the virtual environment in `backend/`, then install
`backend/requirements.txt` from that directory. Do not run
`pip install -r requirements.txt` from the sample root because the requirements
file is under `backend/`. Run backend commands from `backend/` and frontend
commands from `frontend/`, matching the repository layout. Use the platform's
Python and virtual-environment activation commands when `python3` or POSIX
`source` is not available.

## Configure the sample

Copy `backend/.env.example` to `backend/.env`. Tell the user the absolute path
and ask them to populate the VecDB connection values and `CODE_DIR` themselves.
`CODE_DIR` must be an absolute path to the Python codebase to index. Do not
display, read back, copy, or include the connection values in generated content.
Wait for the user to confirm that the file is complete before running the
indexer or backend.

After confirmation, verify that the configured codebase exists and contains
Python files. The sample uses `jinaai/jina-embeddings-v2-base-code` to create
768-dimensional vectors and stores them in the configured
`ORACLE_TABLE_NAME`, which defaults to `LANGCHAIN_CODE_SEARCH`.

## Index the codebase

Ask for explicit confirmation before indexing because this step generates a
local JSONL file and creates or populates the sample's configured VecDB table.
Follow the README's loader command from the `backend/` directory:

```bash
python load_chunks.py
```

Do not drop or recreate an existing table unless the user explicitly requests
that operation. Do not write to tables outside the sample's configured table.

## Run the application

After indexing succeeds, start the backend as documented:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then start the frontend from `frontend/` with the README's `VITE_API_BASE`
setting and development-server command. Verify the backend and frontend URLs
before reporting them. Point the user back to the README for modifying or
extending the sample.

## Sources

- Semantic Code Search README: https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/apps/vecdb/semantic_code_search
- Oracle VecDB Python SDK API reference: https://docs.oracle.com/en/cloud/paas/autonomous-vector-database/vcapi/index.html
