# Oracle AI Database + LangChain.js RAG Assistant

Companion TypeScript application for the article [_Build a LangChain.js RAG Assistant with Oracle AI Database_](./docs/article.md).

This sample shows JavaScript and TypeScript developers how to use LangChain.js with Oracle AI Database as the vector store. It is intentionally a runnable Node.js app, not a notebook: a React frontend calls a Hono API, the API runs a LangChain.js RAG workflow, and `@oracle/langchain-oracledb` stores and searches vectors in Oracle AI Database through `OracleVS`.

The sample answers developer questions about Oracle AI Database, OracleVS, metadata filters, MMR retrieval, vector indexes, and common Oracle connection errors from a seeded markdown knowledge base.

## Pipeline

1. Load markdown files from `samples/knowledge-base`.
2. Split them into section-level LangChain `Document` chunks with metadata.
3. Embed the chunks with a deterministic TypeScript `Embeddings` implementation for repeatable local runs.
4. Store text, embeddings, and JSON metadata in Oracle AI Database with `OracleVS.fromDocuments`.
5. Retrieve context with similarity search, similarity search with scores, metadata filters, or MMR.
6. Generate a grounded answer from the retrieved OracleVS context, or return an extractive answer when no LLM key is configured.
7. Inspect the Oracle table, columns, row count, vector index, query vector preview, retrieved chunks, and representative vector-search SQL in the browser UI.

## Prerequisites

- Node.js 22 or later
- pnpm 10 or later
- One Oracle Database target with vector support: local Oracle Database Free / Oracle AI Database or Autonomous AI Database
- A schema that can create, insert into, select from, and drop demo tables
- Optional: `OPENAI_API_KEY` for generated grounded answers

## Quickstart

```bash
pnpm install
cp .env.example .env
```

Choose one Oracle connection target and fill in `.env`:

| Target | When to use it | Connection values |
| --- | --- | --- |
| Local Oracle Database Free / Oracle AI Database | Local development with a container or local database listener | `ORACLE_CONNECT_STRING=localhost:1521/FREEPDB1` |
| Autonomous AI Database | Cloud database with wallet-based mTLS | `ORACLE_CONNECT_STRING=<service alias or full descriptor>`, plus `ORACLE_WALLET_LOCATION` and usually `ORACLE_WALLET_PASSWORD` |

For example, a local Oracle Database Free setup usually looks like:

```env
ORACLE_USER=<database-user>
ORACLE_PASSWORD=<database-password>
ORACLE_CONNECT_STRING=localhost:1521/FREEPDB1
ORACLE_TABLE_NAME=LC_JS_RAG_DEMO
ORACLE_CREATE_VECTOR_INDEX=false
```

The same app also accepts `DB_USER`, `DB_PASSWORD`, `DB_CONNECT_STRING`, `DB_DSN`, and `ORACLEDB_CONNECTION_STRING` aliases if those are the names copied from another tutorial.

Check the database connection:

```bash
pnpm db:check
```

Seed the OracleVS table:

```bash
pnpm seed
```

Run the API in one terminal:

```bash
pnpm dev:api
```

Run the web app in another terminal:

```bash
pnpm dev
```

Open:

```text
http://localhost:5173
```

## Container Deployment

The Dockerfile builds the React app and the Hono API into one Node.js image. At runtime the API serves the compiled web app from the same origin, so `VITE_API_BASE_URL` can be omitted unless the browser UI must call a separate API host.

Build the image:

```bash
docker build -t oracle-langchain-js-rag .
```

Run it with the same environment values used for local development:

```bash
docker run --env-file .env -p 8787:8787 oracle-langchain-js-rag
```

Open:

```text
http://localhost:8787
```

