# Quickstart: Agent Memory

Proves the feature end to end. Commands and outputs are in [contracts/cli.md](./contracts/cli.md), and the
`recall` result is in [contracts/tools.md](./contracts/tools.md).

## Prerequisites

- **Database and index**: the database is running, `ccctx db migrate` is applied (migration 8), and flask is
  ingested with the model loaded (`ccctx model load`).
- **Stop MCP clients before `uv sync`**: a running `ccctx mcp` holds `ccctx.exe` open on Windows, and the sync
  fails with os error 32. `uv sync` installs `oracleagentmemory`.
- **No model for steps 1 to 5**: leave `CCCTX_MEMORY_MODEL` unset. Every fact should then name `template/1` (SC-010).

## 1. Every call is a run (US1, SC-001)

```bash
npx @modelcontextprotocol/inspector ccctx mcp
```

In the Inspector, call these, in order:
- `search_code` with `{"query": "where is url_for defined", "repo": "flask"}`
- `get_symbol` with `{"name": "url_for", "repo": "flask"}`
- `find_callers` with `{"name": "url_for", "repo": "flask"}`
- `search_code` with `{"query": "how are sessions signed", "repo": "flask"}`
- `search_code` with `{"query": "where's url_for defined?", "repo": "flask"}`
- `search_code` with `{"query": "", "repo": "flask"}`: refused, still recorded

```bash
uv run ccctx memory list --repo flask --limit 10
```

**Expected**: six rows, newest first, each with its tool and question. The refused call shows `unavailable` and
its reason. The Inspector's results did not change.

## 2. Distil and merge (US2, SC-002, SC-003)

```bash
uv run ccctx memory consolidate --repo flask
uv run ccctx memory facts --repo flask
```

**Expected**:
- **Fewer facts than runs**: one fact for `url_for` citing all four `url_for` runs, one for the sessions answer, and
  none from the refused call.
