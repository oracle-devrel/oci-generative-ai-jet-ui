# Feature Specification: Agent Memory

**Feature Branch**: `010-agent-memory`

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "Give the server a memory so it stops working the same things out over and over. Record every tool call (question, tool, what came back, when) as episodic memory. Distil those runs into durable facts about the codebase, each with a subject, the fact, a confidence score and the run IDs it came from, merging duplicates. Run this on demand and automatically after each re-ingestion. Expose a `recall` tool that returns the relevant facts and recent runs for a repository, so an agent opens a session already knowing what has been worked out before. Test with `ccctx memory list`, `ccctx memory consolidate` and `ccctx memory facts`."

Today every session starts from nothing. An agent asks where `url_for` is defined, the server searches, the agent
gets an answer, and the next session asks again. This step gives the server a memory in three layers. It records
every call (the episodic log), distils the log into a short list of facts about the codebase, and hands those facts
back through a `recall` tool at the start of the next session.

A fact is only worth recalling if it is still true and you can see where it came from. Every fact keeps the run IDs
it was distilled from and references to the code it describes. When that code changes, the fact is checked again
instead of being served as current.

## Clarifications

### Session 2026-10-12

- Q: When an agent asks a free-text question, what is the fact's subject? → A: The code that answered, meaning the
  top symbol or wiki page. Every wording of the question is kept on the fact, and `recall`'s topic is matched against
  those wordings.
- Q: When an ingestion edits code a fact describes, how is the fact checked? → A: Re-ask. The fact's stored question
  is run again against the new index. The same answer keeps it fresh at the new location; a different answer lowers
  its confidence and marks it stale until a client run confirms it.
- Q: Should memory use Oracle's AI Agent Memory package? → A: Yes, in full, including its language model for
  distilling facts.
- Q: What may that model see? → A: Tool results, code snippets included. The constitution was amended to v1.1.0 to
  allow this for memory distillation only.
- Q: Which model? → A: Configurable and optional. Without one configured, facts are written by a local template
  distiller that sends nothing out, and everything still works.
- Q: Who distils facts: our code or the package's automatic thread extraction? → A: Our code decides each fact's
  subject, merging, confidence and staleness. The configured model, called through the package, only writes the text.
  The package's thread extraction is not used.
- Q: How do facts meet Principle V's "searchable alongside code"? → A: `search_code` also returns fresh facts, as hits
  of kind `fact`, placed like wiki pages and below definitions that exactly match an identifier.
- Q: Does removed code lower a fact's confidence? → A: Yes. It counts as a contradiction, so the confidence halves
  and the fact goes stale.
- Q: What happens to a fact when the same question later gets a different answer? → A: Two facts, linked. The old
  one is weakened and the wording moves to the new answer's fact.
- Q: Does this feature add `ccctx repo remove`? → A: No. FR-018 applies once removal exists, and `memory.forget` is
  ready for it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every tool call is recorded (Priority: P1)

A developer asks the server several related questions about flask in the MCP Inspector: `search_code` with "where is
url_for defined", `get_symbol` with `url_for`, and `find_callers` with `url_for`. They then run
`ccctx memory list --repo flask --limit 10`. They see one row per call, newest first. Each row shows its run ID, when
it ran, the tool, the question or arguments, the client that asked, the status, and what came back: the result count
and the top results with their locations.

**Why this priority**: the log is what everything else is distilled from. Without it there is nothing to remember.

**Independent Test**: make N tool calls in the Inspector, then run `ccctx memory list --repo flask --limit N` and
check there are exactly N new rows and that each one matches its call.

**Acceptance Scenarios**:

1. **Given** the server is running, **When** a client calls any tool, **Then** one run is recorded with a unique run
   ID, the time, the tool, its arguments, the client that called it, the status, the result count, and the identity
   and location of each returned result (repository, path, symbol, line range, score).
2. **Given** runs were recorded, **When** the developer runs `ccctx memory list --repo flask --limit 10`, **Then** the
   10 most recent runs that touched flask are listed, newest first, one per row.
