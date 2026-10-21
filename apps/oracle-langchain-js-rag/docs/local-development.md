# Local Development

## Prerequisites

- Node.js 22 or later
- pnpm 10 or later
- One Oracle Database target with vector support: local Oracle Database Free / Oracle AI Database or Autonomous AI Database
- Optional: `OPENAI_API_KEY` for generated grounded answers

## Setup

```bash
pnpm install
cp .env.example .env
```

## Choose The Database Connection

The application uses `node-oracledb` thin mode through `@oracle/langchain-oracledb`. The code path is the same for local and Autonomous connections; only the `.env` values change.

### Option A - Local Oracle Database Free / Oracle AI Database

Use this path when you run Oracle Database locally, for example with a container exposing the listener on `localhost`.

```env
ORACLE_USER=<local-schema-user>
ORACLE_PASSWORD=<local-schema-password>
ORACLE_CONNECT_STRING=localhost:1521/FREEPDB1
ORACLE_TABLE_NAME=LC_JS_RAG_DEMO
```

This is the simplest path for local development because it does not require a wallet.

### Option B - Autonomous AI Database

Use this path when the schema is in Oracle Cloud. Autonomous Database connections commonly use mTLS, so keep the downloaded wallet in a stable local directory and point the app at it.

```env
ORACLE_USER=<autonomous-schema-user>
ORACLE_PASSWORD=<autonomous-schema-password>
ORACLE_CONNECT_STRING=<service-alias-from-tnsnames-or-full-connect-descriptor>
ORACLE_WALLET_LOCATION=<path-to-unzipped-wallet-directory>
ORACLE_WALLET_PASSWORD=<wallet-password-if-required>
ORACLE_TABLE_NAME=LC_JS_RAG_DEMO
```

Use the `_high`, `_medium`, or `_low` service according to your Autonomous Database setup. If the connect string, wallet location, or wallet password is wrong, `pnpm db:check` will fail before the app attempts to seed vectors.

For both targets, the schema must be able to create, insert into, select from, and drop the demo table. `pnpm db:check` verifies the connection; `pnpm seed` verifies the table and OracleVS path.

Optional LLM configuration is the same for every database target:

```env
OPENAI_API_KEY=<optional>
```

## Validate The Database

```bash
pnpm db:check
pnpm seed
```

Expected result:

- Oracle connection succeeds.
- The markdown knowledge base is inserted into `LC_JS_RAG_DEMO`.
- Vector index creation is optional.

## Run The App

Terminal 1:

```bash
pnpm dev:api
```

Terminal 2:

```bash
pnpm dev
```

Open:

```text
http://localhost:5173
```

The API runs on:

```text
http://localhost:8787
```

Use `/health`, `/api/status`, `/api/corpus`, and `/api/inspect` for quick API checks.

## Verify The RAG Workflow

After the app opens:

1. Open the Live Assistant tab.
2. Ask one of the suggested questions.
3. Change the metadata filter and retrieval mode.
4. Compare the retrieved evidence, distance scores, LangChain.js call, and representative Oracle vector-search SQL.
5. Open the Oracle Table tab to verify the row count, columns, and optional vector index metadata.

This keeps validation focused on the LangChain.js and Oracle AI Database integration rather than on screenshots.