- **Merged wording**: the `url_for` fact holds both wordings ("where is url_for defined" and "where's url_for
  defined?") and has confidence 0.938.
- **Traceable**: every run ID listed exists in `memory list`.

Consolidate again: `0 runs read, 0 created, 0 merged, 0 weakened, 0 stale, 0 re-asked`, and the facts are unchanged.

```bash
uv run ccctx search "url_for" --repo flask --limit 5
```

**Expected** (FR-021, SC-011): the two `url_for` definitions are still ranks 1 and 2, and rows of KIND `fact` for
`url_for` follow in the top 5, at their definitions' paths.

## 3. Memory keeps pace with the code (US3, SC-005)

In a scratch clone, never in `../ccctx-repos/flask`:

```bash
git clone ../ccctx-repos/flask /tmp/flask-memory && uv run ccctx repo add /tmp/flask-memory --name flaskmem
uv run ccctx ingest flaskmem
```

1. In the Inspector, ask about two functions in `flaskmem`: `get_symbol` on `url_for`, and on a small helper such
   as `get_load_dotenv`.
2. Consolidate.
3. Edit `url_for` (add a line to its body), delete `get_load_dotenv`, commit, and run `uv run ccctx ingest flaskmem`.

**Expected**:
- **Summary**: a `Memory` line with `1 stale, 1 re-asked`.
- **Edited symbol**: re-asking `get_symbol url_for` still finds `url_for`, so `memory facts --repo flaskmem` shows
  the `url_for` fact fresh at its new line range.
- **Removed symbol**: the `get_load_dotenv` fact is stale with `` `get_load_dotenv` was removed ``, and its
  confidence has halved.
- **A re-ask with a different answer**: rename `url_for` to `url_for_old` and add a new `url_for` in another file,
  then commit and ingest. The fact goes stale with ``re-asked "url_for": now answered by `url_for` `` at the new
  path, and its confidence halves.

## 4. Recall in a fresh session (US4, SC-006, SC-007)

Start a new session in a real client (Claude Code with this server configured) and ask: "what do you already know
about the flask codebase?"

**Expected**:
- **Only recall**: the client's tool log shows `recall` with `repo: "flask"`, and no `search_code` call.
- **Same facts**: the answer lists the facts from step 2.
- **Size and speed**: in the Inspector, `recall` with `{"repo": "flask"}` answers in under 2 seconds and returns at
  most 20 facts and 10 runs.

## 5. With a configured model (FR-008, FR-008a, SC-010)

Set `CCCTX_MEMORY_MODEL` to a LiteLLM model string, plus its provider key, for example
`CCCTX_MEMORY_MODEL=anthropic/claude-sonnet-5-5` and `ANTHROPIC_API_KEY`. Then ask one new question in the Inspector
and consolidate.

**Expected**:
- **Distiller**: the new fact names `llm:anthropic/claude-sonnet-5-5`, and the consolidate line counts it under that
  distiller.
- **Unchanged decisions**: its subject, runs and confidence are the same as the template distiller would give.
- **Fallback**: with an invalid key, consolidation still succeeds, the fact names `template/1`, and stderr has one
  warning about the model.

## 6. Regression

```bash
uv run pytest
uv run ruff check
```

**Expected**: all tests pass, and the retrieval evaluation's top-5 hit rate is unchanged (SC-009). Search is
untouched.

## Verified 2026-10-12

- **Step 1** (SC-001): 6 calls through the MCP Inspector CLI (`npx @modelcontextprotocol/inspector --cli uv run ccctx mcp`)
  gave 6 rows in `ccctx memory list --repo flask`, newest first, each with client `inspector-cli 2.10.1`. The blank
  query was recorded as `unavailable` with "the question is empty". The Inspector CLI refuses an empty `query=`
  argument itself, so a single space stood in for the empty question.
- **Step 2** (SC-002, SC-003): 6 runs became 4 facts. "where is url_for defined" and "where's url_for defined?" became
  one fact (0.750, runs 6563,6567). A second consolidation read 0 runs and changed nothing. With the facts present,
  `ccctx search "url_for" --repo flask` kept both definitions at ranks 1 and 2, with the `url_for` facts at ranks 3
  and 4. The live run also showed that the same bare name sent to `get_symbol` and `find_callers` resolves to
  different definitions. That was wrongly counted as a contradiction, and it was fixed: a contradiction is now the
  same tool and wording answered by other code (research R7).
- **Step 3** (SC-005): in a scratch clone (`flaskmem`), `Flask.url_for` was edited and `get_load_dotenv` removed. The
  ingest printed `Memory    0 runs read, 0 created, 0 merged, 1 weakened, 1 stale, 1 re-asked`. `Flask.url_for` stayed
  fresh at 1102-1223 (was 1102-1222). `get_load_dotenv` went stale with "`get_load_dotenv` was removed", at 0.250.
- **Step 4** (SC-006, SC-007): a fresh headless Claude Code session (`claude -p`, `--strict-mcp-config`, built-in tools
  off) asked "what do you already know about the flask codebase?". It called `recall` (`repo: flask, limit: 50`)
  first, then `list_repositories`, and no search tool. It answered with the 4 stored facts and their confidences.
- **Step 5** (SC-010): the template half passed, and every fact names `template/1`. The model half was run with local
  Ollama, `CCCTX_MEMORY_MODEL=ollama_chat/qwen3.5:9b`, so nothing left the machine. A new `get_symbol
  Flask.dispatch_request` run was distilled by the model in one call (about 220s). The fact names
  `llm:ollama_chat/qwen3.5:9b`, and its text was accurate against the source. It named `req.routing_exception`,
  `provide_automatic_options`, `self.view_functions[rule.endpoint]` and `view_args`, all from that source. Its
  subject, runs and confidence (0.5) are what the template would give. With `CCCTX_MEMORY_MODEL=ollama_chat/no-such-model:1b`, the
  fact was written by `template/1`, with one `memory_model_failed` warning, in 0.8s.
  - **First attempt:** every model text was rejected, because the identifier check only allowed names from the
    findings and questions, not the source the model had been sent. It was also misreading prose between unpaired
    backticks as names. Both were fixed (FR-008, research R13).
  - **Test pollution:** that attempt also showed the test suite's tool calls against flask being consolidated into
    flask's memory. tests/conftest.py now drops runs about real repositories, unless a test asks for
    `real_recording`.
- **Step 6** (SC-009): the full suite passes, and the retrieval evaluation stays at top-1 10/10 and top-5 10/10 with
  facts present.
