# Feature Specification: Hybrid Code Search

**Feature Branch**: `005-hybrid-search`
**Created**: 2026-10-11
**Status**: Draft
**Input**: Combine keyword and semantic search through one hybrid index, fused by reciprocal rank fusion, so exact identifiers find their definitions while plain-English questions still find code by meaning. Rank an identifier's definition above its call sites. Search all repositories by default, with a flag to narrow to one or more of them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An exact identifier finds its definition first (Priority: P1)

A developer types `ccctx search "url_for"`. The first result is where `url_for` is defined, not one of the dozens of places it is called. The rest of the list still shows related code.

**Why this priority**: looking up a known name is the most common code search, and today's meaning-only search is weak at it.

**Independent Test**: after ingesting flask, run `ccctx search "url_for"` and check that rank 1 is a symbol named `url_for` (the `url_for` function or the `Flask.url_for` method).

**Acceptance Scenarios**:

1. **Given** flask is ingested, **When** the developer searches `url_for`, **Then** the top result is a definition of `url_for`, and every definition of `url_for` ranks above every symbol that only calls it.
2. **Given** an identifier defined as a method, such as `dispatch_request`, **When** the developer searches it, **Then** `Flask.dispatch_request` ranks above its callers.
3. **Given** a qualified name such as `Flask.url_for`, **When** the developer searches it, **Then** that method is the top result.
4. **Given** an identifier that only appears in calls and comments and is defined nowhere in the index, **When** the developer searches it, **Then** the matches are ranked by fusion alone, with no definition boost.

---

### User Story 2 - Questions and identifiers both work in one search (Priority: P1)

The default search fuses keyword matching and semantic matching. Results that both rank highly rise to the top, and neither can drown out the other. Each result says why it ranked: its keyword rank, its semantic rank and its fused score.

**Why this priority**: real searches mix names and concepts. The constitution requires the default search to be fused and explainable.

**Independent Test**: run the routing question and `url_for` in hybrid mode, and check that each result shows both component ranks.

**Acceptance Scenarios**:

1. **Given** both repositories are ingested, **When** the developer searches "how are incoming requests routed to handlers", **Then** the top 10 includes routing or dispatch code from both flask and gin.
2. **Given** any hybrid search, **When** results are shown, **Then** each shows its fused score and its keyword and semantic ranks, with a dash where one method did not find it.
3. **Given** a question unrelated to the code, such as "recipe for sourdough bread", **When** the developer searches, **Then** few results or none come back, as before.

---

### User Story 3 - Compare the modes (Priority: P2)

A developer can force one method: `--mode vector` (meaning only), `--mode text` (exact words only) or `--mode hybrid` (the default). Running the same query in all three shows what fusion adds.

**Why this priority**: it is how a developer trusts and tunes the fusion. Hybrid stays the default either way.

**Independent Test**: run `url_for` in each mode and compare.

**Acceptance Scenarios**:

1. **Given** `--mode text`, **When** the developer searches `url_for`, **Then** every result contains the text `url_for`.
2. **Given** `--mode vector`, **When** the developer searches `url_for`, **Then** results are ranked by meaning, the similarity floor of 0.3 still applies, and results need not contain the word.
3. **Given** `--mode hybrid` or no `--mode`, **When** the developer searches `url_for`, **Then** the top result is a definition of `url_for`.
4. **Given** an unknown mode, **When** the developer searches, **Then** the command refuses and lists the valid modes.

---

### User Story 4 - Narrow a search to some repositories (Priority: P2)

Search covers every repository by default. A developer can narrow it with `--repo`, naming one repository or several.

**Why this priority**: with more than one codebase indexed, the right answer is often in one known place.

**Independent Test**: run `ccctx search "middleware chain" --repo gin` and check that every result is from gin.

**Acceptance Scenarios**:

1. **Given** flask and gin are ingested, **When** the developer searches "middleware chain" with `--repo gin`, **Then** every result is from gin.
2. **Given** `--repo flask --repo gin`, or `--repo flask,gin`, **When** the developer searches, **Then** results come only from those two.
3. **Given** no `--repo`, **When** the developer searches, **Then** all repositories are searched.
4. **Given** a `--repo` naming an unregistered repository, **When** the developer searches, **Then** the command refuses, names it, and searches nothing.

---

### User Story 5 - Agents get the same search (Priority: P2)

The MCP search tool accepts the same mode and repositories as the command line, and returns the same ranked results with their component ranks.

**Why this priority**: agents are the main consumers, and the CLI and MCP must not diverge (constitution III).

**Independent Test**: call the tool with `url_for` and with the routing question, and compare with `ccctx search`.

**Acceptance Scenarios**:

1. **Given** the same query, mode and repositories, **When** a client calls the search tool, **Then** it returns the same results, order and scores as `ccctx search`.
2. **Given** an existing client that passes a single `repo`, **When** it calls the tool, **Then** the call still works.

### Edge Cases

