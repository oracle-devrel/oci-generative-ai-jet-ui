# Research: Agent Memory

## R1. Oracle's AI Agent Memory package holds the facts; our tables hold the runs

**Decision**: add `oracleagentmemory` (26.8.0) and use it for everything about facts:
- **Storage**: one `OracleAgentMemory` client per connection.
  - `table_name_prefix="ccctx_mem_"`, so its tables sit beside ours.
  - `schema_policy=SchemaPolicy.REQUIRE_EXISTING`. Migration 8 creates the package's tables with a Python step that
    builds the client once with `SchemaPolicy.CREATE_IF_NECESSARY`, so every table comes from a migration
    (constitution, Technology & Data Constraints).
  - `agent_id="ccctx"`, and `user_id` set to the repository name. That is the package's scope, and every package
    search requires one.
- **Records**: facts are `memory_type="fact"` records. Our fields (subject key, findings, questions, run IDs,
  references, confidence, distiller) go in the record's `metadata`. Updates use `update_memory`, which replaces the
  metadata object whole (R6).
- **Lifecycle**: a stale fact gets `status=RecordStatus.INVALID`, and becomes `VALID` again when a run confirms it
  (FR-015). Removing a repository calls `delete_user(<repo>, cascade=True)` (R12).
- **Recall by topic**: package `search` with `record_types=["fact"]` and `include_invalid_results=True` (R10).
- **Embedding**: `OracleDBEmbedder(connection, model="ALL_MINILM_L12_V2", embedding_dimension=384)`. This is the
  in-database model search already uses, so facts are embedded without leaving the database.
- **Writing text**: the package's `Llm` adapter (LiteLLM) writes each fact's text when a model is configured (R13).
- **Links**: `add_memory` is always called with `autonomous_linking=False`, so the per-fact prompt in R13 is the only
  model call, and what it sends is documented. A contradiction we detect (R7) is stored with
  `link_records(new, "fact", old, "fact", "contradicts")`.

**What stays ours**:
- **The run log** (`ccctx_memory_runs`, `ccctx_memory_run_repos`):
  - `ccctx memory list` filters runs by repository and time in SQL and shows integer run IDs.
  - One run can belong to several repositories, each with its own consolidated flag (R4).
  - Package records are scoped to one user, so they cannot hold any of this.
- **Deciding what a fact is**: the subject of each run, merging and confidence (R5 to R7) are decided by code, as the
  spec requires.

**Not used: the package's automatic extraction from thread messages.** It writes free-text memories with no run IDs
and no subject key. We could not trace a fact to its runs (FR-007) or merge by subject (FR-009). Each consolidation
calls the model once per changed fact instead, with exactly the inputs FR-008a lists. Threads are not created, so
`MemoryExtractionConfig(extract_memories=False)` is set.

**Rationale**: the user chose to use the package in full (clarification 2026-10-12). The constitution, amended to
v1.1.0, allows memory distillation to send results to a configured model.

**Cost** (Complexity Tracking): the package brings `litellm`, `aiohttp`, `httpx`, `pillow`, `cryptography` and
`numpy`. Importing it takes about a second, so `memory.py` imports it lazily, only in consolidation, `facts` and
`recall`. Recording a run never imports it.

## R2. Recording in the tool wrapper, written by one background thread

**Decision**: `server._logged` already wraps every tool. After the tool returns, it builds a run from the arguments,
the result and the calling client, and puts it on a queue. One daemon thread holds one connection and inserts the
runs in order. On a write error it logs a `memory_record_failed` event, drops the run, and reconnects on the next
one. At exit, `atexit` waits up to 5 seconds for the queue to drain. Tests call `memory.flush()`.

**Rationale**: FR-003 and SC-008 say recording must never change an answer or slow it down. Opening a second
connection inside each call costs more than a typical tool call takes. The queue keeps the insert off the answering
path, and one writer keeps runs in call order.

**Alternatives considered**:
- **Insert on the tool's own connection**: calls refused before connecting (an empty question, a bad limit) would
  then not be recorded, and US1.3 needs them.
- **A thread per run**: runs could be stored out of order, and nothing would bound the number of connections.

## R3. What a run stores

**Decision**:
- **Arguments**: stored as given, in a JSON column.
- **Question**: the query, name, page or topic argument, whichever the tool has.
- **Client**: name and version from `clientInfo` in the MCP initialize handshake, read through
  `mcp.get_context().session.client_params`. `null` outside a session.
