# Tasks: Usage Feedback

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Data model**: [data-model.md](./data-model.md) | **Contracts**: [cli.md](./contracts/cli.md), [tools.md](./contracts/tools.md) | **Live checks**: [quickstart.md](./quickstart.md)

**Tests come first.** Constitution VI requires every test task to be written before the code it covers, and to fail
first. Database tests run against the local database, like the existing suites:
- **Fixture repositories**: `tests/test_wiki.py` and `tests/test_memory.py` show the pattern, with `t-` names.
- **MCP calls**: `tests/test_server.py` shows `create_connected_server_and_client_session`.

**Order**: phases follow the stories' priorities. US1 (record) and US2 (boost) are P1. US3 (decay and the
`feedback` commands) and US4 (the gold evaluation) are P2.

**Shared files**: `feedback.py`, `server.py` and `cli.py` grow in several phases, so phases run one after another.
Within a phase, `[P]` marks tasks that touch different files.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 to US4, from spec.md

## Path Conventions

Single package: `src/golestan_code_mcp/`, tests in `tests/`, the gold set at `gold.json`. Every path below is from
the repository root.

---

## Phase 1: Setup

**Purpose**: version, settings documentation, test isolation.

- [X] T001 Set the version to `1.3.0` in pyproject.toml and in `__version__` in src/golestan_code_mcp/__init__.py.
  Document `CCCTX_FEEDBACK_CAP` (default 0.2, 0 to 1, where 0 switches feedback off) and
  `CCCTX_FEEDBACK_HALF_LIFE_DAYS` (default 30), commented out, in .env.example. Files: pyproject.toml,
  src/golestan_code_mcp/__init__.py, .env.example
- [X] T002 [P] Extend the autouse fixture in tests/conftest.py. Items queued through `memory.record` that are uses
  (`{"use": ...}`, research R3) for a non-`t-` repository are dropped too, unless the test requests
  `real_recording`. Keep the existing run rule. File: tests/conftest.py

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the table, the settings, and the core weight, boost and write functions every story uses.

- [X] T003 [P] Write failing tests in tests/test_schema.py:
  - Migration 9 "usage feedback" creates `ccctx_feedback` with the columns of data-model.md.
  - The `how` check constraint rejects anything but `cited` and `opened`.
  - The index `ccctx_feedback_result_ix` exists.
  - Deleting a repository deletes its uses.
  - Deleting a run sets `run_id` to null.
  - The migration is idempotent.
- [X] T004 [P] Write failing tests in tests/test_config.py:
  - `feedback_cap(env)` defaults to 0.2, accepts 0 to 1, and rejects negatives, values above 1 and non-numbers
    with `ConfigError` naming `CCCTX_FEEDBACK_CAP`.
  - `feedback_half_life(env)` defaults to 30.0, accepts positive numbers, and rejects 0, negatives and text.
- [X] T005 Add migration 9 "usage feedback" to `MIGRATIONS` in src/golestan_code_mcp/schema.py, as in
  data-model.md: table `ccctx_feedback`, check constraint `ccctx_feedback_how_ck`, foreign keys (repository on delete
  cascade, run on delete set null), `used_at` default `systimestamp`, and index `ccctx_feedback_result_ix` on
  `(repo_id, name)`. Make T003 pass. File: src/golestan_code_mcp/schema.py
- [X] T006 [P] Add `feedback_cap(env) -> float` and `feedback_half_life(env) -> float` to
  src/golestan_code_mcp/config.py, in the style of `search_candidates`. Make T004 pass. File:
  src/golestan_code_mcp/config.py
- [X] T007 Write failing tests in a new tests/test_feedback.py, with a `t-fb` fixture repository ingested once per
  module:
  - **`boost(weight, cap)`**: 0 at weight 0, `cap × weight / 5` below 5, and exactly `cap` at 5 and at 1000.
  - **`write_use`**: an opened use, then a cited use in the same session, leaves one cited row. Two cited uses in
    one session leave one. Another session adds a row.
  - **`weights`**: one cited use now gives 1.00, and an opened use gives 0.50. A cited use with `used_at` set 30
    days back gives 0.50 ± 0.01, and 60 days back gives 0.25 ± 0.01.
  - **`resolve`**: finds a symbol by `(repo, path, name)` and a page by `(repo, directory, name)`, and returns None
    otherwise.
