# Feature Specification: Code Context Tools for AI Clients

**Feature Branch**: `008-mcp-tools`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Hand all of this to an AI client over MCP: a stdio server started with `ccctx mcp`, with four well-described tools: `search_code`, `get_symbol`, `find_callers` and `impact_of`."

Everything built so far works at a terminal. This step hands it to the AI coding tools a developer actually uses. The client starts the server itself as a child process and talks to it over standard input and output, so there is no network listener and no login. Four tools cover what a coding assistant needs: find code, read a symbol in full, see who calls it, and see what a change could break. The client can answer questions about a codebase it cannot open.

Each tool's description is written for a model. It reads them to decide which tool to call, so the descriptions get the same care as the code.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find code by question (Priority: P1)

A developer asks their AI assistant where something happens, for example how Flask routes requests. The assistant calls `search_code` with the question, optionally narrowed to one repository or one language, and gets back up to 10 hits by default. Each hit names the repository, the file, the symbol, its line range and a short snippet, so the assistant can judge relevance without asking for more.

**Why this priority**: finding the relevant code is the first step of nearly every question, and it is the core of what the index already does.

**Independent Test**: in the MCP Inspector, call `search_code` with `{"query": "how are requests routed", "repo": "flask"}` and compare with `ccctx search "how are requests routed" --repo flask`. The same symbols come back in the same order.

**Acceptance Scenarios**:

1. **Given** flask is indexed and the search model is loaded, **When** the client calls `search_code` with a query and `repo: "flask"`, **Then** it gets 10 hits from flask, in the same order as the CLI, each with repository, path, symbol name, kind, line range, a snippet and the scores that explain its rank.
2. **Given** a `language` of `go`, **When** the client searches, **Then** every hit is from a Go file.
3. **Given** a count of 3, **When** the client searches, **Then** it gets at most 3 hits. Given a count outside 1 to 50, the tool refuses with a reason.
4. **Given** an unknown repository, an unknown language or an empty query, **When** the client searches, **Then** the result says why nothing was searched, and the server keeps running.

---

### User Story 2 - Read a symbol in full (Priority: P1)

A snippet shows that `Flask.dispatch_request` matters, but not what it does. The assistant calls `get_symbol` with that name and gets its full source with the repository, file and line range, exactly as it was indexed.

**Why this priority**: without it, a client with no file access can find code but never read it, so every answer would be built from snippets.

**Independent Test**: call `get_symbol` with `{"name": "Flask.dispatch_request"}` and compare the source with those lines of the file in the flask repository.

**Acceptance Scenarios**:

1. **Given** flask is indexed, **When** the client calls `get_symbol` with a qualified name such as `Flask.dispatch_request`, **Then** it gets exactly that definition: its source, repository, path, kind and line range.
2. **Given** a bare name with several definitions, such as `url_for`, **When** the client asks for it, **Then** every matching definition comes back, each labeled with its qualified name, so the client can pick one.
3. **Given** a name that matches more definitions than the result can hold, **When** the client asks for it, **Then** it gets the first ones, the total number of matches, and a flag saying there were more, so it can narrow with a qualified name or a repository.
4. **Given** a name nothing defines, **When** the client asks for it, **Then** the result says no symbol has that name.
5. **Given** a symbol whose source is longer than the limit, **When** the client asks for it, **Then** the source is cut at the limit and marked as cut. The full line range is still reported, so the client knows how much it did not see.

---

### User Story 3 - Trace callers and the reach of a change (Priority: P2)

Before suggesting a change to `url_for`, the assistant calls `find_callers` to see every call site, and `impact_of` to see every symbol within three call hops that could be affected, each with its distance. It answers "what breaks if I change this?" without opening a file.

**Why this priority**: it turns the assistant from a search box into something that can reason about changes. It reuses the graph from the previous step, so it costs little.

**Independent Test**: call `find_callers` with `{"name": "url_for", "repo": "flask"}` and `impact_of` with `{"name": "Flask.url_for", "depth": 3}`, and compare with `ccctx callers url_for --repo flask` and `ccctx impact Flask.url_for --depth 3`.