The container expects the Oracle database target from `.env` to be reachable from inside the container. For a local database running on the host, use the host address that your container runtime exposes rather than `localhost`.

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `ORACLE_USER` | yes | Oracle schema username |
| `ORACLE_PASSWORD` | yes | Oracle schema password |
| `ORACLE_CONNECT_STRING` | yes | Oracle connect string, service name, descriptor, or TCPS DSN |
| `ORACLE_DSN` | alias | Accepted as an alias for `ORACLE_CONNECT_STRING` |
| `ORACLE_WALLET_LOCATION` | no | Wallet directory for mTLS Autonomous Database connections |
| `ORACLE_WALLET_PASSWORD` | no | Wallet password when needed by node-oracledb thin mode |
| `ORACLE_TABLE_NAME` | no | OracleVS table name. Defaults to `LC_JS_RAG_DEMO` |
| `ORACLE_CREATE_VECTOR_INDEX` | no | Set `true` to attempt HNSW vector index creation during seed |
| `OPENAI_API_KEY` | no | Enables generated grounded answers through `@langchain/openai` |
| `OPENAI_MODEL` | no | Chat model for answer generation. Defaults to `gpt-4o-mini` |
| `OAMP_LLM_MODEL` | alias | Accepted as a model-name alias if you already use this variable |
| `PORT` | no | API port. Defaults to `8787` |
| `VITE_API_BASE_URL` | no | Web app API base URL. Defaults to same-origin; `.env.example` sets `http://localhost:8787` for local Vite development |

`DB_USER`, `DB_PASSWORD`, `DB_CONNECT_STRING`, `DB_DSN`, and `ORACLEDB_CONNECTION_STRING` are also accepted as aliases for local conventions.

## Repo Layout

```text
apps/web        React + Vite UI for retrieval controls, traces, answers, and Oracle inspection
services/api    Hono API exposing status, corpus, inspect, seed, reset, and ask endpoints
packages/core   Knowledge-base loading, embeddings, retrieval, answer generation, and trace shaping
packages/db     Oracle config, node-oracledb pool, OracleVS helpers, table inspection
packages/shared Shared TypeScript types for API responses
scripts/        CLI scripts for db:check, seed, reset, and cleanup
samples/        Markdown knowledge-base files loaded into OracleVS
docs/           Long-form article, local development guide, diagrams, and screenshots
```

## Scripts

| Command | Description |
| --- | --- |
| `pnpm db:check` | Validate environment variables and test the Oracle connection |
| `pnpm seed` | Reset and load the markdown knowledge base into OracleVS |
| `pnpm reset` | Drop the demo OracleVS table |
| `pnpm dev:api` | Run the Hono API on `:8787` |
| `pnpm dev` | Run the Vite web app on `:5173` |
| `pnpm typecheck` | Type-check all workspace packages |
| `pnpm test` | Run unit tests |
| `pnpm build` | Build packages, API, and web app |
| `pnpm check` | Run typecheck, tests, and build |
| `pnpm clean` | Remove generated build outputs and caches |
| `pnpm clean:deps` | Remove generated outputs plus `node_modules` folders |

## Docs

- [Article: Build a LangChain.js RAG Assistant with Oracle AI Database](./docs/article.md)
- [Local development](./docs/local-development.md)

## What Is Intentionally Not Here

- Production authentication. The sample is local-first.
- A production embedding provider. The deterministic demo embeddings keep runs reproducible; swap in OpenAI, OCI Generative AI, or another LangChain.js `Embeddings` implementation for real applications.
- A production table lifecycle. The seed script drops and recreates the configured demo table, so do not point `ORACLE_TABLE_NAME` at a production table.
- A separate vector database. Oracle AI Database is the vector store in this sample.

## Learn More

- [Oracle LangChain JavaScript integration guide](https://docs.oracle.com/en/database/oracle/oracle-database/26/aintg/langchain-oracledb-integration-guide/langchain-javascript.html)
- [LangChain.js Oracle AI Database vector store docs](https://docs.langchain.com/oss/javascript/integrations/vectorstores/oracleai)
- [Source: oracle/langchain-oracle](https://github.com/oracle/langchain-oracle/tree/main/libs/js/langchain-oracledb)
