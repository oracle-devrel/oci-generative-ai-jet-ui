# Limitless Workflow

A Claude Code-first understanding machine powered by Oracle AI Database.

This workshop repo lets you:
- connect Oracle AI Database on OCI
- install the Oracle Python + `langchain-oracledb` integration stack
- load starter topic packs
- run a smoke test
- launch XP Builder from Claude Code
- optionally inspect the Obsidian memory console

## What you need before the workshop

- an OCI Free Tier account
- an Oracle AI Database on OCI
- the downloaded wallet for that database
- Python 3.12+ (3.13 preferred, 3.14 works with warnings)
- Claude Code
- optionally Obsidian for the memory-console bonus path

## How to prepare before the session

For the best workshop experience, attendees should arrive with four things ready:

1. an **OCI Free Tier** account
2. an **Oracle AI Database** running on OCI
3. the downloaded **wallet** for that database
4. the repo cloned locally with `.env` filled in

In practice, the attendee journey is:

- sign up for OCI Free Tier
- create or access an Oracle AI Database
- download the wallet from the database connection page
- clone this repo
- install dependencies
- fill in `.env` from `.env.example`
- run the smoke path
- launch XP Builder in Claude Code

If attendees do that before the session starts, they should be able to code along instead of spending the live session doing account setup.

## 5-minute quickstart

Use:
- `docs/quickstart.md`

Core command path:

```bash
python scripts/check_oracle_connection.py
python scripts/load_topics.py
python scripts/demo_smoke.py
```

Then open Claude Code in the repo root and run:

```text
/xp-builder agent-memory procedural-memory
```

## Advanced next step

```text
/xp-debrief agent-memory
/refresh-obsidian
/check-learning-state agent-memory
```

## Optional bonus

If you want the visual memory-console path:

1. download and install **Obsidian**
2. open the `Limitless/` folder as a vault
3. inspect:
   - dashboard
   - topic notes
   - Base
   - Canvas
   - graph

If the styling does not appear immediately, go to **Settings -> Appearance -> CSS snippets**, reload snippets, and ensure `limitless-cognitive-vault` is enabled.