**Acceptance Scenarios**:

1. **Given** flask is indexed, **When** the client calls `find_callers` for `url_for`, **Then** it gets the same calls as `ccctx callers url_for`: calling symbol, repository, path, line, and which definition is called.
2. **Given** flask is indexed, **When** the client calls `impact_of` for `Flask.url_for` with depth 3, **Then** it gets the same symbols and hop counts as `ccctx impact Flask.url_for --depth 3`, nearest first. Depth defaults to 3 and must be 1 to 5.
3. **Given** a name with more results than the cap, **When** the client asks, **Then** it gets the capped list and a flag saying there were more.

---

### User Story 4 - Plug the server into a real client (Priority: P1)

A developer registers the server once with `claude mcp add ccctx -- ccctx mcp`. Later, in a session started in an unrelated directory, they ask "using ccctx, how does Flask decide which view function handles a request?". The client starts the server on its own, sees its tools, and answers by searching, then reading the symbols it found, without touching the file system.

**Why this priority**: this is the point of the step. Tools a client cannot start, or does not pick, deliver nothing.

**Independent Test**: run `npx @modelcontextprotocol/inspector ccctx mcp`, list the tools, and check all four appear with their descriptions and parameters. Then run the question above in a client session started outside the project and record which tools it calls, in order.

**Acceptance Scenarios**:

1. **Given** the developer has run the setup once, **When** a client starts `ccctx mcp` from any directory, **Then** the server finds its database settings and lists its tools.
2. **Given** a client lists the tools, **When** it reads them, **Then** each tool has a description that says what it answers, when to use it instead of the others, what each parameter means, and what comes back.
3. **Given** the routing question above, **When** the client answers it, **Then** its first call is `search_code`, and it reads the routing code with `get_symbol` rather than asking to open files.
4. **Given** the database is stopped, **When** the client calls any tool, **Then** the tool returns a result saying the database is unreachable, and the server keeps running for the next call.

---

### Edge Cases

- **Nothing on standard output but the protocol.** A stray print or log line on standard output breaks the client. All diagnostics go to standard error.
- **The search model is not loaded.** `search_code` says so and how to fix it. `get_symbol`, `find_callers` and `impact_of` do not need the model and keep working.
- **A repository is registered but not yet indexed.** Every tool treats it as empty rather than failing.
- **Line windows.** Files indexed as line windows have no symbol names. Search can return them, with their path and lines, but `get_symbol` finds named definitions only.
- **Names are case-sensitive**, with the same rules as the graph commands: a bare name matches `x` and `<anything>.x`, a qualified name matches only that definition.
- **The client sends a parameter of the wrong type**, or one the tool does not take. The call is refused with a reason, not a crash.
- **Very large results.** Every tool result is bounded: a count limit for search, a match limit and a source length limit for `get_symbol`, and a row cap for the graph tools.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `ccctx mcp` MUST start the server speaking MCP over standard input and output. It MUST NOT open a network port and MUST NOT require authentication.
- **FR-002**: The server MUST write nothing but protocol messages to standard output. Logs and errors go to standard error.
- **FR-003**: The server MUST find its database settings when started from any directory, in the same way the CLI does.
- **FR-004**: The server MUST offer exactly six tools: the four named ones, `search_code`, `get_symbol`, `find_callers` and `impact_of`, plus two helpers. `list_repositories` lists the registered repositories, so a client learns the valid `repo` values. `find_callees` (the previous `calls`) answers "what does this call?". The `health`, `search`, `callers`, `calls` and `impact` tools are removed. A failed call already reports an unreachable database.
- **FR-004a**: `find_callees` MUST take a `name` and an optional `repo`, and return the same rows as `ccctx calls`, at most 200, with a flag when there were more.
- **FR-005**: `search_code` MUST take a `query`, an optional `repo`, an optional `language` and an optional count `limit` (default 10, 1 to 50). It MUST return, for each hit, the repository, path, symbol name, kind, start and end line, a snippet, and the scores that explain its rank.
- **FR-006**: `search_code` MUST return the same hits in the same order as `ccctx search` for the same query, repository and count. The CLI MUST gain the same language and count options.
- **FR-007**: A search snippet MUST be the opening lines of the hit's indexed source, at most 10 lines and 800 characters.
- **FR-008**: `get_symbol` MUST take a `name` and an optional `repo`, and return every matching named definition up to 5. For each: the qualified name, kind, repository, path, start and end line, and the full indexed source. It MUST report the total number of matches and whether some were left out.
- **FR-009**: `get_symbol` MUST cut a source longer than 400 lines at 400 lines and mark it as cut.
- **FR-010**: `find_callers` MUST take a `name` and an optional `repo`, and return the same rows as `ccctx callers`, at most 200, with a flag when there were more.
- **FR-011**: `impact_of` MUST take a `name`, an optional `depth` (default 3, 1 to 5) and an optional `repo`, and return the same symbols and hop counts as `ccctx impact`, at most 200, with a flag when there were more.
- **FR-012**: Every tool description MUST say what question the tool answers, when to use it rather than the other tools, what each parameter means with its default, and what the result contains. Every parameter MUST carry its own description in the tool's input schema.
- **FR-013**: Every tool MUST return a structured result, never a protocol error, for bad input, an unknown repository or language, a missing search model or an unreachable database. The result MUST say why nothing was returned and MUST NOT contain a password.
- **FR-014**: Every tool result MUST include the repository, path and line range of each item it returns.
- **FR-015**: Every tool call MUST be logged to standard error with the tool name, duration, status and result count, never its arguments or source text.
- **FR-016**: The README MUST explain how to install the `ccctx` command so a client can start it from any directory, how to register the server with Claude Code, and how to inspect it with the MCP Inspector. It MUST note that the tool names changed from the previous step.