- [X] T008 Create src/golestan_code_mcp/feedback.py with:
  - **Constants**: `BASE = {"cited": 1.0, "opened": 0.5}` and `SATURATION = 5.0`.
  - **`boost(weight, cap)`**.
  - **`resolve(cur, repo_id, path, name) -> (kind) | None`**: symbol first, then page.
  - **`write_use(cur, use)`**: `MERGE` on `(session, repo_id, path, name)` per data-model.md. A cited use upgrades
    an opened one and resets `used_at`.
  - **`weights(cur, repo_ids, half_life) -> {(repo_id, path, name): (uses, weight, last_used)}`**: one grouped
    query, with age from `cast(systimestamp as date) - cast(used_at as date)`.

  Make T007 pass. File: src/golestan_code_mcp/feedback.py

**Checkpoint**: `ccctx db migrate` applies migration 9, and the core functions are tested.

---

## Phase 3: User Story 1 - Record which results helped (Priority: P1) 🎯 MVP

**Goal**: a client's cited and opened uses are recorded, one per result per session, and linked to the search that
returned them. Past tool calls show which results were used.

**Independent Test**: search, `get_symbol` on hit 2, `mark_used` on hit 1. `ccctx memory list` shows `2/10` on the
search, and the database holds a cited use for hit 1 and an opened use for hit 2, both linked to the search run.

### Tests for User Story 1

- [X] T009 [P] [US1] Write failing contract tests in tests/test_server.py (contracts/tools.md, "Contract tests"),
  using the `recorded` fixture against a `t-` repository and `memory.flush()` before reading:
  - **Tool list**: exactly nine tools, with `mark_used` taking `repo`, `path` and `name`, and annotations
    `readOnlyHint` false and `idempotentHint` true.
  - **`mark_used`**: `ok` with `linked` true after a search returned the result, and false without one.
  - **Not found**: `unavailable` with a reason containing `not found`, and no row. An unknown repository answers
    `unavailable`.
  - **Opened uses**: `get_symbol` on a hit records an opened use linked to the run. `read_wiki` with a page hit's
    name records one for the page. `get_symbol` with no prior search records none.
  - **Dedupe**: search, `get_symbol`, then `mark_used` on the same hit leaves one cited use.
  - **Failures**: a recording failure (patch `feedback.write_use` to raise) leaves the answer unchanged.
- [X] T010 [P] [US1] Write failing tests in tests/test_memory.py:
  - `store_runs` sets `run["id"]` on each run dict.
  - A use queued after its run through `memory.record` is written with that `run_id`.
  - A use whose run was never written is written unlinked.
  - A failing use write logs `feedback_record_failed` and the writer keeps going.
  - `runs()` gives `RunView.used` as the names of linked uses, in result order.
  - `mark_used` is in `NO_FACTS`, so consolidation makes no fact from it.
- [X] T011 [P] [US1] Write failing tests in tests/test_cli.py: `ccctx memory list` shows `RESULTS` as
  `used/returned` (`2/10`) for a run with linked uses, and the plain count otherwise.

### Implementation for User Story 1

- [X] T012 [US1] Change the writer in src/golestan_code_mcp/memory.py, then make T010 pass:
  - **Run ids**: `store_runs` stores each new id back on its run dict.
  - **Uses**: `_write_runs` handles `{"use": use}` items by resolving `run_id` from `use["run"].get("id")` and
    calling `feedback.write_use` then committing. Its failures log `feedback_record_failed`, like runs.
  - **`NO_FACTS`**: add `mark_used`.
  - **`RunView.used`**: `runs()` fills it with one query over `ccctx_feedback` by `run_id`.

  File: src/golestan_code_mcp/memory.py
- [X] T013 [US1] Wire recording into src/golestan_code_mcp/server.py, then make T009 pass:
  - **Session**: add `SESSION = str(uuid.uuid4())`.
  - **Returned results**: add `_returned: dict[tuple[str, str, str], dict]` with a
    `# ponytail: one stdio session per process; key by ctx.session for multi-session transports` comment. Make
    `_logged` expose the run dict it records, so `search_code` can map each hit's `(repo, path, name)` to it.
  - **`_use(repo, path, name, kind, how)`**: queues `{"use": {...}}` through `memory.record`, with the client from
    `_client()`, `SESSION` and the run from `_returned`, if any.
  - **`mark_used`**: the tool with the contracts/tools.md description, parameters and result model `MarkUsedResult`.
    It resolves through `feedback.resolve` and records the cited use.
  - **Opened uses**: after `ok` answers, `get_symbol` records opened uses for returned symbols, and `read_wiki`
    with `page` records one for the page.

  File: src/golestan_code_mcp/server.py
