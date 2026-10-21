# Part 1: Setup & connectivity

## What you are building

An **AML / financial-crime data agent** for Meridian Bank: a small loop on top of Oracle AI Database 26ai that lets an investigator ask natural-language questions of live transaction data without learning the schema.

The formula:

```text
Agent = Model + Harness
```

The model emits tokens. Everything else — state, memory, tool dispatch, identity, budgets, retry logic — is **harness code**. Most "agent quality" complaints are harness problems, not model problems. Part 1 connects the notebook to Oracle; Parts 2–5 implement the harness; Part 6 runs it unattended.

## Canonical environment

The workshop uses **two** database users, and the split is the trust boundary:

| Oracle user | Owns | Used by |
|---|---|---|
| `SYS` | the entire database (super-user) | one-time bootstrap only |
| `AGENT` | harness state — OAMP memory tables, `toolbox`, `skillbox`, the DBFS scratchpad | every notebook cell |
| `FINANCE` | Meridian Bank business data — `branches`, `customers`, `accounts`, `cards`, `merchants`, `transactions`, `loans`, `sar_reports`, plus `account_dv` / `customer_dv` | the agent, via read-only `run_sql` |

`AGENT` is granted `SELECT` on `FINANCE`; it cannot write there. If a hostile prompt got the agent to issue `DROP TABLE`, it could only drop something `AGENT` owns.

In Codespaces, `.devcontainer/provision.sh` boots Oracle, then runs — on every launch, and only for the layers that are missing — the four provisioning scripts in order:

| Script | What it provisions |
|---|---|
| [`app/scripts/bootstrap.py`](../app/scripts/bootstrap.py) | `AGENT` user, `vector_memory_size`, the in-DB ONNX embedder, DBFS |
| [`app/scripts/seed.py`](../app/scripts/seed.py) | the `FINANCE` schema, the AML seed data, the duality views, the skillbox |
| [`app/scripts/setup_advanced.py`](../app/scripts/setup_advanced.py) | the Oracle Text index and the scheduler job |
| [`app/scripts/setup_deep_security.py`](../app/scripts/setup_deep_security.py) | the identity rules (Deep Data Security on Enterprise-class, `DBMS_RLS` on Free) |

`.devcontainer/start_app.sh` runs the same provisioner before starting the Flask backend on port 8000 and the React UI on port 3000. Everything is idempotent and safe to re-run; a fully provisioned database costs a few `SELECT`s (`bash .devcontainer/provision.sh --probe-only` prints what it finds).

| Setting | Default |
|---|---|
| Database DSN | `localhost:1521/FREEPDB1` |
| SYS password | `OraclePwd_2025` |
| Agent user / password | `AGENT` / `AgentPwd_2025` |
| Demo user / password | `FINANCE` / `FinancePwd_2025` |
| Required embedder | `ALL_MINILM_L12_V2` (384 dimensions) |
| Reranker | `RERANKER_ONNX` |
| Running app | `http://localhost:3000` |

## Models and the network boundary

`ALL_MINILM_L12_V2` is loaded *inside* Oracle and called with `VECTOR_EMBEDDING(...)`, so embedding and retrieval never call a hosted vector service. `RERANKER_ONNX` is called through `PREDICTION(...)`. Both live where the data lives: same backups, same audit, same security model.

The chat model is selected with `LLM_PROVIDER`:

- `oci` (the workshop default) uses `OCI_GENAI_API_KEY` (plus `OCI_GENAI_API_KEY_2..6`) against OCI GenAI's OpenAI-compatible endpoint. The shared `oci_key_rotation.py` router adds an invisible fallback chain (instructor note): `grok-phx` (Phoenix keys) → `grok-chi` (Chicago, `OCI_GENAI_FALLBACK_ENDPOINT` + `OCI_GENAI_FALLBACK_API_KEY..6`) → `gptoss-chi` (`OCI_GENAI_BACKUP_MODEL`, default `openai.gpt-oss-120b`). A rate-limited lane cools for `OCI_GENAI_FALLBACK_COOLDOWN_S` (default 120 s) and the next call retries it; a bad key is rotated within its lane. Switches are logged as JSON lines to `OCI_GENAI_ROUTER_LOG` (default `~/.cache/fraud-workshop/llm-router.log`), never printed to attendees. Without the fallback variables only the Phoenix lane runs. This is the only outbound network call in the whole harness.
- `openai` uses `OPENAI_API_KEY` instead.

The app normalizes a bare OCI regional endpoint by appending `/openai/v1`; the notebook does the same when it initializes its client, through the same shared helper.

## The two database parameters that matter

**`vector_memory_size`** — Oracle 26ai keeps HNSW vector indexes in a dedicated in-memory pool. On a stock Free image it ships at `0`, so any `CREATE VECTOR INDEX ... ORGANIZATION INMEMORY NEIGHBOR GRAPH` raises `ORA-51962` and your retrieval silently degrades to full-table cosine scans. The bootstrap allocates 512 MiB at SPFILE scope; the first time it does so Oracle needs a restart, which the devcontainer handles.

