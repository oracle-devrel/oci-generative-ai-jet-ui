# Tasks: Agent Memory

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Data model**: [data-model.md](./data-model.md) | **Contracts**: [cli.md](./contracts/cli.md), [tools.md](./contracts/tools.md) | **Live checks**: [quickstart.md](./quickstart.md)

**Tests come first.** Constitution VI requires that every test task is written before the code it covers, and fails
first. Database tests run against the local database, like the existing suites (see `tests/test_wiki.py` for the
fixture-repository pattern and `tests/test_server.py` for `create_connected_server_and_client_session`).

**Order**: phases follow the stories' priorities. The three P1 stories come first: US1 records, US2 distils, US4
recalls. US3 (P2) keeps the memory in step with the code, and needs facts to exist.

**Shared files**: `memory.py` and `cli.py` grow in every story phase, so those phases run one after another.
Within a phase, `[P]` marks tasks that touch different files and can run together.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 to US4, from spec.md

## Path Conventions

Single package: `src/golestan_code_mcp/`, tests in `tests/`. Every path below is from the repository root.

---

## Phase 1: Setup

**Purpose**: the dependency, the version and the model settings.

- [X] T001 Add `oracleagentmemory>=26.8,<27` to `dependencies` in pyproject.toml, set the version to `1.2.0` in pyproject.toml and `__version__` in src/golestan_code_mcp/__init__.py, then run `uv lock` and `uv sync` with every MCP client stopped (a running `ccctx mcp` locks `ccctx.exe`, os error 32). Check that `uv run python -c "import oracleagentmemory"` works with Python 3.11. Files: pyproject.toml, src/golestan_code_mcp/__init__.py, uv.lock
- [X] T002 [P] Write failing tests for the memory model settings in tests/test_config.py (research R13):
  - **Unset**: `memory_model(env)` returns `None` when `CCCTX_MEMORY_MODEL` is unset or blank.
  - **Set**: it returns a `MemoryModel(model, base, key)`, with `key` hidden from `repr`.
  - **Optional parts**: `CCCTX_MEMORY_MODEL_BASE` and `CCCTX_MEMORY_MODEL_KEY` may be absent.
  - **Precedence**: values come from the environment over `.env`, like the database settings.
- [X] T003 Implement `MemoryModel` and `memory_model(env)` in src/golestan_code_mcp/config.py, and add the three settings, commented out with one line each on what is sent to the model, to .env.example. Files: src/golestan_code_mcp/config.py, .env.example

**Checkpoint**: `uv run pytest -q tests/test_config.py` passes and `uv run ccctx --help` still works.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the run tables and the package client every story uses. No story work starts until this phase is done.

- [X] T004 [P] Write failing migration 8 tests in tests/test_schema.py, per data-model.md:
  - **Columns and defaults**: both tables exist with every column. `called_at` defaults to now, `scoped` and
    `consolidated` default to false.
  - **Constraints**: `status` outside `ok|unavailable|error` is refused, and so is a duplicate `(run_id, repo_id)`.
  - **Cascades**: deleting a run removes its links, and deleting a repository removes its links but not the run rows.
  - **Package tables**: migration 8 also creates the package's `ccctx_mem_` tables (they exist in `user_tables`).
  - **Re-running** the migrations is a no-op, the package step included, and `schema.version` is 8.
- [X] T005 Add migration 8 "agent memory" to `MIGRATIONS` in src/golestan_code_mcp/schema.py (data-model.md):
  - **The run tables**: `ccctx_memory_runs` (JSON `arguments` and `results`, the `status` check constraint, index on
    `called_at`) and `ccctx_memory_run_repos` (primary key `(run_id, repo_id)`, both foreign keys
    `on delete cascade`, index `(repo_id, consolidated)`), each statement tolerating "already exists" like migrations
    1 to 7.
  - **A Python step**: `memory.create_package_schema(conn)`, last. `_run` gains a branch for callable statements,
    and the version row is still written only after every statement and step succeeded.
  - **Depends on T007**, because it needs `create_package_schema`.