### Key Entities

- **Search hit**: one ranked match for a query. Repository, path, symbol name, kind, line range, snippet, and the fused, keyword and semantic scores.
- **Symbol source**: one named definition read back in full. Qualified name, kind, repository, path, line range, source, and whether the source was cut.
- **Caller**, **Callee** and **Impact row**: the rows the graph commands already produce, unchanged.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In the MCP Inspector, all six tools are listed, the four named ones among them, each with a description and a description for every parameter.
- **SC-002**: For `{"query": "how are requests routed", "repo": "flask"}`, `search_code` and the CLI return the same 10 symbols in the same order.
- **SC-003**: For 5 test questions, each written so one tool is clearly the right first step (find code, read a symbol, list callers, gauge impact, and the Flask routing question), a client session with no file access calls the expected tool first in at least 4 of 5.
- **SC-004**: In the routing session, the client answers using only the server's tools, and its answer names the symbols that actually match a URL to a view function.
- **SC-005**: Each tool call on flask and gin returns within 3 seconds, and the tool list is available within 5 seconds of the client starting the server.
- **SC-006**: With the database stopped, every tool returns a reason within 10 seconds, and the next call after the database is back succeeds without restarting the server.

## Assumptions

- `search_code` always uses the hybrid search that `ccctx search` uses by default. The text and vector modes stay CLI-only, so the client has one fewer choice to get wrong.
- `repo` takes one repository name, matching the parameter in the user's example. The client can call again for another repository.
- Tool names are a public contract under the constitution. Renaming `search`, `callers`, `calls` and `impact` and removing `health` is a breaking change, so the server's version moves to the next major release (1.0.0) and the README records the rename.
- "Starts from any directory" assumes `ccctx` is installed from the project checkout, so it finds the project's settings file. Settings passed in the client's environment win over the file, as they do for the CLI.
- The snippet, source and result limits are informed defaults chosen to keep a result readable by a model. They can be tuned in planning without changing the behavior.
- The test in SC-003 and SC-004 uses Claude Code as the client. Any MCP client that reads tool descriptions should behave similarly, but only that one is checked.
