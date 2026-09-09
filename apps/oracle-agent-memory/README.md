# oracle-agent-memory

An AI agent that learns your social media voice over time, using three-layer agent memory in Oracle AI Database 26ai. Companion code for the blog post *"How I Taught an AI to Sound Like Me: Agent Memory with Oracle Database 26ai."*

## What it does

You give it a topic and a platform; it drafts a post that sounds like you. Every time you save a published post, it gets a little better at sounding like you, because of the three memory layers:

1. Episodic memory: Your posts are embedded and stored. Vector search retrieves the K most similar past posts as few-shot examples.
2. Semantic memory: a JSON object describing how you write (tone, sentence length, signature phrases, etc.) that gets injected into every draft prompt.
3. Reflection memory: Every 5 new posts, an LLM compares the recent posts against the current style profile and emits a structured diff to keep the profile current.

All three live in the same Oracle AI Database 26ai instance. Vectors, JSON, and relational rows in one place.

## Stack

- Backend: Node.js + Express, TypeScript, `oracledb` driver
- LLM: OCI Generative AI via `oci-generativeaiinference` (defaults to `cohere.command-r-plus-08-2024` for chat and `cohere.embed-english-v3.0` for embeddings; override with `OCI_CHAT_MODEL_ID` / `OCI_EMBED_MODEL_ID` if those rotate)
- Frontend: React + Vite, TypeScript
- Database: Oracle AI Database 26ai

## Setup

You need an OCI account with API signing keys configured locally (`~/.oci/config`). If you've never done that, see [`terraform/README.md`](./terraform/README.md) for the one-time steps.

### Path A: Terraform

Provisions an Always Free Autonomous AI Database and writes a populated `.env` for you.

```bash
git clone <repo-url> oracle-agent-memory
cd oracle-agent-memory
npm install

cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply

# Write the populated .env into the project root.
#   macOS / Linux / WSL:
terraform output -raw env_file > ../.env
#   PowerShell (forces UTF-8 without BOM; default `>` writes UTF-16 and dotenv chokes on it):
#   terraform output -raw env_file | Out-File ../.env -Encoding utf8NoBOM   # PS 7+
#   [IO.File]::WriteAllText("$PWD\..\.env", (terraform output -raw env_file))  # PS 5.1

cd ..
npm run schema   # creates the 3 tables + HNSW index
npm run seed     # loads data/linkedin-posts.json and seeds the style profile
npm run dev      # starts server (3001) + Vite client (5173)
```

### Path B: Existing database

If you already have an Oracle AI Database 26ai instance:

```bash
git clone <repo-url> oracle-agent-memory
cd oracle-agent-memory
npm install
cp .env.example .env
# edit .env with your existing Oracle + OCI credentials
npm run schema
npm run seed
npm run dev
```

Open http://localhost:5173 and start drafting.

## Project layout

```
oracle-agent-memory/
├── schema.sql                  -- DDL for posts, style_profile, reflections
├── data/
│   └── linkedin-posts.json     -- corpus of social posts
├── terraform/                  -- Always Free DB provisioning
├── shared/
│   └── types.ts                -- types shared between server & client
├── scripts/
│   ├── apply-schema.ts         -- npm run schema
│   └── seed-from-linkedin.ts   -- npm run seed
└── src/
    ├── server/
    │   ├── index.ts            -- express bootstrap
    │   ├── db.ts               -- oracledb connection pool
    │   ├── llm.ts              -- OCI GenAI client wrappers
    │   ├── memory.ts           -- the 3 memory layers + reflection
    │   ├── agent.ts            -- generatePost() composes a draft
    │   └── routes.ts           -- HTTP endpoints
    └── client/
        ├── index.html
        ├── main.tsx
        ├── App.tsx
        ├── api.ts
        ├── styles.css
        └── components/
            ├── PostComposer.tsx
            └── ProfileView.tsx
```

## HTTP API

| Method | Path | What it does |
|---|---|---|
| `GET` | `/api/me` | Return the demo `userId` from `DEMO_USER_ID` in `.env`. Called by the client on startup so the UI doesn't hardcode a user. |
| `POST` | `/api/draft` | Generate a draft for `{userId, platform, topic}` |
| `POST` | `/api/posts` | Save a published post — triggers reflection every 5 |
| `DELETE` | `/api/posts/:id` | Soft-delete (forget) a post |
| `GET` | `/api/profile/:userId` | Load the current style profile |
| `POST` | `/api/profile/:userId/seed` | Rebuild profile from scratch |
| `POST` | `/api/profile/:userId/reflect` | Manually trigger a reflection |

## Notes on the social media corpus

`data/linkedin-posts.json` should be your actual LinkedIn posts (one string per array element), so the agent learns your authentic voice rather than a synthetic one. Replace the file's contents with your own posts before running `npm run seed`.

`npm run seed` is **idempotent**: it deletes the existing posts, reflections, and style profile for the demo user before reloading, so re-running it always lands in the same clean state. Useful when iterating on prompts or schema.

## Privacy

Every query filters on `user_id`. If you run this multi-tenant, that pattern keeps users isolated. `forgetPost()` does a soft delete; swap to hard `DELETE` if you need GDPR-style erasure. Reflections keep a `posts_window` snapshot so if you delete a post that was referenced, consider whether to also recompute the affected reflections.