- [X] T006 [P] Write failing tests for the package client in tests/test_memory.py (new file, docstring "Agent memory (010)"):
  - **Schema policy**: `memory.client(conn)` uses `SchemaPolicy.REQUIRE_EXISTING`. Against a schema whose package
    tables were dropped, it raises a clear error naming `ccctx db migrate`, and creates nothing.
  - **No model**: with no memory model configured, the client has no `llm`.
  - **Model**: with one configured, it gets an `Llm` with that model and `temperature=0`.
  - **Embedder**: with the embedding model loaded (`semantic._state`), the client gets an `OracleDBEmbedder` on
    `ALL_MINILM_L12_V2` with 384 dimensions. Without it, none.
  - **Lazy import**: importing `golestan_code_mcp.memory` does not import `oracleagentmemory` (check `sys.modules`
    in a subprocess).
- [X] T007 Create src/golestan_code_mcp/memory.py with `client(conn, env=None)` and `create_package_schema(conn)` (research R1):
  - **`client`**: imports `oracleagentmemory` inside the function and builds `OracleAgentMemory(connection=conn, table_name_prefix="ccctx_mem_", schema_policy=SchemaPolicy.REQUIRE_EXISTING, memory_extraction_config=MemoryExtractionConfig(extract_memories=False), embedder=..., llm=...)` from `config.memory_model` and the model check. A missing-schema error from the package is re-raised as a `ValueError` naming `ccctx db migrate`.
  - **`create_package_schema`**: the same construction once, with `SchemaPolicy.CREATE_IF_NECESSARY`.
 It also defines the module constants `AGENT = "ccctx"`, `CONSOLIDATOR = f"memory/{__version__}"`, `TEMPLATE = "template/1"`, and the logger `log = logging.getLogger("golestan_code_mcp.memory")`.

**Checkpoint**: `uv run pytest -q tests/test_schema.py tests/test_memory.py` passes.

---

## Phase 3: User Story 1 - Every tool call is recorded (Priority: P1) 🎯 MVP

**Goal**: one run per MCP tool call, viewable with `ccctx memory list`.

**Independent Test**: make 6 calls through an in-memory MCP client session (one refused). Then
`ccctx memory list --repo flask --limit 6` shows exactly those 6 rows, newest first, and every tool's answer
matches what it was before recording existed.

### Tests for User Story 1

- [X] T008 [P] [US1] Write failing unit tests for run building in tests/test_memory.py, with no database (research R3, R4):
  - **Fields per tool**: `memory.run_of(tool, arguments, result, client, ms)` keeps only the allowed result fields
    for each of the eight tools' result models: `search_code` hits, `get_symbol` hits without `source`, caller,
    callee and impact rows, `read_wiki` page as one `{kind: page, name, repo, path: directory}` row, and `read_wiki`
    list.
  - **`question`**: the query, name, page or topic argument, or `None` (`list_repositories`).
  - **`status`, `reason` and `result_count`**: taken from the result envelope, or `error` when the result is `None`.
  - **Repositories**: the `repo` argument, or else the distinct `repo` values of the results.
  - **No source**: no field anywhere holds `source`, `snippet` or page `text`.
- [X] T009 [P] [US1] Write failing recording contract tests in tests/test_server.py (contracts/tools.md "Recording"), using `create_connected_server_and_client_session` with `clientInfo` name `test-client`, version `9.9`:
  - **One run per call**: each of the eight tools (`recall` once it exists, marked `xfail` until Phase 5) writes
    exactly one run after `memory.flush()`, with the tool, arguments, `client = "test-client 9.9"`, status and
    result count.
  - **Refused calls**: an empty `search_code` query and an unknown repository are recorded as `unavailable` with the
    tool's reason.
  - **Recording failure**: with `memory` pointed at an unreachable database (monkeypatched `db.connect` inside the
    writer), the tool's answer is identical, and stderr gets one `{"event": "memory_record_failed", ...}` record.
  - **Unchanged log**: the existing `{"event": "tool", ...}` record is unchanged.
- [X] T010 [P] [US1] Write failing tests for `ccctx memory list` in tests/test_cli.py (contracts/cli.md):
  - **The table**: insert runs with `memory.store_runs`, then check the header, newest first, the default limit of
    20, `--limit`, `--repo` filtering, `-` for no question or no client, the reason in TOP for an unavailable run,
    and TOP formats for a symbol, a call line and a page.
  - **No runs**: `no runs recorded`.
  - **Bad input**: an unknown `--repo` exits 1, and `--limit 0` exits 2.

