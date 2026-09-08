# TanStack Chat + Oracle 26ai Select AI

Copyright (c) 2024 Oracle and/or its affiliates.

A chat application built with TanStack Start and TanStack AI that connects to an Oracle 26ai Autonomous Database via Select AI. The outer LLM (Claude, GPT-4o, Gemini, or Ollama) decides when to query the database and asks questions in plain English. The inner LLM inside Oracle (Select AI) translates those questions to SQL, executes the query, and returns a narrated answer.

```
Browser  ->  TanStack Start  ->  TanStack AI chat handler
                                        |
                                  Outer LLM (Claude / GPT-4o / etc.)
                                        | (tool call: execute_query)
                                  oracledb thin client (Node.js)
                                        | (TLS)
                                  Oracle 26ai Autonomous DB
                                        | (DBMS_CLOUD_AI.GENERATE)
                                  Select AI  ->  Anthropic Claude (in-DB)
                                        |
                                  SQL generated + executed inside DB
                                        |
                                  Natural language answer returned
```

## Prerequisites

- [Node.js](https://nodejs.org/) (current LTS recommended)
- [pnpm](https://pnpm.io/) (`corepack enable` or install globally)
- An **Oracle Cloud** account with an Always Free Autonomous AI Database provisioned (26ai, ATP workload, mTLS off / TLS only)
- An **Anthropic API key** (used both by the app's outer LLM and by Select AI inside the database)

## Quick start

```bash
pnpm install
cp .env.example .env.local
# Fill in your API keys and Oracle connection details in .env.local
pnpm dev
```

The app serves at [http://localhost:3000](http://localhost:3000).

## Environment variables

Copy `.env.example` to `.env.local` and fill in the values:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | At least one LLM key | Anthropic API key (checked first) |
| `OPENAI_API_KEY` | | OpenAI API key (fallback) |
| `GEMINI_API_KEY` | | Google Gemini API key (fallback) |
| `ORACLE_USER` | Yes | Database user (default: `shoestore`) |
| `ORACLE_PASSWORD` | Yes | Password for the database user |
| `ORACLE_CONNECTION_STRING` | Yes | TLS connection string from OCI Console |
| `ORACLE_AI_PROFILE` | Yes | Select AI profile name (default: `SHOESTORE_AI`) |

The chat route picks the first available LLM provider in order: Anthropic, OpenAI, Gemini, then local Ollama.

### Getting the Oracle connection string

1. Go to the OCI Console > Autonomous Database > your database
2. Click **DB Connection**
3. Select the **TLS** tab (not mTLS)
4. Copy the connection string for the `_low` service (least resource priority, fine for a demo)

## Database setup

### 1. Seed the database

Run `seed.sql` as **ADMIN** (first block creates the user and grants), then as **SHOESTORE** (tables + data). The easiest way is to paste it into **Database Actions > SQL Worksheet** in the OCI console.

Alternatively, using SQLcl:

```bash
# As ADMIN — creates user, grants, network ACL
sql admin/<password>@'<TLS connection string>'
@seed.sql
```

The seed script creates:
- **products** (20 rows) -- shoes across 5 categories (running, casual, hiking, basketball, skateboarding)
- **customers** (15 rows) -- spread across US cities/states
- **transactions** (40 rows) -- purchases with completed, returned, and pending statuses
- Table and column comments that Select AI uses to understand the schema

### 2. Configure Select AI

Run `setup-selectai.sql` as the **SHOESTORE** user. Before running, replace `<your-anthropic-api-key>` with your actual Anthropic API key:

```bash
sql shoestore/<password>@'<TLS connection string>'
@setup-selectai.sql
```

This creates:
- An Anthropic credential stored encrypted in the database
- A Select AI profile (`SHOESTORE_AI`) pointing at the three tables
- A verification query to confirm it works

### Select AI actions reference

| Action | What it does | When to use |
|--------|-------------|-------------|
| `narrate` | Generates SQL, executes it, returns natural language summary | Default for our chat tool |
| `runsql` | Generates SQL, executes it, returns raw rows | When the app needs structured data |
| `showsql` | Returns the generated SQL without executing | Debugging / transparency |
| `chat` | General conversation with the LLM (no SQL) | Off-topic questions |

## How it works

When a user asks a data question in the chat:

1. The **outer LLM** (TanStack AI) decides to call the `execute_query` tool with a plain English question
2. The app sends that question to Oracle via `DBMS_CLOUD_AI.GENERATE` using the `oracledb` thin client
3. **Select AI** (the inner LLM inside Oracle) generates SQL from the question using table/column comments as context
4. The SQL executes inside the database and Select AI narrates the results
5. The narrated answer returns to the outer LLM, which incorporates it into its response

The outer LLM never writes SQL. Table/column comments are the prompt engineering for Select AI -- the more descriptive the comments, the better the generated SQL.

## Demo queries to try

- "How many products do we carry?"
- "What's our most expensive shoe?"
- "Who are our customers from Oregon?"
- "What are the top selling brands by revenue?"
- "Show me all returned orders"
- "Which customer has spent the most money?"
- "What category of shoes sells the best?"
- "Are there any pending orders?"
- "What should a customer from Gresham buy based on what's popular in their area?"
- "Compare running shoe sales vs hiking shoe sales"

## Building for production

```bash
pnpm build
pnpm preview
```

## Testing

```bash
pnpm test
```

## Cleanup

To tear down Select AI config without dropping the database, run as SHOESTORE:

```sql
BEGIN
  DBMS_CLOUD_AI.DROP_PROFILE(profile_name => 'SHOESTORE_AI', force => true);
END;
/

BEGIN
  DBMS_CLOUD.DROP_CREDENTIAL(credential_name => 'ANTHROPIC_CRED');
END;
/
```

To drop the user entirely, run as ADMIN:

```sql
DROP USER shoestore CASCADE;
```

## Tech stack

- **Framework**: TanStack Start + TanStack Router (file-based routing)
- **AI**: TanStack AI with Anthropic/OpenAI/Gemini/Ollama adapters
- **Database**: Oracle 26ai Autonomous DB with Select AI (`DBMS_CLOUD_AI`)
- **DB Client**: `oracledb` v6+ thin mode (pure JS, no Oracle Client install needed)
- **Styling**: Tailwind CSS
- **Language**: TypeScript

## License

Licensed under the Universal Permissive License (UPL), Version 1.0.

See [LICENSE](LICENSE) for more details.

ORACLE AND ITS AFFILIATES DO NOT PROVIDE ANY WARRANTY WHATSOEVER, EXPRESS OR IMPLIED, FOR ANY SOFTWARE, MATERIAL OR CONTENT OF ANY KIND CONTAINED OR PRODUCED WITHIN THIS REPOSITORY, AND IN PARTICULAR SPECIFICALLY DISCLAIM ANY AND ALL IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE. FURTHERMORE, ORACLE AND ITS AFFILIATES DO NOT REPRESENT THAT ANY CUSTOMARY SECURITY REVIEW HAS BEEN PERFORMED WITH RESPECT TO ANY SOFTWARE, MATERIAL OR CONTENT CONTAINED OR PRODUCED WITHIN THIS REPOSITORY. IN ADDITION, AND WITHOUT LIMITING THE FOREGOING, THIRD PARTIES MAY HAVE POSTED SOFTWARE, MATERIAL OR CONTENT TO THIS REPOSITORY WITHOUT ANY REVIEW. USE AT YOUR OWN RISK.