3. **Given** a call that failed or found nothing, **When** it is recorded, **Then** its run shows the status and the
   reason, with no results.
4. **Given** recording fails (for example, the database is unreachable), **When** a client calls a tool, **Then** the
   tool still answers as it would have. The failure is logged.
5. **Given** a call without a repository filter, **When** it is recorded, **Then** the run belongs to every repository
   its results came from, so it appears in each one's list.

---

### User Story 2 - Distil runs into facts (Priority: P1)

The developer runs `ccctx memory consolidate --repo flask`, then `ccctx memory facts --repo flask`. Twenty runs have
become a handful of facts, such as "`url_for` is a function defined in `flask/helpers`", with the subject, the fact
itself, a confidence score, and the IDs of the runs it came from. They ask "where's url_for defined?" once more,
consolidate again, and still see one `url_for` fact. Its confidence has gone up and the new run ID is in its list.

**Why this priority**: the raw log grows by thousands of rows a week and nobody can read it. Facts are what makes the
memory useful.

**Independent Test**: record 20 or so runs over a few topics, consolidate, and check that there are far fewer facts
than runs, that every fact lists run IDs that exist, and that two near-identical questions become one fact.

**Acceptance Scenarios**:

1. **Given** recorded runs, **When** the developer consolidates, **Then** each fact has a repository, a subject, the
   fact text, a confidence between 0 and 1, the run IDs it came from, references to the code it describes, and when it
   was created and last updated.