- **Results**: every row the tool returned (each tool already caps how many), keeping only these fields: `kind`,
  `repo`, `name`, `path`, `start_line`, `end_line`, `line`, `score`, `similarity`, `callee`, `caller`, `hops`,
  `state`. `source`, `snippet` and page `text` are dropped (FR-002). The model reads source from the index at
  distillation time instead (R13).
- **`read_wiki` with a page**: its result is stored as one row, `{kind: page, name, repo, path: directory}`.
- **Status**: `ok`, `unavailable` or `error` (an exception escaped). Unavailable runs keep the tool's reason.

## R4. Which repositories a run belongs to

**Decision**: a run belongs to the repository named in its `repo` argument. Without one, it belongs to every
repository its results came from. A run with neither, such as `list_repositories` or a refused call, belongs to
none: it shows in `ccctx memory list` without `--repo` and is never consolidated. Each run-repository link has its own
`consolidated` flag.

## R5. The subject of a run: the first result's code

**Decision** (clarification Q1): each run gives at most one finding per repository, about one subject. The finding
keeps the tool and arguments that produced it, because a re-ask runs them again (R8).

| Tool | Subject | Finding |
|---|---|---|
| `search_code` | the top hit (a symbol or a wiki page). A `fact` hit (R14) stands for its own subject | defined at, or module page, plus the question's wording |
| `get_symbol` | the first definition returned | defined at, and how many definitions share the name |
| `find_callers` | the definition named in the first row's `callee` | its callers: count and the first 5 names |
| `find_callees` | the definition named in the first row's `caller` | what it calls: count and the first 5 names |
| `impact_of` | the first definition matching the `name` argument | its reach: count, depth and the 5 nearest |
| `read_wiki` with a page | the page | the module's purpose (the page's first line) |
| `read_wiki` list, `list_repositories`, `recall`, failed or empty runs | none | none |

A subject's key is `symbol:<path>:<qualified name>:<kind>` or `page:<page name>`. It is stored in the fact's
metadata, and `list_memories(user_id=<repo>, agent_id="ccctx", metadata_filter={"subject_key": ...})` finds the one
fact for it. Subjects are resolved against the current index at consolidation time. A subject that no longer
exists gives no finding, and the run still counts as consolidated.

## R6. One fact per subject

**Decision**: a fact record's metadata holds:
- **`findings`**: the latest finding for each aspect (`defined`, `module`, `callers`, `callees`, `impact`), each with
  its tool, arguments and run ID.
- **`questions`**: up to 20 distinct question wordings, newest first.
- **`runs`**: the run IDs, and **`refs`**: the references (R8).
- **`agree`, `contradict`, `confidence`** (R7).
- **`state`, `stale_reason`**.
- **`distiller`**: `template/1` or `llm:<model>`, and **`consolidator`**: `memory/<version>`.

The record's `content` is the fact's text, written again whenever the fact changes, by the model (R13) or by the
templates:

> `url_for` is a function in `src/flask/helpers.py`. It is called by 12 symbols, including `Flask.url_for`,
> `redirect_to_login`. Asked as "where is url_for defined", "where's url_for defined?".

**Rationale**: FR-009 allows no second fact for a subject. Keeping the findings, not just the text, lets a newer
finding replace an older one, lets a re-ask run the same tool again, and lets the text follow the code.

## R7. Confidence

**Decision**: `confidence = (1 - 0.5^agree) * 0.5^contradict`, rounded to 3 places.
- **`agree`** counts the runs that confirmed the fact: a new finding for its subject, including the first.
- **`contradict`** counts the times a newer run or a re-ask disagreed:
  - The same tool, asked a wording the fact held, now leads to a different subject. The wording moves to the new
    fact, and the two facts are linked `contradicts`. The same words to another tool are not a contradiction: a
    bare name is resolved to different definitions by `get_symbol` and `find_callers`, both correctly. Each fact
    keeps which tool asked each wording in `asked`.
  - An aspect was replaced by a different value.
  - A re-ask was answered by another subject (R8).
  - The subject's code was removed (R8). This is what FR-010 means by code that changed and was not confirmed
    again.

One run gives 0.5, two give 0.75 and three give 0.875. Each contradiction halves the result. The README documents
this (FR-010). The score is computed by code, never by the model.

## R8. When the code changes: re-ask (clarification Q2)

**Decision**: every consolidation first re-checks the fresh facts of the repository. For each one, it looks up the
subject reference (repository, qualified name and kind, preferring the same path) and compares the content hash. A
page subject compares a hash of the page text.