### Implementation for User Story 1

- [X] T011 [US1] Implement run building and storage in src/golestan_code_mcp/memory.py:
  - **`run_of(...)`** (T008).
  - **`store_runs(conn, runs)`**: inserts each run and its run-repository links with `executemany` (repositories
    resolved by name, unknown names skipped), sets `scoped` when it has a link, and commits.
  - **The recorder** (research R2): `record(run)` puts the run on a `queue.Queue`. One lazily started daemon thread
    keeps a single `db.connect(load())` connection and calls `store_runs`. On any exception it logs
    `{"event": "memory_record_failed", "tool": ..., "reason": ...}`, drops the run, and reconnects next time.
  - **Draining**: `flush()` waits for the queue (`queue.join`), and `atexit` waits up to 5 seconds.
- [X] T012 [US1] Hook recording into `_logged` in src/golestan_code_mcp/server.py:
  - **When**: after the tool returns (in `finally`), it calls `memory.record(memory.run_of(...))`.
  - **Arguments**: the tool's arguments, from `kwargs` bound with `inspect.signature`.
  - **Client**: `f"{info.name} {info.version}"`, from `mcp.get_context().session.client_params.clientInfo`, or
    `None` when that raises (no request context).
  - **Safety**: the whole block is in its own `try` so it can never change the result or raise.
- [X] T013 [US1] Implement `memory.runs(conn, repo=None, limit=20)` in src/golestan_code_mcp/memory.py, returning dataclass rows (id, called_at, tool, question, client, status, reason, result_count, top), newest first and filtered through the run-repository links when `repo` is given (unknown repo raises `RegistryError`). Then add `ccctx memory list [--repo NAME] [--limit N]` to src/golestan_code_mcp/cli.py: the `memory` group, the `_memory_list` handler and its `format_table` output exactly as contracts/cli.md shows, reusing `_positive` and `_when`.

**Checkpoint**: T008 to T010 pass, `uv run pytest -q tests/test_server.py tests/test_cli.py` shows no regression, and quickstart step 1 works in the MCP Inspector.

---

## Phase 4: User Story 2 - Distil runs into facts (Priority: P1)

**Goal**: `ccctx memory consolidate` turns runs into one fact per subject, as package `fact` records traceable to
their runs, and `ccctx memory facts` lists them.

**Independent Test**: store 20 runs about 5 subjects (two near-identical `url_for` questions among them) and
consolidate. The result is at most 10 facts, one `url_for` fact citing both runs, every run ID existing, and a
second consolidation changing nothing.

### Tests for User Story 2

- [X] T014 [P] [US2] Write failing finding tests in tests/test_memory.py against an ingested fixture repository (pattern of tests/test_wiki.py, research R5):
  - **One case per row of the R5 table**: `memory.finding(cur, repo_id, run)` returns the subject key, the subject,
    the aspect and the stored tool and arguments.
  - **Page subjects**: from a page hit and from `read_wiki` with a page.
  - **No finding**: from a failed run, an empty run, `list_repositories`, `read_wiki` without a page, `recall`, and
    a run whose subject no longer exists in the index.
  - **Multi-repository runs**: a run with results from two repositories gives each repository its own top result.
- [X] T015 [P] [US2] Write failing consolidation tests in tests/test_memory.py, using the template distiller (no model), per research R6, R7 and R9 and data-model.md:
  - **Merging**: "where is url_for defined" and "where's url_for defined?" give one fact holding both wordings and
    both run IDs.
  - **Confidence**: 1, 2 and 3 agreeing runs give 0.5, 0.75 and 0.875.
  - **A wording moves to another subject**: the old fact gets `contradict` 1 and confidence halved, the wording moves
    to the new fact, and a package `contradicts` link joins them.
  - **An aspect changes value**: `contradict` + 1.
  - **The counts**: `Consolidation` returns runs read, created, merged, weakened, stale and re-asked.
  - **Idempotency**: a second consolidation with no new runs changes no record (compare content and metadata).
  - **Crash between writes**: links reset to unconsolidated after a consolidation are not counted again.
  - **Concurrency** (research R9 step 1): two `consolidate` calls on one repository, from two threads with two
    connections, count every run exactly once and create one fact per subject. A call that times out waiting for the
    lock fails with "another consolidation of <repo> is running".
  - **Distiller**: every fact's metadata has `distiller = "template/1"` and `consolidator = "memory/1.2.0"`.
  - **Run IDs**: every ID in `runs` exists in `ccctx_memory_runs`.
  - **Text**: the template text matches the R6 example shape.
