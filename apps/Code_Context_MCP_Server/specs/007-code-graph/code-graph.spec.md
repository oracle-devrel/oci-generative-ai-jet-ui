# Feature Specification: Code Relationship Graph

**Feature directory**: `specs/007-code-graph`
**Created**: 2026-10-11
**Status**: Draft

Search finds code that looks like the question. It cannot say what breaks when a function changes. This step records the structure of the code while it is ingested (which file imports which file, which file defines which symbol, which symbol calls which symbol) and makes it queryable as a graph over the rows already stored. Developers can then ask what calls a symbol, what it calls, and how far a change could spread.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - What calls this? (Priority: P1)

Before changing a function, a developer runs `ccctx callers url_for`. The tool lists every symbol that calls it, with the repository, file and line of each call. Unlike a text search, it does not list mentions in comments, docstrings, documentation or string literals.

**Why this priority**: it is the question asked before every change, and it needs the call relationships, which everything else in this step builds on.

**Independent Test**: ingest flask, run `ccctx callers url_for`, and compare the results with `grep -rn "url_for" ~/ccctx-repos/flask`. Every real call in Python code inside a function or method appears, and no comment, docstring or documentation line does.

**Acceptance Scenarios**:

1. **Given** flask is ingested, **When** the developer runs `ccctx callers url_for`, **Then** each result names the calling symbol, its kind, the repository, the file and the line of the call, and which `url_for` definition it calls.
2. **Given** a function whose name appears only in a comment or docstring of another function, **When** the developer asks for its callers, **Then** that other function is not listed.
3. **Given** a name with several definitions (the `url_for` function and the `Flask.url_for` method), **When** the developer asks with the bare name, **Then** callers of each definition are listed and labeled with the definition they call. Asking with `Flask.url_for` narrows the results to that method.
4. **Given** a name nothing defines, **When** the developer asks for its callers, **Then** the tool says no symbol has that name.

---

### User Story 2 - What does this call? (Priority: P1)

The developer runs `ccctx calls url_for` and sees every symbol that `url_for` calls, with the line of each call. Calls to code outside the repository, such as the standard library, are not listed as symbols, because there is nothing indexed to point at.

**Why this priority**: it is the other half of reading a change, and it uses the same relationships.

**Independent Test**: run `ccctx calls url_for` and check each result against the body of `url_for` in the source.

**Acceptance Scenarios**:

1. **Given** flask is ingested, **When** the developer runs `ccctx calls url_for`, **Then** each result is a symbol called from the body of a `url_for` definition, with the line of the call.
2. **Given** a function that only calls the standard library, **When** the developer asks what it calls, **Then** the tool says it calls no indexed symbols.

---

### User Story 3 - Blast radius (Priority: P1)

The developer runs `ccctx impact url_for --depth 3`. The tool follows the call relationships back from `url_for` through its callers, its callers' callers, and so on, up to 3 hops. It lists every symbol that could be affected, each with how many hops away it is. A direct caller is 1 hop, a caller of a caller is 2. A symbol reachable by several paths is listed once, at its shortest distance.

**Why this priority**: distance is the risk measure the request asks for. A direct caller is a very different risk from something three steps away.

**Independent Test**: run `ccctx impact url_for --depth 1` and `--depth 3`. The depth 3 list is longer, the depth 1 list equals the callers list, and every row shows its hop count.

**Acceptance Scenarios**:

1. **Given** flask is ingested, **When** the developer runs `ccctx impact url_for --depth 3`, **Then** each affected symbol appears once with its hop count from 1 to 3, ordered nearest first.
2. **Given** the same symbol, **When** the developer compares `--depth 1` with `--depth 3`, **Then** depth 3 returns more symbols, and every symbol at depth 1 is also in depth 3 with hop count 1.
3. **Given** a recursive function or a cycle of calls, **When** the developer asks for impact, **Then** the command finishes and lists each symbol once.
4. **Given** `--depth 0`, a negative depth, or a depth above the maximum, **When** the developer runs impact, **Then** the tool refuses it and names the allowed range.

---

### User Story 4 - The graph stays current (Priority: P2)

The developer keeps re-ingesting as the code changes. Relationships are extracted for every file that is re-read, and relationships that came from deleted or changed code disappear with it. After an incremental ingest, the graph is the same as after a full rebuild of the same tree.

**Why this priority**: a stale graph points at code that is not there, which is the same poison step 6 removed from search.

**Independent Test**: delete a calling function, re-ingest, and confirm it no longer appears among the callers. Then compare the graph after an incremental ingest with the graph after `--full`.

**Acceptance Scenarios**:

1. **Given** a function that calls `url_for` is deleted, **When** the developer re-ingests, **Then** `ccctx callers url_for` no longer lists it.
2. **Given** a callee is edited in a file other than its callers' files, **When** the developer re-ingests incrementally, **Then** the unchanged callers still appear among its callers.
3. **Given** a repository indexed before this step, **When** the developer next ingests, **Then** relationships are extracted for every file, not only the changed ones.