**`pga_aggregate_limit`** — the cross-encoder reranker allocates enough transient PGA per call that the Free build's default ceiling (2 GiB) can be exceeded under load, surfacing as `ORA-04036`. Nothing in the provisioning scripts changes it: if you see `ORA-04036`, raise it by hand to 4 GiB at the CDB level ([troubleshooting](troubleshooting.md)).

`vector_memory_size` is configured for you. It is explained here so you know what to look up if you hit `ORA-51962` against a non-Codespaces database.

## Connect in the notebook

Part 1 has one TODO (§1.3). Run the import and connection cells from the repository root:

```python
SYS_DSN    = "localhost:1521/FREEPDB1"
AGENT_USER = "AGENT"
AGENT_PASS = "AgentPwd_2025"
DEMO_USER  = "FINANCE"

agent_conn = connect(AGENT_USER, AGENT_PASS, SYS_DSN)
```

The `connect` helper retries because a Docker healthcheck can pass before Oracle's listener is ready to accept application sessions. 

### §1.2 Preflight

The connection cell is followed by a **preflight**: a dozen fast queries against the same catalogs the scanner will read, plus the LLM credentials. It reports FINANCE's tables and the AML rows in the seed, the in-database ONNX embedder and reranker, the OAMP memory table, the Oracle Text index, `toolbox` / `skillbox`, and the API keys.

Each ❌ row prints the command that fixes it (`cd app && python scripts/bootstrap.py && python scripts/seed.py` for a missing seed, the Codespaces-secret instructions for a missing key). Only two failures stop the notebook — no `FINANCE`, no embedder — because everything from Part 2 on depends on those. If the preflight is green, the rest of the workshop has what it needs.

If you want to see *how* Oracle was provisioned, read `app/scripts/bootstrap.py`, `seed.py`, `setup_advanced.py`, and `setup_deep_security.py` — the Codespace runs exactly those four, in that order, whenever a layer is missing (`.devcontainer/provision.sh`; whatever is already in place is left alone). `seed.py` itself is not idempotent — it drops and recreates `FINANCE`, including its policies — which is why `setup_deep_security.py` always runs after it.

### Kernel dependencies

The workshop kernel is the Codespace's Python 3.11 (`/usr/local/bin/python`, `pip install -r requirements.txt -r app/backend/requirements.txt`). The notebook needs `numpy`, `oracledb`, `openai`, `oracleagentmemory` and `langchain_oracledb` (Part 3). §1.2 prints each version; if the preflight says a version is unknown, re-run the Codespace's build step (`bash .devcontainer/setup_build.sh`) rather than pip-installing into a different interpreter.

## TODO 1: `QUESTION`

§1.3: set `QUESTION`, run the cell, read the answer. No memory, retrieval or tools: this is the bare model, the baseline Part 5 wraps in a context block and a dispatch loop.

**Solution:**

```python
QUESTION = "In one sentence: what does an AML 'structuring' pattern look like in transaction data?"
```

The checkpoint at the end of the cell fails until `QUESTION` is non-empty and the model answers. With OCI as the provider, the call goes through the model router, so a rate limit or outage is absorbed by the fallback chain before the cell raises.

## Verify the running app

In another terminal:

```bash
curl http://localhost:8000/api/health
```

Then open the UI and confirm the header shows the **Analyst (default)** persona:

<http://localhost:3000>

If the app is not serving:

```bash
bash .devcontainer/start_app.sh
tail -60 .devcontainer/logs/backend.log
tail -40 .devcontainer/logs/frontend.log
```

## Key takeaways — Part 1

- **Agent = Model + Harness.** The model emits tokens; everything else (state, dispatch, memory, identity, budgets) is harness code.
- **Separate the agent's DB user from the data's DB user.** `AGENT` owns harness state; `FINANCE` owns the bank data. The trust boundary is grants, not Python code — and it makes the persona demo in the app real.
- **`vector_memory_size` is non-optional for HNSW.** Without it, vector-index creation raises `ORA-51962`.
- **ONNX models load *into* the database.** Embeddings come from `VECTOR_EMBEDDING(...)` SQL calls, not network round-trips.
- **The AML use case already has opinions in the data.** `transactions.amount_cents` is USD **cents** and `customers.risk_rating` is a 1–100 score — both documented with `COMMENT ON COLUMN` so the scanner (§2.3) teaches the model those rules.

## Troubleshooting

**`ORA-12541: TNS:no listener`** — the Oracle container isn't ready yet. Wait 30 seconds and retry.

**`ORA-01017: invalid username/password`** — `AGENT` or `FINANCE` wasn't created; re-run `bash .devcontainer/provision.sh`.

**`ORA-51962: vector memory area is out of space`** — `vector_memory_size = 0`. Re-run `app/scripts/bootstrap.py`, restart Oracle, then restart the kernel.

See the [troubleshooting guide](troubleshooting.md) for more.