- [X] T016 [P] [US2] Write failing distiller tests in tests/test_memory.py (research R13), with a fake `Llm` whose `generate` records its prompt and returns `{"text": "..."}`:
  - **What is sent**: the prompt holds exactly the subject's source (at most 200 lines), its findings, the related
    names and locations, and the questions. Nothing else from the run log.
  - **Model text**: the fact's content is the model's text and its distiller is `llm:<model>`.
  - **Fallback**: a `generate` that raises, or returns empty text, falls back to the template, sets
    `distiller = "template/1"`, logs one warning, and consolidation still completes.
  - **The model never decides**: subject, runs and confidence are identical with and without the fake model.
  - **One call per fact**: `generate` is called exactly once per created or changed fact, and never through
    `add_memory` or `update_memory` (linking is off, research R1).
  - **Identifier check** (FR-008, R13): a fake `Llm` whose text names a symbol not among the subject, findings,
    references or questions has its text rejected. The template writes the fact, its distiller is `template/1`, and
    one `memory_model_rejected` record lists the rejected names but not the text. Text naming only known identifiers
    is accepted.
- [X] T017 [P] [US2] Write failing tests for `ccctx memory consolidate` and `ccctx memory facts` in tests/test_cli.py (contracts/cli.md):
  - **consolidate**: one line per repository, with the distiller counts in parentheses. Without `--repo`, every
    repository with runs or facts. The rerun prints all zeros.
  - **facts**: column order, fresh first then confidence, the 8-character FACT ID, RUNS oldest first, TEXT cut at 120
    with a stale fact's reason appended, and `no facts`.
  - **Bad input**: an unknown `--repo` exits 1.

### Implementation for User Story 2

- [X] T018 [US2] Implement `memory.finding(cur, repo_id, run)` in src/golestan_code_mcp/memory.py, per the R5 table. It resolves subjects against `ccctx_symbols`/`ccctx_files` (by repository, path, qualified name and kind for symbol hits; by repository and qualified name for `callee`/`caller`; through `graph.definitions` for `impact_of`) and `ccctx_wiki_pages` for pages. It returns a `Finding(subject_key, subject, kind, aspect, value, tool, arguments, run_id, question, refs)`, or `None`.
- [X] T019 [US2] Implement the distillers in src/golestan_code_mcp/memory.py:
  - **`template_text(subject, kind, findings, questions)`**: the R6 sentences.
  - **`model_text(llm, ...)`**: one `llm.generate(prompt, response_json_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]})` call with the R13 prompt. The subject's source is read from `ccctx_symbols.source` (first 200 lines) or the page text. It returns `(text, distiller)`, falling back to the template on any exception or empty text, with a `{"event": "memory_model_failed", ...}` warning.
  - **`known_names(text, allowed)`**: the identifier check from research R13. Backticked words and `snake_case`, `CamelCase` and dotted names must all be in `allowed`, or `model_text` rejects the text, falls back to the template, and logs `memory_model_rejected` with the names only.