| Found | Hash | Action |
|---|---|---|
| no | n/a | Stale: ``` `X` was removed ```, `contradict + 1` (confidence halves), status `INVALID` |
| yes | same | Nothing to do. A moved symbol with the same hash is only re-pointed to its new path. |
| yes | different | Re-ask: run each stored finding's tool and arguments again, through the same core functions the tools use (`semantic.search`, `graph.definitions`, `graph.callers`, `graph.calls`, `graph.impact`, `wiki.read`). No run is recorded. |

What a re-ask does with the answers:
- **Same subject answers every aspect**: the findings are refreshed, references re-pointed, and the text rewritten.
  The fact stays fresh.
- **Another subject answers any aspect**: `contradict + 1` and the fact is stale with ``re-asked "<question>": now
  answered by `Y` in `<path>` ``. A new run confirming the fact makes it fresh again (FR-015).

Related references (callers and callees named in the text) are refreshed by the same re-ask. Their removal alone
does not make the fact stale, because the re-ask lists the current callers.

**Rationale**: re-pointing alone would keep a fact whose text no longer holds, such as a caller list from before the
edit. A re-ask costs one search or graph query per aspect, and only for facts whose code changed. Re-checking is
idempotent: a second consolidation finds every hash matching (FR-011).

## R9. Consolidation is incremental, idempotent and runs after every ingestion

**Decision**: `memory.consolidate(conn, repo)` does this per repository:
1. Opens a second connection and holds `select id from ccctx_repos where id = :r for update wait 60` on it for the
   whole consolidation, rolling it back in a `finally`. The package commits on the main connection, which would
   release a lock taken there. A lock on the second connection is unaffected. Two consolidations of one repository
   wait for each other, and a timeout (ORA-30006) fails with "another consolidation of <repo> is running".

   This replaces the `DBMS_LOCK` named lock, because the app user cannot call `DBMS_LOCK` (PLS-00201) and this needs
   no grant (user decision, 2026-10-12).
2. Re-checks (R8).
3. Reads the run links not yet consolidated, in run id order, and turns each into a finding (R5).
4. Merges the findings by subject key into the facts loaded from the package (R6, R7).
5. Writes each created or changed fact once, writing its text with the distiller (R13).
6. Flags the links consolidated and commits.

The package commits its own writes, so steps 5 and 6 are not one transaction. If consolidation dies between them,
the next one re-reads those links. A finding whose run ID is already in its fact's `runs` is skipped, so nothing is
counted twice.

It returns the counts: runs read, created, merged, weakened, marked stale. `ingest.ingest` calls it after the wiki
refresh, on every ingestion, and `Summary.memory` carries the counts or the error. A failure never undoes the
ingestion. Runs recorded while consolidation is running are not among the links it read, so the next run picks them
up.

**Performance**: 1,000 runs touch tens of subjects. Facts are listed once per repository, each subject is resolved
once, and each changed fact is written once. Without a model that is well under SC-004's 1 minute. With a model,
add one call per changed fact, about 1 to 3 seconds each. SC-004 is measured with the template distiller, and the
model's time is reported separately in the summary log.

## R10. Recall: fixed size, fresh first, optionally ranked by topic

**Decision**: `memory.recall(conn, repo, topic, limit)` returns at most `limit` facts (1 to 50, default 20) and the
10 most recent runs, excluding `recall`'s own runs.
- **Order without a topic**: list the repository's facts, then sort by fresh before stale, confidence, and last update.
- **Order with a topic**: package `search(topic, user_id=repo, agent_id="ccctx", record_types=["fact"],
  include_invalid_results=True, max_results=limit)`, then a stable re-sort that puts fresh facts first and keeps the
  search order within each state.
- **Without a repository**: the same call for each repository that has facts, merged by search score.
- **Without the embedding model**: the client has no embedder and its search falls back to keyword matching.

**Rationale**: recall never reads more than 10 runs, and facts grow with subjects, not runs, so SC-007's size and time
stay flat.

## R11. Telling clients to call `recall` first

**Decision**: `recall`'s description starts with "Call this at the start of a session…". `FastMCP(...)` gets
`instructions` saying the same, plus "call recall before searching for something an earlier session may already have
worked out". SC-006 is checked live in a real client.

## R12. Removing a repository

**Decision**:
- **Our run tables**: run-repository links cascade from `ccctx_repos`. A run that ever belonged to a repository is
  marked `scoped`, and consolidation deletes scoped runs that have no repository left.
- **Package facts**: they live in the package's tables, outside our foreign keys. `memory.forget(conn, repo)` calls
  `delete_user(repo, cascade=True)`.