- [X] T014 [US1] Show `used/returned` in `RESULTS` for runs with uses in `ccctx memory list`, in
  src/golestan_code_mcp/cli.py. Make T011 pass. File: src/golestan_code_mcp/cli.py

**Checkpoint**: Quickstart step 2 works through an MCP client.

---

## Phase 4: User Story 2 - Bounded boost for used results (Priority: P1)

**Goal**: search raises used results by at most 20% of their score, only among the candidates it found, with
identifier definitions still first, and shows the boost on every hit.

**Independent Test**: 1000 uses of `url_for` (flask). It is absent from `ccctx search "database connection
pooling"`, every hit's feedback is at most 0.2, and `--no-feedback` gives the old order.

### Tests for User Story 2

- [X] T015 [P] [US2] Write failing ranking tests in tests/test_feedback.py, against `t-fb` with uses written by
  `feedback.write_use`:
  - **Fields**: every `Result` has `relevance` and `feedback`, and `score == relevance × (1 + feedback)`.
  - **The bound**: `feedback` stays within [0, cap] for 1, 5 and 1000 uses.
  - **Reordering**: a used symbol moves above an unused one whose score was within 20%, and not above one more than
    20% ahead.
  - **Never adds**: a symbol with 1000 uses that the question does not find is not in the hits.
  - **Definitions**: an identifier's definitions stay first when another symbol has feedback.
  - **Pages and facts**: a used page is placed by its boosted similarity, and facts always have feedback 0.
  - **Off switches**: `feedback=False`, and a cap of 0, give exactly the order and scores of an empty table.
  - **Latency**: with feedback, the median over 5 searches is within 10% of the median without it (SC-007).
- [X] T016 [P] [US2] Write failing contract tests in tests/test_server.py:
  - `search_code` hits carry `relevance` and `feedback`.
  - `feedback: false` gives every hit 0.
  - The description contains the contracts/tools.md sentence about the feedback field.
- [X] T017 [P] [US2] Write failing tests in tests/test_cli.py:
  - `ccctx search` prints a `FEEDBACK` column after `SCORE`, with `+N%`, blank at 0.
  - `--no-feedback` leaves it blank on every row.

### Implementation for User Story 2

- [X] T018 [US2] Boost the candidates in src/golestan_code_mcp/semantic.py (research R5), then make T015 pass:
  - **Result fields**: add `relevance: float` and `feedback: float = 0.0` to `Result`.
  - **Switch**: add `feedback: bool = True` to `search`. When on and `config.feedback_cap(env) > 0`, read
    `feedback.weights` once for the repository ids among `symbols | definitions | pages` (local import, as for
    memory).
  - **Symbols**: multiply each fused entry's score by `1 + boost` and stably re-sort `fused`. Sort `first` the
    same way, but keep it first.
  - **Pages**: multiply a page entry's similarity by `1 + boost`, capped at 1.0, before `_place`.
  - **Facts**: keep feedback 0.
  - **Explaining**: carry `relevance` and `feedback` into each `Result`.

  File: src/golestan_code_mcp/semantic.py
- [X] T019 [US2] Update src/golestan_code_mcp/server.py, then make T016 pass:
  - **`SearchHit`**: add `relevance` and `feedback`.
  - **`search_code`**: add the `feedback: bool = True` argument with a Field description, and pass it to
    `semantic.search`.
  - **Description**: add the sentence from contracts/tools.md, and extend the scores sentence.

  File: src/golestan_code_mcp/server.py
- [X] T020 [US2] Add `--no-feedback` and the `FEEDBACK` column to `ccctx search` in src/golestan_code_mcp/cli.py.
  Make T017 pass. File: src/golestan_code_mcp/cli.py

**Checkpoint**: Quickstart step 4 holds.

---

## Phase 5: User Story 3 - Feedback fades over time (Priority: P2)

**Goal**: the operator lists weights and boosts, records uses by hand (backdated or many), and resets a
repository.

**Independent Test**: Quickstart steps 5 and 6. Weights are 1.00, 0.50 and 0.25, boosts +4%, +2% and +1%, and the
reset empties the list.

### Tests for User Story 3

- [X] T021 [P] [US3] Write failing tests in tests/test_feedback.py:
  - **`listing(conn, repo)`**: rows sorted by weight, with uses, weight, boost, last use and `indexed`. A use for a
    removed symbol lists `indexed` False and boosts nothing in search.
  - **`add(conn, repo, name, path=None, days_ago=0, count=1)`**:
    - Each of the `count` cited uses gets its own `cli:` session, client `cli`.
    - `days_ago=30` dates them 30 days back.
    - A negative `days_ago` raises `ValueError`.
    - An unknown name raises "not found".
    - A name at several paths without `path` raises an error listing the paths.
  - **`reset(conn, repo)` and `reset(conn, None)`**: delete one repository's uses or all of them, return the
    count, and leave other repositories' uses alone.