- [X] T020 [US2] Implement `memory.consolidate(conn, repo=None, env=None) -> list[Consolidation]` in src/golestan_code_mcp/memory.py (research R9 steps 1 and 3 to 6). Step 2, re-check, is a no-op hook until T033:
  - **Per repository**: lock the repository row on a second connection (research R9 step 1, `for update wait 60`,
    rolled back in `finally`), read the unconsolidated links in run-id order, and turn each into a finding.
  - **Load and merge**: load the repository's facts once with
    `client.list_memories(user_id=repo, agent_id=AGENT, limit=None)`, keyed by `metadata["subject_key"]`, and merge
    per R6 and R7. Skip a finding whose run ID is already in the fact's `runs`.
  - **Write**: each new or changed fact once, through `add_memory(text, memory_type="fact", user_id=repo, agent_id=AGENT, metadata=..., ttl_days=None, autonomous_linking=False)`, with the subject's `language` in the metadata (R14), or `update_memory(id, content=..., metadata=..., status=...)`. Add `link_records(..., "contradicts")` for moved wordings.
  - **Finish**: flag the links consolidated, delete scoped runs with no repository left (R12), commit, and log one
    `{"event": "consolidate", "repo": ..., counts..., "seconds": ...}` record. That record carries no arguments,
    results or text (FR-020).
- [X] T021 [US2] Implement `memory.facts(conn, repo=None, limit=20)` in src/golestan_code_mcp/memory.py: list the package fact records, ordered fresh first, then confidence, then `updated_at`, returned as `FactView` dataclasses with sources resolved to current locations. Then add `ccctx memory consolidate [--repo]` and `ccctx memory facts [--repo] [--limit]` to src/golestan_code_mcp/cli.py, with the outputs of contracts/cli.md. Add `memory.log` to the stderr handlers in `main`.

**Checkpoint**: T014 to T017 pass, and quickstart step 2 works: fewer facts than runs, one merged `url_for` fact, and a rerun that changes nothing.

---

## Phase 5: User Story 4 - Recall at the start of a session (Priority: P1)

**Goal**: a `recall` MCP tool, plus server instructions, so a fresh session loads what earlier ones worked out.
Facts also show up in `search_code`, so they are searchable alongside code (Principle V, FR-021).

**Independent Test**:
1. After consolidating, call `recall` with `{"repo": "flask"}` through an in-memory client session. It returns the
   same facts as `ccctx memory facts --repo flask` and the 10 newest runs without `recall`'s own runs, and a topic
   puts the matching fact first.
2. `ccctx search "where is url_for defined" --repo flask` still has the `url_for` definition first, with the
   `url_for` fact in the top 5 (SC-011).

### Tests for User Story 4

- [X] T022 [P] [US4] Write failing `recall` contract tests in tests/test_server.py (contracts/tools.md):
  - **Listing**: the server lists exactly eight tools, and the existing list test is updated to name `recall`.
  - **Description and instructions**: `recall`'s description and parameter descriptions match the contract, and
    the server's `instructions` match it word for word.
  - **Result shape**: the fields and their types, `limit` 1 to 50 (0 and 51 refused before connecting), and an
    empty `topic` refused.
  - **Order**: fresh facts first, and a topic ranks the related fact first.
  - **Bounds**: at most 10 runs, never `recall` runs, and `total`/`truncated` correct.
  - **Errors**: an unknown repository and an unreachable database return `unavailable` with empty lists.
  - **No model**: `recall` does not call the model (a fake `Llm` records zero calls).
  - **Recorded**: `recall` is itself recorded as a run, so T009's `xfail` is removed.
- [X] T023 [P] [US4] Write failing `memory.recall` tests in tests/test_memory.py (research R10): no topic, then topic ordering through the package search, a missing repository merging every repository's results, the result size unchanged at 100 and at 2,000 stored runs, and a stale fact carrying its reason and its references with null locations when the record is gone.

### Implementation for User Story 4

- [X] T024 [US4] Implement `memory.recall(conn, repo=None, topic=None, limit=20)` in src/golestan_code_mcp/memory.py, per research R10:
  - **Without a topic**: list the facts and sort them.
  - **With a topic**: `client.search(topic, user_id=repo, agent_id=AGENT, record_types=["fact"], include_invalid_results=True, max_results=limit)`, then a stable re-sort that puts fresh facts first.
  - **Without a repository**: search each repository that has facts and merge the results.
  - **Recent runs**: `runs(conn, repo, 10)`, without `tool = 'recall'`.
  - **Returns**: `Recall(facts, runs, total)`.
