# Feature Specification: Usage Feedback

**Feature Branch**: `011-usage-feedback`

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "Let the server learn from which results actually turned out to be useful. Record when
a client uses a result by citing it in an answer or opening it, and mark it as used, so a returned result can be told
apart from one that helped. Boost frequently used symbols on future searches, capped at 20 percent, so the boost
nudges the ordering without ever overruling relevance. Halve the weight of feedback every 30 days. Testing: a gold
set of questions and expected paths; `ccctx eval --gold gold.json` prints `Questions: 20` and `recall@10: 0.65
(13/20)`; `ccctx eval --gold gold.json --with-feedback` must improve or hold; hammering one symbol must not make it
appear for `ccctx search \"database connection pooling\"`; backdated feedback must show halved influence in `ccctx
feedback list --repo flask`."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record which results helped (Priority: P1)

An AI client searches the code, opens some of the hits, and cites one of them in its answer. The server records
each of those as a use of that result, so anyone looking at past tool calls can see, for every search, which of the
returned results were actually used and which were ignored.

**Why this priority**: Every later step (boosting, decay, evaluation with feedback) needs recorded uses. On its own it
already answers "do clients use what search returns?".

**Independent Test**: Run a search through the MCP interface, open one hit and cite another, then list recorded tool
calls and feedback: the search shows two of its results as used, one opened and one cited, and the feedback list
shows one use for each of the two results.

**Acceptance Scenarios**:

1. **Given** a client session that ran a search, **When** the client cites one hit with the new "mark used" tool,
   **Then** a cited use of that result is recorded, attributed to the client and the time, and linked to the search
   that returned it.
2. **Given** a client session that ran a search, **When** the client opens one of its hits (reads its source or its
   wiki page), **Then** an opened use of that result is recorded and linked to that search.
3. **Given** a client that reads a symbol it was never shown by a search in this session, **When** it opens the
   symbol, **Then** no use is recorded (it was not a returned result).
4. **Given** a client that opens and then cites the same result in one session, or cites it several times, **When**
   feedback is listed, **Then** that result has one use from that session, counted as cited.
5. **Given** a client that cites something that is not indexed, **When** the call returns, **Then** it answers "not
   found" with the reason, and nothing is recorded.
6. **Given** recorded tool calls, **When** the operator lists them, **Then** each search shows how many of its
   results were used and which ones.

---

### User Story 2 - Bounded boost for used results (Priority: P1)

The next time anyone searches, results that were used often rank a little higher than results that were not, but
never by more than 20 percent of their relevance score, and never so much that they appear for a question they were
not already found for.

**Why this priority**: This is the point of the feature. The cap is what stops the loop where popular results get
shown, then used, then boosted, until search only returns the same few things.

**Independent Test**: Record many uses of one symbol, then search for something unrelated (`ccctx search "database
connection pooling"`): the symbol does not appear. Search for a question it does match: it rises, and its shown
feedback boost is at most 20 percent.

**Acceptance Scenarios**:

1. **Given** a result with recorded uses that a search found anyway, **When** the search ranks it, **Then** its score
   is raised by a feedback boost between 0 and 20 percent, and the hit shows the boost and the score before it.
2. **Given** one symbol with a thousand recorded uses, **When** a search runs for a question that does not find that
   symbol on relevance, **Then** the symbol is not among the hits.
3. **Given** any amount of feedback, **When** any hit is ranked, **Then** its boost never exceeds 20 percent, and a
   result with no feedback has a boost of 0.
4. **Given** a search for an exact identifier, **When** feedback exists for other symbols, **Then** the identifier's
   definitions still come first.
5. **Given** feedback for symbols, **When** the operator asks for a search without feedback, **Then** the ranking is
   exactly what it would be with no feedback recorded.

---

### User Story 3 - Feedback fades over time (Priority: P2)

Each use counts less as it ages: a use 30 days old counts half as much as a new one, 60 days old a quarter, so what
the server learned during last quarter's refactor fades out instead of steering searches forever. The operator can see
this and can wipe feedback for a repository.

**Why this priority**: Without decay, old habits stay in the ranking forever. It depends on Story 1's records but not
on Story 2.

**Independent Test**: Record a use dated today and another dated 30 days ago for two symbols, then run `ccctx
feedback list --repo flask`: the backdated symbol's weight is half the other's.

**Acceptance Scenarios**:

1. **Given** one cited use recorded now, **When** feedback is listed, **Then** the result's weight is 1.0.
2. **Given** one cited use recorded 30 days ago, **When** feedback is listed, **Then** its weight is 0.5 and its boost
   is lower than that of a result with one use recorded now.
3. **Given** recorded feedback, **When** the operator resets feedback for a repository, **Then** that repository's
   feedback list is empty and its searches rank as if no feedback had ever been recorded; other repositories keep
   theirs.

---

### User Story 4 - Measure retrieval with and without feedback (Priority: P2)

The operator keeps a gold set: a file of questions, each with the paths where the answer lives. Running the
evaluation prints how many questions there are and how many have an expected path in the top 10 hits. Running it
again with feedback switched on shows whether feedback helped, held steady, or pushed right answers out.

**Why this priority**: This is how the operator catches a boost that is too strong. It can be built first as a
baseline, independent of the other stories.

**Independent Test**: Run `ccctx eval --gold gold.json`: it prints `Questions: 20` and `recall@10: <r> (<n>/20)`.
Record uses of the expected results for some questions, then run with `--with-feedback`: recall is at least the
baseline.

**Acceptance Scenarios**:

1. **Given** a gold set of 20 questions, **When** the evaluation runs, **Then** it prints `Questions: 20` and
   `recall@10: <fraction to two decimals> (<hits>/<questions>)`, followed by one line for each question that missed.
2. **Given** recorded feedback, **When** the evaluation runs without `--with-feedback`, **Then** feedback is ignored
   and the result equals a run with no feedback recorded.
3. **Given** recorded feedback, **When** the evaluation runs with `--with-feedback`, **Then** searches use feedback
   the same way normal searches do.
4. **Given** an evaluation run, **When** it finishes, **Then** it has recorded no tool calls and no feedback of its
   own.
5. **Given** a gold file that is missing, is not valid, or names an unregistered repository, **When** the evaluation
   runs, **Then** it stops with a message naming the problem and exits with a failure status.

---

### Edge Cases

- A used result is later removed or moved by a re-ingest: its feedback stays listed but marked as no longer indexed,
  and it boosts nothing. A symbol moved to a new path starts without feedback.
- A repository is removed: its feedback is removed with it.
- A use dated in the future (for example by a clock error or a bad backdate) is rejected.
- Many clients use the same result: each session adds one use; the boost still saturates at 20 percent.
- A client marks a result used without any search in the session: the use is recorded as cited but not linked to a
  search (citing from memory or from an earlier session is still a sign of usefulness).
- Feedback recording fails (database busy): the client's tool call still answers normally; recording is best effort,
  like run recording.
- A gold question lists several expected paths: it counts as a hit when any of them appears in the top 10. An
  expected directory matches any hit inside it.
- A gold question has no hits at all: it counts as a miss.

## Requirements *(mandatory)*

### Functional Requirements

**Recording use**

- **FR-001**: The server MUST offer an MCP tool with which a client marks a result it cited as used, identifying the
  result the way search hits identify it (repository, path, name).
- **FR-002**: When a client opens a result that a search returned to it earlier in the same session (reads the
  symbol's source or the page's text), the server MUST record an opened use of that result.
- **FR-003**: The server MUST NOT record a use for a result that no search returned to the session, except through
  the explicit mark-used tool (FR-001).
- **FR-004**: Each use MUST record the result, the kind (cited or opened), the client, the time, and the search run
  that returned it when there was one.
- **FR-005**: Within one session, a result MUST count as at most one use; a cited use replaces an opened one.
- **FR-006**: A mark-used call for a result that is not indexed MUST answer "not found" with the reason and record
  nothing.
- **FR-007**: The record of past tool calls MUST show, for each search, which of its returned results were used.
- **FR-008**: Recording a use MUST NOT delay or fail the client's tool call.

**Ranking**

- **FR-009**: A result's feedback weight MUST be the sum over its uses of the use's base weight (cited 1.0, opened
  0.5) halved for every 30 days of the use's age, computed when it is read.
- **FR-010**: Search MUST raise each hit's score by a feedback boost that is 0 with no feedback, grows with the
  feedback weight, and never exceeds 20 percent of the hit's score.
- **FR-011**: Feedback MUST only reorder the hits search found for the question on relevance; it MUST NOT add a
  result to the hits.
- **FR-012**: The definitions of an exact identifier MUST keep coming first regardless of feedback.
- **FR-013**: Each hit MUST show its feedback boost alongside its other scores, and the score before the boost.
- **FR-014**: The boost cap (20 percent) and the half-life (30 days) MUST be configurable, with these documented
  defaults.