2. **Given** two runs that found the same thing (for example "where is url_for defined" and "where's url_for
   defined?"), **When** they are consolidated, **Then** there is one fact citing both runs, not two.
3. **Given** a fact already exists, **When** later runs find the same thing and are consolidated, **Then** those runs
   are added to that fact and its confidence goes up. No near-duplicate fact is created.
4. **Given** a fact, **When** a later run of the same question is answered by different code and is consolidated,
   **Then** the old fact's confidence goes down, the question's wording moves to the fact for the new answer, and the
   two facts are linked as contradicting each other.
5. **Given** runs already consolidated, **When** the developer consolidates again with no new runs, **Then** the facts
   are unchanged.
6. **Given** runs that failed, found nothing, or only listed repositories, **When** they are consolidated, **Then**
   they produce no fact.
7. **Given** facts exist, **When** the developer runs `ccctx memory facts --repo flask`, **Then** each fact is listed
   with its subject, text, confidence, state, and the run IDs it came from. A run ID shown there can be found with
   `ccctx memory list`.

---

### User Story 3 - The memory keeps pace with the code (Priority: P2)

The developer edits and commits a function that a fact describes, in a scratch copy of flask, then runs
`ccctx ingest flask`. The ingest summary reports that memory was consolidated: the new runs were distilled, and the
facts whose code changed were checked again. A fact whose symbol moved now points at the new location. A fact whose
symbol is gone is marked stale. Facts about unchanged code stay as they were.

**Why this priority**: a memory that remembers code that no longer exists is worse than none. It depends on facts
existing, so it comes after them.

**Independent Test**: in a scratch clone of flask, create facts about two functions, remove one, edit the other,
commit, ingest, and check the summary and `ccctx memory facts`.

**Acceptance Scenarios**:

1. **Given** facts that reference code, **When** an ingestion changes that code, **Then** the same ingestion
   consolidates the repository's memory and checks those facts against the new index.
2. **Given** a fact's symbol was edited or moved, **When** it is checked, **Then** the fact's stored question is asked
   again against the new index. If the same symbol answers, the fact stays fresh and points at the current version. If
   another one answers, the fact's confidence drops and it is marked stale with what now answers instead.
3. **Given** a fact's symbol was removed, **When** it is checked, **Then** the fact is marked stale with the reason,
   its confidence halves, and it is never shown as current again unless new runs confirm it.
4. **Given** consolidation fails after an ingestion, **When** the ingestion finishes, **Then** the ingestion still
   succeeds and the summary says consolidation failed.
5. **Given** an ingestion that changes nothing, **When** it finishes, **Then** no fact changes state.

---

### User Story 4 - Recall at the start of a session (Priority: P1)

A developer opens a fresh session in a real client and asks "what do you already know about this codebase?". The
client calls `recall` for flask and answers from what comes back: the facts worked out before and the most recent
runs. It does not call `search_code` or any other tool to find them.

**Why this priority**: this closes the loop. Memory that no client reads changes nothing.

**Independent Test**: after consolidating, start a fresh client session, ask the question above, and check in the
client's tool log that `recall` was called and no search tool was. Compare the facts it reports with
`ccctx memory facts --repo flask`.

**Acceptance Scenarios**:

1. **Given** facts exist for flask, **When** a client calls `recall` with `repo: "flask"`, **Then** it gets the
   repository's facts, fresh ones first and then by confidence, and its most recent runs. Each fact has its subject,
   text, confidence, state, source run IDs, and the locations of the code it describes.
2. **Given** a topic, **When** a client calls `recall` with a repository and a topic (for example "sessions"),
   **Then** the facts most related to that topic come first.
3. **Given** no repository, **When** a client calls `recall`, **Then** it gets facts and recent runs across all
   repositories, each labelled with its repository.
4. **Given** a repository with no memory yet, or an unknown repository, **When** a client calls `recall`, **Then** it
   gets an empty result or a reason, like the other tools.
5. **Given** the server's tool list, **When** a client reads `recall`'s description, **Then** the description says to
   call it at the start of a session and before searching for something that may already be known.
6. **Given** a client calls `recall`, **When** the call is recorded, **Then** it is logged as a run but never distilled
   into a fact.

---

### Edge Cases

- **Thousands of runs.** `memory list` is bounded by `--limit` and shows the newest first. `recall` returns at most a
  fixed number of facts and runs, so its size stays the same however long the log gets.
- **Results without code.** `list_repositories` and calls with errors are recorded but distil into nothing.
- **Wiki pages in results.** A `read_wiki` run or a page hit from `search_code` can become a fact about a module, with
  the page as its reference.
- **Same subject in two repositories.** `url_for` in flask and a `url_for` in another repository are separate facts,
  each in its own repository.
- **A run whose results span repositories.** It counts toward facts in each repository it touched, for the results
  from that repository only.
- **Arguments that look like secrets.** Arguments are stored as given. Source code bodies are never stored in runs or
  facts, only the identity and location of what came back.
- **A repository is removed** (no command exists yet). Its runs and facts go with it. A run that also belongs to
  another repository stays for that one.
- **Consolidating while clients are calling.** Runs recorded during a consolidation are picked up by the next one,
  never half-processed.
- **CLI commands are not recorded.** CLI commands such as `ccctx search` are not runs. Only MCP tool calls are recorded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every MCP tool call MUST be recorded as a run with a unique run ID, the time, the tool, its arguments, the
  calling client's name and version (as reported when it connected), the status, the latency, the result count, and
  for each returned result its kind, repository, path, symbol, line range and score.
- **FR-002**: Runs MUST NOT store source code bodies or snippets. They record what was found and where, not its text.
- **FR-003**: Recording MUST NOT change any tool's answer. If a run cannot be recorded, the tool MUST still answer, and
  the failure MUST be logged.
- **FR-004**: A run MUST belong to the repository it was filtered to, or else to every repository its results came
  from.
- **FR-005**: `ccctx memory list [--repo NAME] [--limit N]` MUST list runs newest first, one per row, with the run ID,
  time, tool, arguments, client, status, result count, and top results. The default limit is 20.
- **FR-006**: `ccctx memory consolidate [--repo NAME]` MUST distil the runs not yet consolidated into facts. Without
  `--repo` it consolidates every repository. It MUST report how many runs were read and how many facts were created,
  merged, weakened and marked stale.
- **FR-007**: A fact MUST have a repository, a subject (the symbol or wiki page that answered), the fact text, the
  wordings of the questions that led to it, a confidence between 0 and 1, the IDs of the runs it came from, references to the symbol, file or wiki page records it
  describes with their content hash at the time, its state (fresh or stale), and when it was created and last updated.
  It MUST record who produced it: the consolidator and its version, and the distiller that wrote its text (the
  configured model's name, or the template distiller).
- **FR-008**: A fact's text MUST be stated from what the runs returned and the index supports, and MUST NOT claim more
  than the runs found. When a language model is configured, the text MUST be written by that model through Oracle's AI
  Agent Memory package, from the subject's findings, question wordings and source. With no model configured, or when
  the model call fails, a local template distiller MUST write it instead, sending nothing out. Model-written text
  MUST name only code identifiers that appear in what it was sent: the subject's source, findings, references or
  question wordings. Text that
  names any other identifier is rejected, and the template writes the fact instead.
- **FR-008a**: The model MUST be chosen by configuration, never by default. With none configured, recording,
  consolidation and recall MUST all work and no API key may be required. The README MUST name the setting and list
  exactly what is sent to the model: the subject's source, its findings, the related symbols' names and locations,
  and the question wordings. Search, chunking and embedding MUST NOT send anything out.
- **FR-009**: A fact's subject MUST be the code that answered: the top symbol or wiki page a run returned. Consolidation
  MUST merge a finding into an existing fact when it has the same repository and the same subject, however the
  questions were worded. Merging adds the run IDs, adds the question's wording to the fact's list of questions, and
  raises the confidence. It MUST NOT create a second fact for the same subject.
- **FR-010**: Confidence MUST rise with the number of runs that agree, and fall when later runs contradict the fact or
  its code changes without being confirmed again. Removed code counts as a contradiction, and so does a re-ask
  answered by other code. How it is computed MUST be documented.
- **FR-011**: Consolidation MUST be idempotent. Consolidating again with no new runs and no code change MUST change
  nothing.
- **FR-012**: Runs that failed, returned nothing, came from `list_repositories` or came from `recall` MUST NOT produce
  facts.
- **FR-013**: `ccctx memory facts [--repo NAME] [--limit N]` MUST list facts, fresh first and then by confidence, with
  the subject, text, confidence, state, and source run IDs.
- **FR-014**: Every ingestion MUST consolidate that repository's memory after it commits. It MUST check every fact
  whose referenced code changed. A fact whose code was removed is marked stale with the reason and gains a
  contradiction (FR-010). A fact whose code was edited or moved is re-asked: its stored question is run again against the new index, without recording a run. If
  the same subject answers, the fact is re-pointed at the current version and stays fresh. Otherwise it gains a
  contradiction and is marked stale with what now answers. A consolidation failure MUST NOT undo the ingestion, and the
  ingest summary MUST report what consolidation did or that it failed.
- **FR-015**: A stale fact MUST be shown as stale everywhere it appears. A stale fact becomes fresh again only when new
  runs confirm it.
- **FR-016**: A `recall` MCP tool MUST take an optional `repo`, an optional `topic`, and an optional limit. It returns
  that repository's facts (fresh first, then by confidence, or by relevance to the topic when one is given, matched against
  each fact's subject, text and question wordings) and its
  most recent runs. Each fact includes its subject, text, confidence, state, source run IDs, and the repository, path
  and line range of the code it describes. The result is bounded: at most 50 facts and 10 runs by default. Unknown
  repositories MUST come back as a result with a reason, like the other tools.
- **FR-017**: `recall`'s description MUST tell clients to call it at the start of a session and before searching for
  something that may already be known. The server's instructions MUST say the same.
- **FR-018**: When a repository is removed, its facts and the runs that belong only to it MUST be removed. No removal
  command exists yet, and this feature does not add one. A `memory.forget` function MUST provide the fact removal
  for when one is added, and is tested directly.
- **FR-019**: Adding `recall` extends the tool contract without breaking it. The server's version MUST move to 1.2.0,
  and the README MUST describe the memory commands, the `recall` tool, how facts are merged and scored, and how they go
  stale.
- **FR-020**: Consolidation MUST be logged to standard error: repository, runs read, facts created, merged, weakened
  and marked stale, and duration, never arguments, results or fact text.
- **FR-021**: `search_code` and `ccctx search` MUST return fresh facts that match the question as hits of kind `fact`.
  - **Fields**: the fact's subject as the name, its repository, the subject's current path and line range, the
    subject's language, `state` `fresh`, and the fact text as the snippet.
  - **Placement**: fact hits are placed by their similarity to the question, the same way as wiki pages, and never
    above a definition that exactly matches an identifier in the question.
  - **Filters and limit**: they follow the same `repo` and `language` filters, and count toward the same limit.
  - **Stale facts**: they are never returned in search.
  - **The description**: `search_code`'s description MUST say that a `fact` hit is something an earlier session
    worked out, and that `recall` lists them.

### Key Entities

- **Run** (episodic memory): one MCP tool call. Run ID, time, tool, arguments, client, status, latency, result count,
  the results' identities and locations, the repositories it belongs to, and whether it has been consolidated.
- **Fact** (durable memory): one thing learned about a repository. Repository, subject (the answering symbol or wiki
  page, unique per repository), text, question wordings, confidence, state,
  created and updated times, consolidator version, distiller, and what last made it stale.
- **Fact source**: a link from a fact to a run it was distilled from.
- **Fact reference**: a link from a fact to a symbol, file or wiki page record it describes, with that record's content
  hash at the time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After N tool calls, `ccctx memory list --limit N` shows exactly N new rows, one per call, each matching
  its call's tool and arguments.
- **SC-002**: A session of 20 calls about 5 subjects consolidates into at most 10 facts. Every fact lists at least one
  run ID, and 100% of the run IDs it lists exist.
- **SC-003**: Two near-identical questions, consolidated, give exactly one fact that cites both runs.
- **SC-004**: Consolidating 1,000 runs takes under 1 minute, and consolidating again right after changes nothing.
- **SC-005**: After an edited and a removed function are committed and ingested, every fact about the edited function
  points at its new location, every fact about the removed function is stale, and facts about untouched code are
  unchanged.
- **SC-006**: In a fresh client session, the question "what do you already know about this codebase?" makes the client
  call `recall` and answer with the stored facts, without calling a search tool.
- **SC-007**: `recall` answers within 2 seconds, and its result is the same size with 100 runs or 10,000.
- **SC-008**: Recording runs adds no visible delay: the tools' response times grow by under 5%, and no tool's answer
  changes.
- **SC-009**: The retrieval evaluation's top-5 hit rate does not drop, with facts present in the index.
- **SC-011**: After the `url_for` facts exist, `ccctx search "url_for" --repo flask` still returns the `url_for`
  definitions first, and a `url_for` fact appears in the top 5. For a free-text question such as "where is url_for
  defined", definitions are not promoted (they never were). The fact for the code that answered may rank first, and
  it points at that code.
- **SC-010**: With no model configured and no API key set, SC-001 to SC-007 still pass, and every fact names the
  template distiller. With a model configured, every fact it wrote names that model.

## Assumptions

- **A model writes the text; code decides the fact.** Which subject a run is about, which runs merge, the confidence
  and staleness are all decided by code, so they are the same with or without a model. The configured model only
  writes the fact's text. The template distiller states what a run returned: where a symbol is defined, what calls
  it, what a module is for (from its wiki page), and which questions led to it.
- **"Same finding" means same answering code.** Two runs merge when their top result is the same symbol or wiki page,
  however the question was worded. Wording that is near-identical but leads to different code is a contradiction, not
  a duplicate.
- **The question is the tool's arguments.** `search_code` has a free-text query, and `get_symbol` and the graph tools
  have a name. The run stores the arguments as given and shows the query or name as its question.
- **Only MCP calls are runs.** The user's test asks questions through the Inspector or a client. CLI commands are a
  developer's own tools and are not recorded.
- **Runs are kept.** The episodic log is never pruned in this step. It is bounded at read time by limits, and pruning
  can be added when the log's size becomes a problem.
- **Usage feedback is out of scope.** The constitution allows feedback to influence ranking. That is a later step.
  Facts appear in search as their own hits (FR-021), but they do not change how code hits rank against each other.
- **The staleness test runs on a copy.** The tool never modifies indexed code, so the check edits and commits in a
  scratch clone of flask.