---

### User Story 5 - Agents can ask too (Priority: P2)

An AI coding tool connected over MCP asks the same three questions and gets the same answers as the command line, with repository, path and line for every result.

**Why this priority**: the constitution requires every capability to be an MCP tool. It comes after the CLI because both run on the same core.

**Independent Test**: call the MCP tools for callers, calls and impact on `url_for` and compare them with the CLI output.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** a client asks for the callers, callees or impact of `url_for`, **Then** the results match the CLI and every result carries repository, path and line.

### Edge Cases

- A call written as an attribute on an object (`self.url_for(...)`, `app.url_for(...)`) resolves to methods of that name. A bare call (`url_for(...)`) resolves to a function of that name, preferring one in the same file, then one the file imports, then any in the repository.
- A call that matches no indexed symbol (standard library, third-party code, dynamic dispatch) is not an edge. Nothing is invented for it.
- A call at module level, outside every function and class, is attributed to the file.
- A call inside a method is attributed to the method, not to the enclosing class.
- Files that fall back to line windows (no grammar, or a syntax error) contribute no relationships.
- Calls never cross repositories: a symbol in gin is not a caller of a symbol in flask.
- Templates, documentation and other non-code files are out of scope even when they contain call-like text.
- `--repo` limits each command to the named repositories, as in search.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ingest MUST record, for each parsed file, the files it imports within the same repository.
- **FR-002**: Ingest MUST record, for each call in a parsed file, the calling symbol (or the file, for module-level calls), the called symbol, and the line of the call.
- **FR-003**: Calls MUST be found from the parse tree, so text in comments, docstrings and string literals is never a call.
- **FR-004**: The relationships MUST be exposed as a property graph defined over the stored tables, with files and symbols as vertices and imports, calls and defines as edges, without copying the rows into a separate store.
- **FR-005**: `ccctx callers <name>` MUST list the symbols that call any definition matching the name, with repository, kind, path, call line, and the definition called.
- **FR-006**: `ccctx calls <name>` MUST list the symbols called by any definition matching the name, with repository, kind, path and call line.
- **FR-007**: `ccctx impact <name> --depth <n>` MUST list every symbol that reaches the name through calls in at most `n` hops, once each, with its shortest hop count, nearest first.
- **FR-008**: The callers, calls and impact questions MUST be answered by graph pattern queries over the property graph.
- **FR-009**: A qualified name (`Type.method`) MUST match only that definition. A bare name MUST match every definition with that name, whether a function or a method.
- **FR-010**: Each command MUST accept `--repo` one or more times, and search all repositories by default.
- **FR-011**: An unknown name MUST be refused with a message naming it. A depth outside 1 to the maximum MUST be refused with the allowed range.
- **FR-012**: After an incremental ingest, the relationships MUST equal those a full rebuild of the same tree produces. Relationships of deleted or changed code MUST be removed with it.
- **FR-013**: The first ingest of a repository indexed before this step MUST extract relationships for every file.
- **FR-014**: The callers, calls and impact questions MUST be available as MCP tools with the same results as the CLI.

### Key Entities

- **File** (vertex): an indexed file, as today.
- **Symbol** (vertex): an indexed function, method, class or type, as today.
- **Defines** (edge): a file to each symbol it contains. Every symbol has exactly one.
- **Imports** (edge): a file to a file in the same repository that it imports.
- **Calls** (edge): a calling symbol to a called symbol, with the line of the call. A module-level call comes from the file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For flask, `ccctx callers url_for` lists at least 90% of the real calls to `url_for` that `grep -rn "url_for"` finds inside Python functions and methods.
- **SC-002**: None of its results comes from a comment, docstring, string literal, documentation file or template.
- **SC-003**: `ccctx impact url_for --depth 3` returns more symbols than `--depth 1`, and every row shows a hop count between 1 and 3.
- **SC-004**: Each of the three commands answers within 2 seconds on the flask and gin index.
- **SC-005**: After any tested change (add, edit, delete, rename of a caller or a callee), the relationships after an incremental ingest equal those after a full rebuild.
- **SC-006**: The MCP tools return the same results as the CLI for the three questions on `url_for`.

## Assumptions

- "Blast radius" means the symbols that depend on the changed one: its callers, then their callers. Changing `url_for` can break code that calls it, not code it calls.
- Depth defaults to 3, the request's example, and is capped at 5. Five hops already reaches most of a repository.
- Call resolution is by name within the repository, guided by the call form (bare or attribute) and the file's imports. It is not type inference. Dynamic calls, decorators that wrap at runtime and calls through variables are not caught.
- Imports resolve only to files inside the same repository. A Go package import links to the files of that package directory.
- Python, Go and JavaScript are the parsed languages, as today.

## Verbatim Constraints

- `CREATE PROPERTY GRAPH`
- `GRAPH_TABLE`
- `MATCH`
- `ccctx callers url_for`
- `ccctx calls url_for`
- `ccctx impact url_for --depth 3`
- `ccctx impact url_for --depth 1`
- `--depth`