- **No command yet**: no `repo remove` command exists, and this feature does not add one (clarification
  2026-10-12). FR-018 applies once removal exists, and `memory.forget` is ready for it (noted in `registry.py`).
  Until then, FR-018 is tested by calling `forget` and deleting the repository row.

## R13. The distiller: a configured model, or the templates

**Decision**: one setting, `CCCTX_MEMORY_MODEL`, a LiteLLM model string such as `anthropic/claude-sonnet-5-5`,
`ollama/qwen3`, or `oci/<model>`. `CCCTX_MEMORY_MODEL_BASE` and `CCCTX_MEMORY_MODEL_KEY` are optional. Provider keys
otherwise come from LiteLLM's usual variables (`ANTHROPIC_API_KEY`, ...). `config.py` reads them like the database
settings, from the environment or `.env`.

| Setting | Distiller | What leaves the database |
|---|---|---|
| unset (default) | `template/1` | nothing |
| set | `llm:<model>` via `oracleagentmemory.core.llms.llm.Llm(model=..., temperature=0)` | for each fact written: the subject's identity and source (capped at 200 lines), its findings, the names and locations of related symbols, and its question wordings |

The prompt asks for at most 3 sentences, stating only what the findings and source show. `response_json_schema`
requires the answer as `{"text": "..."}`. If a model call fails or returns no text, that fact is written by the
templates, its distiller says so, and consolidation goes on. The summary counts the facts each distiller wrote. No
other model call is made: linking is off (R1), and `recall` and search never call the model.

**Identifier check** (FR-008): the code identifiers in the model's text are a backticked span that is one
identifier, and any word shaped like `snake_case`, `CamelCase` or `a.b`. Inside a backticked phrase only those
code-shaped words count, so prose caught between unpaired backticks is not taken for a name, and a flag such as
`--debug` is not one. Each identifier must appear somewhere in what the model was sent: the subject line, its
source, the findings, the related code and the questions. A dotted name passes when each of its parts does. The
first live run against `qwen3.5:9b` showed why the source has to count: checking only findings and questions
rejected every text, for naming real methods such as `open_session` from the code it had just been shown. Otherwise the text is rejected, the template writes the fact (distiller `template/1`), and a
`{"event": "memory_model_rejected", "repo": ..., "names": [...]}` record goes to stderr. That record holds the
rejected names only, never the text.

**Rationale**: this is the constitution's v1.1.0 exception, with its three conditions met. The model is optional,
what it is sent is documented here and in the README (FR-008a), and every fact records its distiller (FR-007).
Merging, confidence and staleness never depend on the model, so tests are deterministic without one. The model's
own output is tested with a fake `Llm` that returns fixed text.

## R14. Facts in search (Principle V, FR-021)

**Decision**: `semantic.search` asks memory for fact hits after it has its symbol and page candidates.
1. **Fetch**: `memory.search_facts(conn, question, repos, language, k=5)` runs the package
   `search(question, user_id=<repo>, agent_id="ccctx", record_types=["fact"], include_invalid_results=False, max_results=5)`
   for each repository in scope that has facts, and keeps facts whose subject language matches the `language`
   filter. The language is stored in the fact's metadata at consolidation.
2. **Similarity**: package results carry no score, so each fact's similarity to the question is computed in the
   database, with `1 - vector_distance(vector_embedding(ALL_MINILM_L12_V2 using :q as data), vector_embedding(ALL_MINILM_L12_V2 using :t as data), cosine)`
   over the fact's text. That is at most 5 short embeddings per repository, from the same model the symbol
   similarities come from.
3. **Placement**: fact hits go through the same `_place` rule as wiki pages (009 R9). Each sits above the first code
   hit whose similarity is lower than its own, and never above a definition that exactly matches an identifier.
   They count toward `limit`.
4. **The hit**: `kind="fact"`. The name is the subject, the path and line range are the subject's current location,
   the language is the subject's, `state="fresh"`, and the snippet is the fact text (first 800 characters).
   `keyword_rank` is null and `semantic_rank` is the rank among fact hits.

**Cost**: the package is imported on the first search with facts in scope, about a second once per process. If no
repository in scope has facts (a count on our side, from `ccctx_memory_run_repos` having consolidated links), search
never imports it. The retrieval evaluation (T038) checks that placing facts does not lower the top-5 hit rate
(SC-009).

**Recording**: a run whose top hit is a fact gives a finding for that fact's subject (R5), so asking again confirms
the fact.