**Inspecting and controlling feedback**

- **FR-015**: `ccctx feedback list --repo <name>` MUST list the repository's used results with their number of
  uses, current weight, current boost, and the time of the last use, highest weight first.
- **FR-016**: `ccctx feedback add` MUST let the operator record a use of an indexed result by hand, with an optional
  age in days (backdating) and an optional count, attributed to the operator. A negative age (a use in the future)
  MUST be rejected.
- **FR-017**: `ccctx feedback reset` MUST delete all feedback for one repository, or for all repositories when asked
  explicitly, and report how many uses it deleted.
- **FR-018**: `ccctx search` and the search tool MUST accept a switch to rank without feedback.

**Evaluation**

- **FR-019**: `ccctx eval --gold <file>` MUST run every question in the gold file through search and print the
  number of questions and recall@10 as a fraction to two decimals with hits over questions, then one line per missed
  question.
- **FR-020**: Without `--with-feedback`, the evaluation MUST rank without feedback; with it, as normal search does.
- **FR-021**: The evaluation MUST NOT record tool calls or feedback.
- **FR-022**: The project MUST include a versioned gold set of 20 plain-language questions over the sample
  repositories (flask and gin), each with its expected paths and its repository.
- **FR-023**: A gold file that is missing, invalid, or names an unregistered repository MUST stop the evaluation with
  a message naming the problem and a failure exit status.

**Lifecycle**

- **FR-024**: Feedback for a result that is no longer indexed MUST boost nothing and MUST be listed as no longer
  indexed; removing a repository MUST remove its feedback.
- **FR-025**: Feedback MUST never alter indexed source content.

### Key Entities

- **Use**: one record that a result helped: the result's repository, path, name and kind; cited or opened; the
  client; the time; the search run that returned it, if any.
- **Result feedback**: the aggregate for one result: number of uses, decayed weight, boost, last use. Derived from
  uses when read, never stored as a running total.
- **Gold set**: a versioned file of questions, each with a repository and one or more expected paths.
- **Evaluation result**: number of questions, hits, recall@10 and the missed questions, with or without feedback.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every search a client ran, the operator can tell which returned results were used, from the record
  of past tool calls alone.
- **SC-002**: With feedback recorded for the expected results of at least 5 gold questions, recall@10 with feedback is
  greater than or equal to recall@10 without it.
- **SC-003**: After one symbol receives 1,000 uses, it does not appear in the top 10 hits for "database connection
  pooling", and for every gold question it enters the top 10 only if its score without feedback was at least 1/1.2
  of the tenth hit's (the most a 20 percent boost can lift it).
- **SC-004**: No hit's feedback boost exceeds 20 percent, for any amount of feedback.
- **SC-005**: A single use backdated 30 days shows a weight of 0.50 (and 60 days 0.25), to two decimals.
- **SC-006**: The existing identifier evaluation keeps its result (top-1 10 of 10) with feedback switched on.
- **SC-007**: Searches with feedback take no more than 10 percent longer than searches without it.
- **SC-008**: After a reset, the repository's searches rank identically to searches without feedback.

## Assumptions

- "Session" is one MCP client connection; an opened use only counts for results a search returned in that
  connection. Tools are called by AI clients that follow the tool descriptions; the server cannot see the client's
  final answer, so "cited" means the client called the mark-used tool.
- Feedback is per result, not per question: a used symbol gets the same boost for every question that finds it. This
  is what the brief asks for ("boost frequently used symbols"); the cap and FR-011 keep it from taking over.
- Results include symbols and wiki pages. Fact hits are not boosted (they come from memory, not from use).
- A citation is a stronger signal than opening, so opened uses weigh half as much. The boost grows in proportion to
  the weight until it reaches the cap (at a weight of 5, five fresh citations), so halving a weight below that halves
  its boost, and a thousand uses get the same 20 percent as five.
- Old uses are never deleted automatically; decay makes them negligible (a year-old use weighs under 0.0003).
- The gold set's baseline is whatever the current search achieves; `0.65 (13/20)` in the brief is illustrative.
- `ccctx feedback add` and `reset` are operator tools for testing and maintenance, available only through the CLI,
  not to MCP clients.
- The server version becomes 1.3.0 and the MCP tool count rises by one, with its contract test (constitution VI).
- Constitution V (recorded, bounded, decaying, resettable) and IV (explained scores, configurable weights) are met by
  FR-004/010/009/017 and FR-013/014.