- [X] T022 [P] [US3] Write failing tests in tests/test_cli.py for `ccctx feedback list|add|reset`, following
  contracts/cli.md:
  - **`list`**: the columns, `WEIGHT` to two decimals, `BOOST` as a whole percent, and `no feedback recorded for
    <name>`.
  - **`add`**: the summary line, and exit 1 for not found or an ambiguous name. Exit 2 for a negative
    `--days-ago`, or a `--count` of 0 or above 100000.
  - **`reset`**: `deleted N uses in <repo>` and `--all`. Exit 2 without exactly one of the two flags.
  - **Errors**: an unknown `--repo` exits 1.

### Implementation for User Story 3

- [X] T023 [US3] Add `listing`, `add` and `reset` to src/golestan_code_mcp/feedback.py (research R9, R11). `listing`
  uses `weights` plus an existence check against symbols and pages. Make T021 pass. File:
  src/golestan_code_mcp/feedback.py
- [X] T024 [US3] Add the `ccctx feedback` group (`list --repo`, `add NAME --repo [--path] [--days-ago] [--count]`,
  `reset --repo|--all` as a required mutually exclusive group) to src/golestan_code_mcp/cli.py. Make T022 pass.
  File: src/golestan_code_mcp/cli.py

**Checkpoint**: Quickstart steps 5 and 6 hold.

---

## Phase 6: User Story 4 - Measure retrieval with and without feedback (Priority: P2)

**Goal**: `ccctx eval --gold gold.json [--with-feedback]` prints the question count and recall@10 over a versioned
20-question gold set, without recording anything.

**Independent Test**: Quickstart steps 1 and 3. The baseline prints `Questions: 20` and `recall@10: r (n/20)`.
After feedback on the expected results of 5 questions, `--with-feedback` gives at least r, and the run without it
still gives r.

### Tests for User Story 4

- [X] T025 [P] [US4] Write failing tests in tests/test_eval.py:
  - **`feedback.load_gold(path, conn)`**: rejects a missing file, invalid JSON, a missing `version` or
    `questions`, an empty question, empty `paths` and an unregistered `repo`, each with the message from
    contracts/cli.md.
  - **The hit rule**: an exact path matches, and an expected directory matches files under it.
  - **`feedback.evaluate(conn, gold, with_feedback, limit=10)`**: returns questions, hits and missed.
  - **Records nothing**: the run and use counts are the same before and after.
  - **The gold set**: `gold.json` has 20 questions.
  - **The floor**: recall without feedback is at least the recorded baseline (T030).
  - **SC-002**: with feedback for the expected results of 5 questions (added, then reset in teardown),
    `with_feedback=True` is at least the baseline and `False` equals it.
  - **SC-003**: with 1000 uses of `url_for`, the gold rule holds. It enters a question's top 10 only if its
    unboosted score is at least 1/1.2 of the tenth hit's. It is absent for "database connection pooling".
  - **SC-006**: the existing identifier tests still pass with feedback on.
- [X] T026 [P] [US4] Write failing tests in tests/test_cli.py for `ccctx eval`:
  - The output lines `Questions: N`, `recall@10: x.xx (n/N)` and `missed: ...`.
  - `@` follows `--limit`.
  - Gold-file errors exit 1.
  - `--with-feedback` is passed through.

### Implementation for User Story 4

- [X] T027 [P] [US4] Write gold.json (version 1) with 20 plain-language questions: about 12 for flask and 8 for gin
  (routing, sessions, blueprints, config loading, templates, JSON, the request context, error handlers, gin
  middleware, binding, rendering, router groups). Each has its `repo` and expected `paths`. Check every path exists
  in the index (`ccctx symbols --repo ...`). Questions must be in plain words, not identifiers. File: gold.json
- [X] T028 [US4] Add `load_gold` and `evaluate` to src/golestan_code_mcp/feedback.py (research R10). They call
  `semantic.search(conn, q, [repo] if repo else None, feedback=with_feedback, limit=limit)` directly. Make T025's
  unit parts pass. File: src/golestan_code_mcp/feedback.py
- [X] T029 [US4] Add `ccctx eval --gold FILE [--with-feedback] [--limit N]` to src/golestan_code_mcp/cli.py, with the
  contracts/cli.md output and errors. Make T026 pass. File: src/golestan_code_mcp/cli.py
