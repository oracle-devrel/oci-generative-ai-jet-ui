# Cloud migration — local Oracle 26ai → Oracle Autonomous AI Database

Move the brain to a managed, always-on cloud database (encrypted, auto-backed-up, reachable from
a hosted MCP server). The app code is already cloud-ready — `db.py` connects to Autonomous over an
mTLS wallet when wallet env vars are set, with **no other code changes.** You do the provisioning
(your Oracle Cloud account); everything else is the steps below.

> Local stays fully working and private. You can run cloud and local side by side.

---

## Phase 1 — Provision the database (OCI console)
1. Sign in to **cloud.oracle.com** — or **create a free account** there if you don't have one
   (the **Always Free** tier is enough for everything in this guide; no paid upgrade needed).
   One tier rule worth knowing: Oracle **auto-stops** an Always Free instance that sits idle for
   7 days (one click to restart) and can reclaim one left inactive for ~90 days — the daily sync
   in this repo is exactly the activity that keeps yours awake.
2. **Autonomous Database → Create Autonomous Database.**
   - Workload type: **Transaction Processing** (or "AI").
   - **Always Free**: on.
   - Database version: **26ai** (some region consoles still label it 23ai — either works here).
   - Set the **ADMIN password** (save it).
3. When it's **Available**, open it → **Database Connection → Download Wallet** (Instance Wallet).
   Set a **wallet password** (save it). **Unzip** it to a folder, e.g. `~/brain-wallet/`.
   - It contains `tnsnames.ora` (connection aliases like `mybrain_high`) and `ewallet.pem`.

## Phase 2 — Create a least-privilege app user
Open **Database Actions → SQL** (web worksheet) on the ADB, signed in as **ADMIN**, and run:
```sql
CREATE USER CCC IDENTIFIED BY "<StrongPwd>";
GRANT CREATE SESSION, RESOURCE, CREATE VIEW, CREATE MINING MODEL TO CCC;
ALTER USER CCC QUOTA UNLIMITED ON DATA;
-- for loading the ONNX model from object storage later:
GRANT EXECUTE ON DBMS_CLOUD TO CCC;
GRANT READ, WRITE ON DIRECTORY DATA_PUMP_DIR TO CCC;
```
> Least privilege on purpose — the app never runs as ADMIN.

## Phase 3 — Point the app at the cloud
In `oracle/.env` (gitignored), add:
```bash
DB_DSN=mybrain_high                 # an alias from the wallet's tnsnames.ora
DB_USER=CCC
APP_PWD=<StrongPwd>
DB_WALLET_DIR=/Users/you/brain-wallet
DB_WALLET_PASSWORD=<wallet password>
```
Test the connection:
```bash
cd oracle/agent && ../../.venv/bin/python -c "import db; print(db.connect().cursor().execute(
  \"select 'connected to '||sys_context('userenv','con_name') from dual\").fetchone()[0])"
```

## Phase 4 — Apply the schema (one command)
With the cloud env set (Phase 3), run the applier — it builds all 8 schema layers over the wallet
connection, in the connected user's schema:
```bash
./.venv/bin/python scripts/apply_schema.py
```
Idempotent (re-runnable). Creates the content/Duality tables, all four memory types, content
chunks, and the wiki layer. No manual SQL pasting.

## Phase 5 — Load the embedding model (direct BLOB — no Object Storage needed)
```bash
./.venv/bin/python scripts/load_model_cloud.py
```
This streams `oracle/models/all_MiniLM_L12_v2.onnx` straight into the database as a BLOB and
registers it as `MINILM` via `DBMS_VECTOR.LOAD_ONNX_MODEL`, then verifies an embedding — so no
bucket, no Pre-Authenticated Request, no `DBMS_CLOUD.GET_OBJECT`.
(If you'd rather stage it in Object Storage instead, that path is in the git history.)

## Phase 6 — Load your data (re-ingest from your local sources)
Cleanest path: with the cloud env set (Phase 3), re-run the loaders — embeddings regenerate in-DB
on the cloud, so nothing else changes:
```bash
./.venv/bin/python scripts/youtube.py
./.venv/bin/python scripts/youtube_transcripts.py
./.venv/bin/python scripts/notion.py          # your private loaders
./.venv/bin/python scripts/claude_chats.py
./.venv/bin/python scripts/claude_code.py
cd oracle/agent && ../../.venv/bin/python wiki.py     # recompile the wiki in the cloud
cd ../.. && ./.venv/bin/python scripts/consolidate.py  # re-consolidate semantic memory
```
> Alternative: Oracle Data Pump / `DBMS_CLOUD` to move tables directly — heavier; re-ingest is
> simpler and reproducible (and it's what the tutorial shows).

## Phase 7 — Lock it down (security)
- **Wallet is a secret** — keep `DB_WALLET_DIR` outside the repo; never commit it (already gitignored).
- **Access control:** ADB → Network → restrict to an **access-control list** (your IP / the MCP
  host's egress) once the hosted MCP server is up.
- **Rotate** the ADMIN + CCC passwords and wallet on a schedule.
- The hosted **MCP server** (separate step — see [ARCHITECTURE.md](ARCHITECTURE.md)) is what then
  exposes this cloud brain to Claude/ChatGPT, with its own bearer auth.

---

### What's already done for you
`db.py` auto-detects the wallet env and connects over mTLS — so **all** the loaders, the agent,
the wiki, and the MCP server work against the cloud DB unchanged. Flip the env vars and you're on
cloud; remove them and you're back to local.

### The memory package on Autonomous (first run)
On the default memory backend, the first agent run against the cloud auto-creates the
`BRAIN_*` tables **and a hybrid vector index** — no extra setup. Two things to expect:

1. You may see one `[error] DatabaseError while executing managed schema DDL; details
   suppressed` line during that first run. It's a **benign retry inside the package's
   schema setup** — verify everything landed with:
   ```sql
   SELECT index_name, status FROM user_indexes WHERE table_name = 'BRAIN_RECORD_CHUNKS';
   -- expect: BRAIN_RECORD_CHUNKS_CONTENT_HVX_I  DOMAIN  VALID
   ```
2. Do that first run as a deliberate **warm-up** (one throwaway question) rather than
   inside something time-sensitive — schema + index creation adds ~a minute, once.

After the flip, the daily `sync.py` automatically adds the **OAMP privacy sweep** as its
final step (run `scripts/oamp_sweep.py` by hand to check it), and `tests/eval_oamp.py`
on the local sandbox is the pre-flight before any package version upgrade.