- [X] T025 [US4] Add the `recall` tool to src/golestan_code_mcp/server.py:
  - **Definition**: description, `Annotated` parameters and result models (`RecallFact`, `RecallSource`,
    `RecallRun`, `RecallResults`), all as contracts/tools.md says.
  - **Decorators and checks**: `@_logged` and `READ_ONLY`, with checks through `_answer`.
  - **Server**: `FastMCP(NAME, instructions=INSTRUCTIONS)`.
  - **Strict arguments**: `recall` is defined before the loop at the bottom of the file, so the unknown-argument
    refusal covers it.
- [X] T026 [US4] Write failing fact-hit tests (FR-021, research R14, contracts/tools.md "search_code: fact hits"):
  - **In tests/test_semantic.py**, against a fixture repository with consolidated facts:
    - fresh facts come back as `kind="fact"` hits with the subject's current path, lines and language, and the fact
      text as the snippet;
    - an exact identifier question still puts the definition first, with the fact below it;
    - the `--repo` and `language` filters apply to facts;
    - fact hits count toward `limit`, and stale facts never appear;
    - with no consolidated facts in scope, `oracleagentmemory` is not imported (check `sys.modules` in a subprocess).
  - **In tests/test_server.py**: `search_code` returns the same fact hits as `semantic.search`, and its description
    contains the new fact sentence word for word.
  - **In tests/test_memory.py**: a run whose top hit is a fact gives a finding for that fact's subject.
- [X] T027 [US4] Implement fact hits:
  - **`memory.search_facts(conn, question, repos, language, k=5)`** in src/golestan_code_mcp/memory.py: the package
    search per repository in scope that has consolidated links, `include_invalid_results=False`, the language
    filter, and the in-database cosine similarity of question and fact text (research R14).
  - **`semantic.search`** in src/golestan_code_mcp/semantic.py: merge fact hits through the same `_place` rule as
    pages, counted toward `limit`, with `keyword_rank=None` and `score=0.0`.
  - **`search_code`** in src/golestan_code_mcp/server.py: add the fact sentence to its description.
  - **`memory.finding`** (T018): map a `fact` top hit to the fact's subject.
  - **`ccctx search`** in src/golestan_code_mcp/cli.py: no change needed beyond fact rows showing `fact` as KIND.

**Checkpoint**: T022, T023 and T026 pass. In the MCP Inspector, `recall` with `{"repo": "flask"}` answers in under 2 seconds, and quickstart step 2 followed by `ccctx search "where is url_for defined" --repo flask` meets SC-011.

---

## Phase 6: User Story 3 - The memory keeps pace with the code (Priority: P2)

**Goal**: every ingestion consolidates. Facts about removed code go stale. Facts about edited code are re-asked
and stay fresh only when the same code answers.

**Independent Test**: in a fixture repository, create facts about two functions, then remove one and edit the
other, commit and ingest. The summary's `Memory` line reports one stale and one re-asked. The edited function's
fact is fresh at its new lines, the removed one's is stale with its reason, and other facts are unchanged.

### Tests for User Story 3

- [X] T028 [P] [US3] Write failing re-check tests in tests/test_memory.py (research R8), against a fixture repository edited and committed between ingests:
  - **Removed subject**: the fact is stale (`INVALID`) with `` `X` was removed ``, `contradict` goes up by 1, and
    the confidence halves.
  - **Moved subject, same hash**: only re-pointed, and no re-ask happens.
  - **Edited subject, same answer**: the re-ask keeps it fresh, with refreshed findings, re-pointed references and
    rewritten text.
  - **Edited subject, different answer**: rename the function and add a new one of that name elsewhere. The fact is
    stale with ``re-asked "<question>": now answered by `Y` `` and its confidence is halved.
  - **No runs**: a re-ask records no run.
  - **Stale facts**: they are not re-checked, and a new run with their subject makes them fresh again.
  - **Idempotency**: a second consolidation after the ingest changes nothing.
- [X] T029 [P] [US3] Write failing ingestion tests in tests/test_ingest.py:
  - **Every ingestion consolidates**: `ingest.ingest` consolidates the repository after the wiki refresh, including
    when the mode is `current`, and `Summary.memory` carries the counts.
  - **Failure**: when consolidation raises (monkeypatched), the ingestion still commits, `Summary.memory` holds the
    error, and the index is the same as without memory.
  - **Unchanged ingestion**: no fact changes state.
