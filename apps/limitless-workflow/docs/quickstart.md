# Quickstart

## Before the workshop

For the best experience, complete the Oracle + wallet setup before the live session starts.

You need:
- an OCI Free Tier account
- an Oracle AI Database on OCI
- the downloaded wallet for that database
- Claude Code
- optionally Obsidian

## What attendees should do before the live session

For the smoothest code-along experience, try to complete these before the session begins:

- create an **OCI Free Tier** account
- create or access an **Oracle AI Database** on OCI
- download the **wallet** for that database
- clone this repo
- install Python dependencies
- fill in `.env` from `.env.example`

If you arrive with those steps already done, you should be able to spend the live session running the workflow instead of doing account setup.

## 1. Clone the repo and install dependencies

Clone the repo and install Python dependencies. This step is what actually pulls down the Oracle integration packages used by the workshop, including `langchain-oracledb`.

### macOS

```bash
git clone https://github.com/casius-connect/limitless-workflow.git
cd limitless-workflow
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows

```powershell
git clone https://github.com/casius-connect/limitless-workflow.git
cd limitless-workflow
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## 2. Create `.env`

Point the repo at your Oracle AI Database and wallet path.

Use `.env.example` as the base and fill in:
- `ORACLE_DSN`
- `ORACLE_USER`
- `ORACLE_PASSWORD`
- `ORACLE_WALLET_LOCATION`
- `ORACLE_WALLET_PASSWORD`
- `OBSIDIAN_VAULT_PATH=Limitless`

## 3. Run the smoke path

These commands prove your environment is connected, the Oracle integration packages are installed, and the starter content is loaded.

```bash
python scripts/check_oracle_connection.py
python scripts/load_topics.py
python scripts/demo_smoke.py
```

## 4. Optional workshop bootstrap helper

If you want the same checks in one shortcut:

```bash
python scripts/workshop_bootstrap.py
```

## 5. First Claude Code command

Once the environment is working, launch XP Builder from Claude Code.

```text
/xp-builder agent-memory procedural-memory
```

Fallback Python command:

```bash
python scripts/run_xp_builder.py --topic agent-memory --focus procedural-memory
```

## 6. Advanced next step

If you’re keeping up, you can debrief the session and inspect the memory update.

```text
/xp-debrief agent-memory
/refresh-obsidian
/check-learning-state agent-memory
```

## 7. Optional bonus — Obsidian

Obsidian is optional. It gives you a visual memory console, but it is not required for the core workshop path.

To use the bonus path:

1. download and install **Obsidian**
2. open the `Limitless/` folder in this repo as a vault
3. inspect:
   - `00 Dashboard.md`
   - `10 Topics/Agent Memory.md`
   - `Atlas/Concept Tracker.base`
   - `Atlas/Knowledge Map.canvas`

If the styling does not appear immediately:
- open **Settings -> Appearance -> CSS snippets**
- reload snippets
- ensure `limitless-cognitive-vault` is enabled

## 8. SQL verification

If you want to verify Oracle state directly, use Database Actions or another SQL client.

If you connect as `ADMIN`, run:

```sql
ALTER SESSION SET CURRENT_SCHEMA = LIMITLESS;
```

Then:

```sql
SELECT id, session_key, status, started_at, finished_at
FROM xp_sessions
ORDER BY id DESC
FETCH FIRST 5 ROWS ONLY;
```

```sql
SELECT c.label, ca.score_before, ca.score_after, ca.band_after, ca.delta, ca.trend, ca.created_at
FROM concept_assessments ca
JOIN concepts c ON c.id = ca.concept_id
ORDER BY ca.id DESC
FETCH FIRST 10 ROWS ONLY;
```

```sql
SELECT c.label, ce.hint_used, ce.confusion_note, ce.evidence_snippet, ce.created_at
FROM concept_evidence ce
JOIN concepts c ON c.id = ce.concept_id
ORDER BY ce.id DESC
FETCH FIRST 10 ROWS ONLY;
```