- [X] T030 [US4] Measure the baseline:
  - Run `ccctx eval --gold gold.json` with no feedback, and record the result in specs/011-usage-feedback/quickstart.md.
  - Set the floor constant in tests/test_eval.py to it. Make T025 pass.
  - If a question misses because its expected path is wrong, fix gold.json, not the floor.

  Files: specs/011-usage-feedback/quickstart.md, tests/test_eval.py, gold.json

**Checkpoint**: Quickstart steps 1 and 3 hold.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T031 [P] Update README.md:
  - **The tools table**: nine tools, with `mark_used`.
  - **`search_code`**: the `relevance` and `feedback` fields and the `feedback` argument.
  - **A "Usage feedback" section**: what counts as a use, the weight and decay, the boost formula and cap, the
    settings and their defaults, and `ccctx feedback list|add|reset`.
  - **"Evaluating retrieval"**: `ccctx eval` and the gold format.
  - **"Changed in 1.3.0"**, and the layout (`feedback.py`, `gold.json`).

  File: README.md
- [X] T032 Run the full suite (`uv run pytest`) and ruff (`uvx ruff@0.14.0 check`) on the changed files, and fix
  what fails. Stop every MCP client first if `uv sync` is needed (`ccctx.exe` lock). Files: src/golestan_code_mcp/*.py,
  tests/*.py
- [X] T033 Walk through the quickstart live:
  - Steps 2 to 6, with a real MCP client (the Inspector CLI or `claude -p`) for step 2.
  - Append a "Verified 2026-10-12" section with the observed outputs.
  - Finish with `ccctx feedback reset --all` so the demo feedback does not linger.

  File: specs/011-usage-feedback/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none. T001 and T002 in parallel.
- **Foundational (Phase 2)**: needs Setup. It blocks every story. T003, T004 and T007 are tests, written first.
  T005 and T006 can run together, and T008 needs T005.
- **US1 (Phase 3)**: needs Phase 2.
- **US2 (Phase 4)**: needs Phase 2. Its tests write uses directly, so it does not need US1, but it runs after US1
  because both edit `server.py`.
- **US3 (Phase 5)**: needs Phase 2. T021's "boosts nothing" check needs US2's T018.
- **US4 (Phase 6)**: needs US2 (the `feedback` switch in `semantic.search`) and US3 (`add` and `reset`, used by
  T025's SC-002 and SC-003 tests).
- **Polish (Phase 7)**: needs every story.

### User Story Dependencies

- **US1**: independent once the foundation exists.
- **US2**: independent of US1; uses come from `feedback.write_use`.
- **US3**: reads the same table. Its listing is independent; the search check uses US2.
- **US4**: the baseline alone needs only `semantic.search`. With-feedback and the hammer check need US2 and US3.

### Within Each User Story

Tests are written first and must fail (constitution VI), then `feedback.py`, `memory.py` or `semantic.py`, then the
surface files (`server.py`, `cli.py`).

### Parallel Opportunities

- **Setup**: T001 and T002.
- **Foundational**: T003, T004 and T007 (three test files), then T005 and T006.
- **US1**: T009, T010 and T011 (test_server, test_memory, test_cli).
- **US2**: T015, T016 and T017.
- **US3**: T021 and T022.
- **US4**: T025, T026 and T027 (test_eval, test_cli, gold.json).
- **Polish**: T031 alongside T032.

## Parallel Example: User Story 1

```text
Task: "T009 [P] [US1] mark_used and opened-use contract tests in tests/test_server.py"
Task: "T010 [P] [US1] writer and RunView.used tests in tests/test_memory.py"
Task: "T011 [P] [US1] memory list used/returned tests in tests/test_cli.py"
# then, in order: T012 (memory.py) → T013 (server.py) → T014 (cli.py)
```

## Implementation Strategy

### MVP First (User Story 1 Only)

Phases 1 and 2, then US1: the server records which results helped, and `ccctx memory list` shows it. Ranking is
untouched, so nothing can regress.

### Incremental Delivery

1. **US1**: record uses.
2. **US2**: the bounded boost. Check that "database connection pooling" doesn't change.
3. **US3**: decay visible in `feedback list`; add and reset.
4. **US4**: the gold baseline and with-feedback recall.
5. **Polish**: README, the suite, the live walkthrough.

## Notes

- Feedback never changes indexed content (FR-025). `feedback.py` only touches `ccctx_feedback`.
- Tests that write uses for flask must reset them in teardown. `conftest.py` only guards uses queued through
  `memory.record`.
- Commit only when the user asks.
