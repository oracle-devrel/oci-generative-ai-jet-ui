# Meridian Bank AML Agent — The Fraud Detection Use Case (One-Pager)

> **What the demo actually is:** a compliance analyst — `the Meridian Bank Enterprise Data Agent` — questioning a live Oracle AI Database 26ai about *real, deliberately planted* financial-crime signals. Every prompt you type is an AML investigation; every answer is grounded in data that was designed to be suspicious.

## The story

Meridian Bank is a fictional global retail bank with **60 branches** and **140 merchants** across four regions (AMERICAS, EUROPE, MIDDLE_EAST, ASIA_PACIFIC), **2,000 customers**, **2,650 accounts**, ~**3,000 cards**, ~**23,600 transactions** in the last 90 days, **900 loans**, **117 Suspicious Activity Reports (SARs)** — plus the AML operational tables (**sanctions screenings**, **beneficial owners**, **wire messages**, **login events**, **KYC documents**, **case notes**, **FX rates**).

The FINANCE schema is seeded so that a slice of transactions carries an AML story: `transactions.status` is `FLAGGED` or `BLOCKED` with a `flag_reason` explaining *which rule fired*. **That flag column is the fraud use case** — it's what turns a generic "query the bank database" demo into a money-laundering investigation.

## The five seeded AML patterns (the "fraud")

| Flag reason | What the pattern simulates | Typical story in the data |
|---|---|---|
| `STRUCTURING` | Cash deposits just under the **$10,000 CTR threshold**, repeated in a short window | Deposits of $8,000–$9,999 at branches/ATMs to dodge Currency Transaction Reports |
| `GEO_VELOCITY` | A card spends at home… then in a **far region hours later** (impossible travel) | Card-cloning / account takeover; one attempt is `BLOCKED` outright |
| `HIGH_RISK_COUNTRY` | Wire-outs to **elevated-risk corridors** (crypto exchanges, gold & forex, casinos, remittance) right after an inbound credit | Layering — moving funds to high-risk merchants shortly after money arrives |
| `RAPID_CASH_OUT` | Big inbound wire, then **ATM withdrawals drain the account within 48h** | Cash-out stage of laundering |
| `LARGE_CASH_DEPOSIT` | A single **> $50,000 cash deposit** with no plausible source | Structuring alternative; often precedes other activity |

Customer `risk_rating` (1–100) is hotter on the seeded bad actors; 15 **SAR_REPORTS** (compliance-only table) carry the narratives for exactly these customers — `STRUCTURING`, `GEO_VELOCITY`, etc. — in `UNDER_REVIEW` / `FILED` / `OPEN` states. A bank examiner would pick these 15 customers up immediately.

## How the agent "works a case"

Every demo prompt is an end-to-end AML workflow:

1. **Remember the schema** → `search_knowledge` retrieves scanner-built institutional knowledge of FINANCE (tables, columns, relationships) before any SQL is written.
2. **Query live data** → `run_sql` against `FINANCE.transactions` (read-only, schema-qualified). E.g. *"Which branch regions have the most FLAGGED or BLOCKED transactions?"* — the FLAGGED/BLOCKED + flag_reason columns do the AML work.
3. **Compute honestly** → `exec_js` (Oracle MLE — JavaScript running inside the database kernel) computes mean/median over flagged amounts instead of the model guessing.
4. **Investigate geography** → Oracle Spatial `SDO_WITHIN_DISTANCE` on `merchants.location` / `branches.location` (e.g. merchants within 1500 km of Dubai) — the same engine a real geo-velocity review uses.
5. **Pull the 360° view** → JSON Relational Duality Views: `get_document("account_dv", "7")` returns one JSON document joining account, branch, customer, cards, and transactions; `query_documents("account_dv", where=…)` filters flagged activity (e.g. all STRUCTURING in EUROPE).
6. **Cross-reference the world** → `search_tavily` pulls live news (sanctions, fraud rings, bank actions) and joins it to on-book exposure via `run_sql`.
7. **Work the queue autonomously** → notebook **Part 6** flips the direction of the demo: instead of asking questions, the harness builds the alert queue from `FINANCE`, assembles an evidence pack per alert, decides `ESCALATE` / `KYC_REVIEW` / `DISMISS` with a confidence and a written rationale, records every decision in `AGENT.AML_TRIAGE` and OAMP memory, and computes the impact on the bank. Guide: [`part-6-autonomous-aml-triage.md`](part-6-autonomous-aml-triage.md).

## The compliance boundary (what makes it a *bank* demo)

The agent acts as a **persona with clearance**, not the database as god: `agent` (STANDARD, masked), `cfo` (EXECUTIVE, everything), `analyst.east` / `analyst.west` (regional row filters + masked amounts), `ops.viewer` (forbidden customer/SAR tables). The harness *enforces* it — forbidden tables refused, masked columns come back `[REDACTED]`, rows outside the persona's regions are dropped. Only `compliance.officer`/`cfo`-level identities can read `SAR_REPORTS`. Denials are helpful: the agent names the persona, the missing privilege, and who could unblock it.

## Where it lives

- **Seed & schema:** `app/backend/db/seed_finance.py` (deterministic, `random.seed(42)`) — DDL, spatial metadata, duality views, AML patterns, SARs. Run by `app/scripts/seed.py`.
- **Data model:** `FINANCE.{branches, customers, accounts, cards, merchants, transactions, loans, sar_reports}` over `VECTOR(384, FLOAT32)`-indexed OAMP memory + `toolbox`/`skillbox`.
- **Agent loop:** `app/backend/agent/harness.py` (~370 lines) + `system_prompt.py` (money-in-cents, flag_reason semantics, identity rules).
- **Tools:** `app/backend/agent/tools.py` — `search_knowledge`, `run_sql`, `exec_js`, `get_document`, `query_documents`, `scan_database`, `search_tavily`, `focus_world`, DBFS scratchpad.
- **Notebook mirror:** `notebook_student.ipynb` builds the same harness primitive-by-primitive with hard-stop asserts.

*All monetary columns are integer USD CENTS (÷100 for dollars) — a data-quality trap the agent is explicitly trained to handle.*

---

## Architecture at a glance (high level)

The demo is **Agent = Model + Harness** on one database: a React/Socket.IO chat UI drives a ~370-line Python agent loop that retrieves vector-indexed tools, assembles context from OAMP memory + the skillbox manifest, calls the LLM (OCI GenAI by default; OpenAI as an optional mid-turn fallback), and dispatches tools that run *entirely inside Oracle AI Database 26ai* — hybrid retrieval on `VECTOR(384, FLOAT32)` + HNSW, in-DB ONNX embeddings/reranking, Oracle MLE JavaScript, DBFS scratchpad, Oracle Spatial on `SDO_GEOMETRY`, JSON Relational Duality Views, and persona-based row/column authorization.

- **Diagram (Excalidraw, shareable):** https://excalidraw.com/#json=iAjKM7zP9mKKOADMYNtLj,8p5kQ15osB9FDHPqarGJSg
- **Diagram source files:** `docs/architecture-high-level.excalidraw` (editable scene) · `images/architecture-excalidraw.png` (rendered)