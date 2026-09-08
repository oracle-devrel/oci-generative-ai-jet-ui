# Oracle Data Migration Harness

A worked example of an AI agent harness that moves a RAG corpus from MongoDB into Oracle AI Database 26ai. The migration preserves the AI workload (the vectors keep working) and unlocks new capabilities (SQL aggregation through JSON Relational Duality).

Built for the SuperFans Creator Lab at Oracle Redwood Shores, 12 May 2026.

> **Oracle AI Developer Hub layout:** this app is intended to live at `apps/oracle-data-migration-harness/`. The companion notebook is intended to live at `notebooks/oracle_data_migration_harness_walkthrough.ipynb`.

## What is in here

- `data_migration_harness/` — the harness, organised into nine modules that map to the nine harness layers (model, instructions, tools, environment, memory, context, orchestration, verify, governance).
- `ui/` — a split-pane React app showing the same RAG chatbot running before and after migration.
- `../../notebooks/oracle_data_migration_harness_walkthrough.ipynb` — a runnable companion notebook in the Oracle AI Developer Hub `notebooks/` directory, the slow-motion version of the app.
- `scripts/` — corpus seeding, embedding, and optional local response-cache generation.
- `tests/` — pytest suite covering connections, model wrapper, Mongo reader, duality, orchestrator, verify, and runtime cache behavior.

## Architecture, in one picture

Mongo on the left. Oracle on the right. A migrate button in the middle, with the seven-stage state machine running underneath:

```
+-----------------+        +-----------------------+        +--------------------+
| MongoDB         |        | seven-stage harness   |        | Oracle AI 26ai     |
| products        | -----> | plan, sample, schema, | -----> | products + reviews |
| (with vectors)  |  agent | dry_run, transfer,    |  agent | duality view       |
|                 |        | verify, reconcile     |        | VECTOR(384)        |
+-----------------+        +-----------------------+        +--------------------+
```

The agent uses Oracle's own published [migration skills](https://github.com/oracle/skills/tree/main/db/migrations) as its Layer 2 playbook. When it reaches `translate_schema` it reads the Mongo-to-Oracle skill, sees that JSON Relational Duality is the recommended approach, and applies it. That decision lights up in the orchestrator's narration and powers the demo's punchline.

## Quick start

You will need: Python 3.11+, Node.js, Podman or Docker, and OCI Generative AI access. The default configuration uses OCI Generative AI with `xai.grok-3-fast`; credentials are read from your local OCI config and `.env`.

```bash
make install            # python venv + npm install
cp .env.example .env    # fill in OCI_COMPARTMENT_ID and optional OCI_MODEL_ID
podman pull docker.io/gvenzl/oracle-free:latest        # ~3 GB
podman pull mongo:7
podman run -d --name oracle-free -p 1521:1521 -e ORACLE_PWD=migration_agent docker.io/gvenzl/oracle-free:latest
podman run -d --name mongo-demo -p 27017:27017 mongo:7

# Wait for Oracle to finish starting (look for "DATABASE IS READY TO USE!"):
podman logs -f oracle-free 2>&1 | grep -m1 "DATABASE IS READY TO USE"

# Create the demo Oracle user:
podman exec -i oracle-free sqlplus -L system/migration_agent@localhost:1521/FREEPDB1 <<EOF
CREATE USER migration_agent IDENTIFIED BY migration_agent;
GRANT CONNECT, RESOURCE, DB_DEVELOPER_ROLE TO migration_agent;
ALTER USER migration_agent QUOTA UNLIMITED ON USERS;
EXIT;
EOF

make seed               # 500 synthetic product reviews into Mongo
make embed              # local sentence-transformers, 384-dim vectors
make app                # FastAPI on port 8000
make ui                 # Vite on port 5173
```

Open <http://localhost:5173>. Click the wireless-headphones preset on the Mongo side; click Migrate; click the same preset on the Oracle side; click the second preset on Oracle to see the duality unlock chart. The first free-form chat request calls your configured LLM. If you want repeatable offline responses for a local rehearsal, run `make cache`; it writes `.cache/demo_cache.json`, which is intentionally ignored by git.

## Apple Silicon note

The official `container-registry.oracle.com/database/free` image fails on Apple Silicon Podman with `ORA-01096`. We use `docker.io/gvenzl/oracle-free:latest` (a community-maintained native arm64 build by Gerald Venzl) instead. Same database, same DSN, no platform flag required.

## Embedding model

Embeddings run locally with `sentence-transformers/all-MiniLM-L6-v2` (384 dims). No API call, no data leaves the machine. The same model is used on the Mongo side and the Oracle side so the chatbot finds the same answers after migration.

## Tests

```bash
make test
```

Eight test modules covering: environment connections, model wrapper, Mongo reader, duality unlock, orchestrator stage ordering and narration, verify and PII flag, and runtime cache behavior.

## Layers in one paragraph each

| Layer           | Module                                   | What it owns                                                 |
| --------------- | ---------------------------------------- | ------------------------------------------------------------ |
| 1 Model         | `data_migration_harness/model.py`        | Oracle Code Assist client (OpenAI-compatible).               |
| 2 Instructions  | `data_migration_harness/instructions/`   | Curated Oracle migration skills excerpts + system prompt.    |
| 3 Tools         | `data_migration_harness/tools/`          | Mongo reader, Oracle landing, Duality, Vector, DBFS.         |
| 4 Environment   | `data_migration_harness/environment.py`  | Connection pools, env vars, sandbox.                         |
| 5 Memory        | `data_migration_harness/memory/`         | Prior-run vector store and migrated corpus retrieval.        |
| 6 Context       | `data_migration_harness/context.py`      | Explicit prompt builder per call.                            |
| 7 Orchestration | `data_migration_harness/orchestrator.py` | The seven-stage state machine.                               |
| 8 Verification  | `data_migration_harness/verify/`         | Row count and content checks driven by the validation skill. |
| 9 Governance    | `data_migration_harness/governance.py`   | PII field flagging.                                          |

## Companion content

- Talk: SuperFans Creator Lab, 12 May 2026 (Oracle Redwood Shores).
- Blog: _Agent harness: the operating layer your AI agent is missing_ (Oracle Developers, link tbd).
- Notebook: `../../notebooks/oracle_data_migration_harness_walkthrough.ipynb` when installed in the Oracle AI Developer Hub.

## License

This application is licensed under Apache-2.0. The curated Oracle skills content in `data_migration_harness/instructions/*.md` retains its original UPL license notice; see `data_migration_harness/instructions/ORACLE_SKILLS_LICENSE.txt`.