- **Characters with special meaning to keyword search** (quotes, `-`, `&`, `|`, parentheses, `%`, `_`): they are treated as literal text, never as operators, and never cause an error.
- **Case**: `URL_FOR` and `url_for` find the same results. Definitions match their name regardless of case.
- **Several words in text mode**: all of them must appear in a result, so a common word alone does not match everything.
- **Duplicate repositories** in `--repo`: each is searched once.
- **Repositories ingested before this step**: their symbols are searchable once the hybrid index exists, without another ingest.
- **Searching during an ingest**: the search sees the previous complete index or the new one, never a half-replaced mix.
- **Empty question, unreachable database, missing model**: refused as in step 4.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A single hybrid vector index MUST cover each symbol's searchable text (kind, name, path and source), serving both keyword and semantic matching.
- **FR-002**: Searches MUST run through `DBMS_HYBRID_VECTOR.SEARCH`.
- **FR-003**: Hybrid mode MUST fuse keyword and semantic results with `search_scorer` `RRF` and `search_fusion` `UNION`.
- **FR-004**: `ccctx search` MUST accept `--mode` with the values `vector`, `text` and `hybrid`, defaulting to `hybrid`, and MUST refuse any other value.
- **FR-005**: In vector mode the similarity floor of 0.3 MUST still apply. Text mode MUST return only symbols that contain every word of the query.
- **FR-006**: When the query names an identifier that is the name of an indexed symbol, matched case-insensitively against the full name or its last dotted part, those symbols MUST rank above every other result in hybrid and text modes.
- **FR-007**: Each result MUST show its rank, fused score, keyword rank, semantic rank, repository, kind, name, path and line range. A method that did not find the result shows a dash.
- **FR-008**: The fusion's tunable values MUST be settings with documented defaults.
- **FR-009**: Search MUST cover all repositories by default. `--repo` MUST accept one or more repository names, repeated or comma-separated, and restrict results to them.
- **FR-010**: `--repo` naming an unregistered repository MUST be refused, with the name in the message, before any search runs.
- **FR-011**: Query text MUST be treated literally. Characters with keyword-search meaning MUST NOT change the query or cause an error.
- **FR-012**: Search MUST return at most 10 results.
- **FR-013**: Symbols stored before this step MUST be searchable through the hybrid index without re-ingesting.
- **FR-014**: Ingest MUST keep the hybrid index consistent with the stored symbols, so a completed ingest is fully searchable.
- **FR-015**: The MCP search tool MUST accept a mode and a list of repositories, keep accepting a single `repo`, and return the same results as `ccctx search` through the same core code.

### Key Entities

- **Hybrid index**: one index over each symbol's searchable text that answers both keyword and semantic queries.
- **Search result**: a symbol with its rank, fused score, keyword rank, semantic rank, repository, kind, name, path and line range.
- **Definition match**: a symbol whose name, or the last part of its dotted name, equals the identifier searched for.
- **Search mode**: `vector`, `text` or `hybrid`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `ccctx search "url_for"` returns a definition of `url_for` at rank 1, and both definitions rank above every call site.
- **SC-002**: For 10 identifiers that are defined in flask or gin, the definition is at rank 1 in hybrid mode for at least 9 of them.
- **SC-003**: For "how are incoming requests routed to handlers", the hybrid top 10 includes routing or dispatch code from both flask and gin. This was carried over from step 4.
- **SC-004**: `ccctx search "middleware chain" --repo gin` returns only gin results, 100% of the time.
- **SC-005**: "recipe for sourdough bread" returns 3 or fewer results in hybrid mode.
- **SC-006**: Every text-mode result for `url_for` contains `url_for`.
- **SC-007**: A hybrid search over both repositories answers in under 2 seconds.
- **SC-008**: The MCP tool and the command line return identical results for the same query, mode and repositories.

## Assumptions

- **Two definitions can share a name.** Flask defines both a `url_for` helper function and a `Flask.url_for` method. Either counts as "the definition" at rank 1, and both rank above call sites.
- **"Contains every word" uses whole words, ignoring case.** Punctuation inside an identifier, such as the underscore in `url_for`, is part of the word.
- **The definition boost is a fixed rule applied after fusion.** Definition matches come first, in fused order, then everything else in fused order.
- **The default number of results stays 10.** The vector-mode floor stays 0.3.
- **The step 4 per-symbol embedding and its index may be replaced by the hybrid index**, as long as every requirement of step 4 still holds. That is a planning decision.
- **The MCP tool gains optional inputs only**, so existing calls keep working and no breaking version bump is needed.

## Verbatim Constraints

- Query procedure: `DBMS_HYBRID_VECTOR.SEARCH`, with `search_scorer` `RRF` and `search_fusion` `UNION`
- Commands: `ccctx search "url_for"`, `ccctx search "url_for" --mode vector`, `ccctx search "url_for" --mode text`, `ccctx search "url_for" --mode hybrid`, `ccctx search "middleware chain" --repo gin`
- Mode values: `vector`, `text`, `hybrid`
- Flag: `--repo`
