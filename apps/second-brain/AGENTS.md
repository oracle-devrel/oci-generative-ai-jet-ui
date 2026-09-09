# Instructions for AI coding agents

You (an AI coding agent — Claude Code, Cursor, Codex, or similar) have been handed this
repo to set up, adapt, or extend a **second brain**: one Oracle database holding your
user's content, searchable by meaning, with a self-compiling wiki, agent memory, and an
MCP server. Everything below is what a maintainer would tell you on day one.

## What to read first

- `README.md` — the build, in order. The Quickstart IS the setup procedure; run it
  top to bottom rather than improvising your own.
- `README.md` → "Build yours with your AI" — if your user wants THEIR version (their
  sources, their questions), start from those three prompts: interview → plan first.
- `docs/EXPORT_GUIDE.md` + any loader in `scripts/` — the pattern for adding a source.
- `SECURITY.md` — before anything touches real data or the internet.

## The rules (non-negotiable)

1. **Secrets never enter files or chat.** Credentials live in `oracle/.env` (gitignored)
   or the OS keychain (`keychain:<item>` values — see `oracle/agent/keychain_secrets.py`).
   Never print token values, never commit `.env`, never paste keys into your transcript.
2. **Privacy is structural — keep it that way.** Every read path filters
   `visibility='content'`. If you write a new query over `posts`/`content_chunks`,
   include the visibility filter. Private/business items must stay out of search, the
   wiki compiler, memory consolidation, AND anything you add.
   The column's values: `'content'` = searchable everywhere; anything else
   (`'business'`, `'archived'`, or a label of the user's choosing) is excluded from
   every read path, and the cloud-copy script ships only `'content'`. If the user's
   most valuable questions are ABOUT their private data, plan a local-only query path
   for that scope — don't widen the default filters.
   The **memory layer** carries the same contract: `agent_memory` and `conversations`
   have a `visibility` column too, tagged at write time by the deterministic deny-list
   (`oamp_memory.violates_privacy`) and filtered to `'content'` on every read — so a
   private detail the agent saw never resurfaces in its recall, a shared memory view, or
   the working-memory window. Any new memory write/read keeps that filter. (Semantic and
   procedural memory need no column: the consolidator distills only from content-scope
   posts, and tool definitions hold no private data.)
3. **Run the tests after any change:** `./.venv/bin/python tests/test_brain.py`
   (needs the local DB from the Quickstart running). All green before you call it done.
4. **Run the matching eval when you touch quality-bearing code:**
   - retrieval/search changes → `tests/eval_retrieval.py`
   - agent answer/verify changes → `tests/eval_grounding.py`, `tests/eval_verify.py`
   - privacy classifier changes → `tests/eval_classifier.py`
   - memory backend changes → `tests/eval_oamp.py`
   The golden sets in `tests/*.json` work on the sample data; encourage your user to
   grow their own once real content is loaded.
5. **Every loop earns its keep.** A new source, agent, or scheduled job ships with an
   eval that proves it works or a report your user will actually read (see
   `docs/LOOP_ENGINEERING.md`). Don't add silent automation.
6. **No self-modification patterns.** Agents here never rewrite their own prompts or
   code at runtime; scheduling stays deterministic (`scripts/sync.py` + cron/launchd).
   Keep that property — it's what makes the system auditable with plain SQL.
7. **Don't scrape platforms.** Loaders use official APIs and user-requested exports
   only. If a platform has neither, the answer is "not yet," not a headless browser.

## Common tasks, the sanctioned way

- **Add a source/loader:** copy the closest loader in `scripts/` (they all normalize
  into the same `posts` + `content_chunks` shape, embed in-database, and set
  `visibility` on insert). Delete+reload should be one transaction. Add a golden case
  or make sure its output lands in the user's freshness/report flow (rule 5).
- **Change retrieval:** `oracle/agent/content.py` (hybrid = vector + keyword, RRF
  fusion). Run `eval_retrieval.py` before/after and compare.
- **Touch the MCP server:** `oracle/agent/mcp_server.py`. Read tools get
  `readOnlyHint`; write tools must stay gated and unregistered under `MCP_READONLY=1`.
  `tests/test_brain.py` pins the exact public tool list — update it deliberately.
- **Set up the database:** don't hand-roll SQL; `oracle/bootstrap.sh` applies the
  schema idempotently. The schema files assume the `CCC` schema — restoring into
  another schema name requires stripping the `current_schema` lines.
- **Need a throwaway schema next to the real one** (safe experiments, drills)?
  As SYSTEM: `create user X identified by ...; grant connect, resource, create view
  to X; grant read on directory VEC_MODELS to X; grant create mining model to X;`
  then apply the schema files with the `current_schema` lines stripped
  (`sed '/current_schema/Id'`) and load MINILM as X. Drop the user when done.
- **Deploy the hosted server:** `docs/HOSTED_MCP.md`. Auth is fail-closed by design —
  if the server refuses to start, that's the feature. Never "fix" it with
  `MCP_ALLOW_ANON` on a public host.

## Enforcement, not just instructions

The rules above are Tier 1: text you read and follow. This repo also ships Tier 2 —
enforcement that doesn't depend on you remembering:

- **Env-guard hook (paste into `.claude/settings.json` in your copy):** this hub's
  root `.gitignore` excludes `.claude/`, so the hook file can't ship inside this
  snapshot — create it yourself before letting an agent loose. It carries a PreToolUse
  hook that BLOCKS any agent edit to a `.env`-style file (`.env`, `foo.env`,
  `.env.local`, … — `.env.example` stays editable), with the reason returned to you.
  Claude Code asks the user to approve project hooks on first use — approving is
  recommended. Other tools (Cursor, etc.): wire the same guard into your tool's
  equivalent hook mechanism; the command is plain python3 reading the tool call as
  JSON on stdin. The canonical repo
  ([LindaHaviv/second-brain](https://github.com/LindaHaviv/second-brain)) ships this
  exact file at `.claude/settings.json`; copy it verbatim:

  ```json
  {"hooks": {"PreToolUse": [{"matcher": "Write|Edit|MultiEdit|NotebookEdit",
    "hooks": [{"type": "command",
    "command": "python3 -c \"import json,sys,os; d=json.load(sys.stdin); p=str(d.get('tool_input',{}).get('file_path','')); b=os.path.basename(p); hit=(b.endswith('.env') or b.startswith('.env')) and not b.endswith('.env.example'); sys.exit(0) if not hit else (sys.stderr.write('BLOCKED by repo hook: '+p+' is a secrets file. Real values belong in the user-managed .env (never written by an agent, never committed); document new variables in oracle/.env.example instead.'), sys.exit(2))\""}]}]}}
  ```
- **Opt-in hook (paste into `.claude/settings.local.json` if you want tests enforced,
  not just requested):** run the suite whenever the agent finishes a turn. Caveat: it
  needs the local database running, so enable it only after the Quickstart works.

  ```json
  {"hooks": {"Stop": [{"hooks": [{"type": "command",
    "command": "./.venv/bin/python tests/test_brain.py"}]}]}}
  ```

- Everything deeper is enforced below the agent layer entirely: the `visibility`
  filter runs in the database, auth fails closed, `MCP_READONLY` unregisters write
  tools. You can't skip those even if you ignore this file — that's the design.

## Verifying your work (in order of strength)

1. Unit tests green (rule 3).
2. The relevant eval didn't regress (rule 4).
3. The feature demonstrated end-to-end: load → search → correct answer with the
   user's real question, not a synthetic one.
4. Ask the brain itself: the MCP `overview` / `source_status` tools report what's
   loaded and how fresh — use them to check your own ingestion landed.