- [X] T030 [P] [US3] Write failing tests in tests/test_cli.py for the ingest summary's `Memory` line: it appears only when runs were read or facts changed, has the exact contracts/cli.md format, and the failure form prints `Memory    not consolidated: <reason>` plus the stderr warning, still exiting 0.
- [X] T031 [P] [US3] Write failing `memory.forget` tests in tests/test_memory.py (research R12, FR-018): `forget(conn, "x")` removes every fact of `x` and leaves other repositories' facts. After the repository row is deleted, its links are gone, runs only it held are deleted by the next consolidation, and runs shared with another repository stay.

### Implementation for User Story 3

- [X] T032 [US3] Implement `memory.forget(conn, repo)` in src/golestan_code_mcp/memory.py, calling `client.delete_user(repo, cascade=True)` and falling back to deleting each listed fact if the repository has no package user record. Add a comment above `registry.add_repo` in src/golestan_code_mcp/registry.py saying that a future repository removal must call `memory.forget`.
- [X] T033 [US3] Implement `memory.recheck(cur, client, repo)` in src/golestan_code_mcp/memory.py, per research R8, and call it as step 2 of `consolidate`:
  - **Look up**: each fresh fact's subject reference, by repository, qualified name and kind, preferring the same
    path; compare `content_hash`, or a SHA-256 of the page text.
  - **Removed or moved**: stale when gone, re-pointed when only moved.
  - **Re-ask**: re-run each finding's tool and arguments through `semantic.search`, `graph.definitions`,
    `graph.callers`, `graph.calls`, `graph.impact` or `wiki.read`, never through the MCP tools, so no run is
    recorded. Then apply the R8 outcomes, with the text rewritten by the distiller.
  - **Count** stale and re-asked.
- [X] T034 [US3] Call `memory.consolidate(conn, name)` in src/golestan_code_mcp/ingest.py after the wiki refresh, outside the ingest transaction and catching every exception into `Summary.memory`, a new field defaulting to `None` that holds a `Consolidation` or an error string. Then print the `Memory` line from `format_summary` and the warning from `_ingest` in src/golestan_code_mcp/cli.py, per contracts/cli.md.

**Checkpoint**: T028 to T031 pass, and quickstart step 3 works in a scratch clone (never in `../ccctx-repos/flask`).

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T035 [P] Document the feature in README.md (FR-019, FR-008a):
  - **The commands**: `ccctx memory list|consolidate|facts`, with example output.
  - **`recall`**: what it returns, and that clients are told to call it first.
  - **Fact hits in search**: the `fact` kind in `search_code` and `ccctx search`, and how they are placed.
  - **Facts**: merging by answering code, the confidence formula with the 0.5/0.75/0.875 examples, staleness and the
    re-ask.
  - **Memory after ingestion**: what the `Memory` line means.
  - **The `CCCTX_MEMORY_MODEL` settings**: what is sent to the model, word for word from research R13, and what
    happens without one.
  - **The package**: its `ccctx_mem_` tables.
  - **The tool list**: updated to eight tools at version 1.2.0.
- [X] T036 [P] Add a timing test to tests/test_memory.py, marked like the existing slow database tests (SC-004): 1,000 stored runs over 30 subjects consolidate in under 60 seconds with the template distiller, and a rerun changes nothing.
- [X] T037 [P] Add a latency check to tests/test_server.py (SC-008): the median of 20 `get_symbol` calls with recording on is within 5% of the median with `memory.record` replaced by a no-op.
- [X] T038 Run the whole suite and the linters: `uv run pytest` (database tests included), the retrieval evaluation in tests/test_eval.py (its top-5 hit rate unchanged, SC-009), and `uv run ruff check`, with no more findings than the 35 baseline. Fix any regression in the file it comes from.
- [X] T039 Run the live checks in specs/010-agent-memory/quickstart.md steps 1 to 6 and record the results in specs/010-agent-memory/quickstart.md under a dated "Verified" note:
  - **Inspector**: step 1 through `npx @modelcontextprotocol/inspector ccctx mcp`.
  - **Scratch clone**: step 3, never in `../ccctx-repos/flask`.
  - **SC-006 in a real client**: a fresh Claude Code session, asked "what do you already know about the flask
    codebase?", calls `recall` and no search tool.
  - **SC-010**: without a model every fact names `template/1`, and with `CCCTX_MEMORY_MODEL` set the new facts name
    the model. Skip the model half if no key is available, and say so in the note.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none. T001 first (it installs the package), then T002 and T003.
- **Foundational (Phase 2)**: needs T001 and T003. It blocks every story.
- **US1 (Phase 3)**: needs Phase 2.
- **US2 (Phase 4)**: needs US1 (`store_runs`, the run tables filled).
- **US4 (Phase 5)**: needs US2 (facts to recall). It can start right after T021.
- **US3 (Phase 6)**: needs US2 (`consolidate`). It does not need US4, so Phases 5 and 6 can run in parallel if
  `memory.py` edits are coordinated, but running them in order is simpler.
- **Polish (Phase 7)**: needs every story.

### User Story Dependencies

- **US1**: independent once the foundation exists.
- **US2**: consumes US1's runs. It can be tested with runs inserted by `memory.store_runs`, without the MCP server.
- **US4**: reads US2's facts. Its tests seed facts through `consolidate`.
- **US3**: extends US2's `consolidate` with the re-check and wires it into ingestion.

### Within Each User Story

Tests are written first and must fail (constitution VI), then `memory.py`, then the surface files (`server.py`,
`cli.py`, `ingest.py`).

### Parallel Opportunities

- **Setup**: T002 alongside T001's `uv sync` once the lock is written.
- **Foundational**: T004 and T006 together (two test files). Then T007, then T005, because migration 8's Python step
  calls `memory.create_package_schema`.
- **US1**: T008, T009 and T010 together (test_memory, test_server, test_cli).
- **US2**: T014, T015, T016 and T017 together (T014 to T016 append to test_memory.py, so give each its own section
  or run them in sequence; T017 is in test_cli.py).
- **US4**: T022, T023 and T026 together (test files). T026 adds to three test files, so coordinate it with T022
  (test_server.py) and T023 (test_memory.py).
- **US3**: T028 to T031 together (test_memory, test_ingest, test_cli).
- **Polish**: T035, T036 and T037 together.

## Parallel Example: User Story 1

```text
Task: "T008 [P] [US1] run building unit tests in tests/test_memory.py"
Task: "T009 [P] [US1] recording contract tests in tests/test_server.py"
Task: "T010 [P] [US1] ccctx memory list tests in tests/test_cli.py"
# then, in order: T011 (memory.py) → T012 (server.py) → T013 (memory.py + cli.py)
```

## Implementation Strategy

### MVP First (User Story 1 Only)

Phases 1 to 3 give a working episodic log: every MCP call recorded and listed. Stop and check with quickstart step 1
before distilling anything.

### Incremental Delivery

1. **Setup and foundation**: the package installed, run tables, the package client.
2. **US1**: runs recorded and listed (MVP).
3. **US2**: facts distilled, merged and listed, the brief's `consolidate`/`facts` test.
4. **US4**: `recall` closes the loop, the brief's fresh-session test.
5. **US3**: memory follows the code through ingestion.
6. **Polish**: README, timing, regression, live checks.

### Parallel Team Strategy

`memory.py` is shared by every story, so one developer should own it. Test files and surface files (`server.py`,
`cli.py`, `ingest.py`) can go to others within a phase.

## Notes

- **Fixtures**: never edit `../ccctx-repos`. Staleness tests use fixture repositories or a scratch clone.
- **No model in tests**: no test needs a network, an API key or a running model. The model path uses a fake `Llm`.
- **Lazy import**: `oracleagentmemory` is imported only inside `memory.client`. Recording must never import it (T006
  checks this).
- **Commits**: commit after each phase checkpoint.
- **Where some tests landed**: the fact-hit search tests (T026), the ingest-consolidation tests (T029) and the
  re-check tests (T028) are in tests/test_memory.py, beside its fixture repository, not in test_semantic.py or
  test_ingest.py. T036 spreads its 1,000 runs over the fixture's 5 symbols, not 30 subjects.
