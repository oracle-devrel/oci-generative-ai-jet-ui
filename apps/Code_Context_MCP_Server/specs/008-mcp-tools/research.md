# Research: Code Context Tools for AI Clients

## R1. How the client starts the server

**Decision**: add a `mcp` subcommand to the existing `ccctx` parser that calls `server.main()` before any database work. The CLI's `main()` connects before running a command, so `mcp` is dispatched ahead of that. The old `golestan-code-mcp` script stays as an alias of the same function, so a client registered in an earlier step keeps working.

**Rationale**: the user pinned `ccctx mcp`. Dispatching it before the connect means the server starts with the database down, and every tool reports the outage itself (spec US4 scenario 4).

**Alternatives considered**: a separate `ccctx-mcp` script (not the pinned spelling). Connecting at startup to fail fast (a client then sees a dead server instead of a reason).

## R2. Starting from an unrelated directory

**Decision**: install with `uv tool install --editable .` from the checkout. `config.PROJECT_ROOT` comes from the package's own file path, and an editable install keeps that path in the checkout, so `.env` is found whatever the working directory. A non-editable install puts the package in a tool environment where there is no `.env`. That case is documented: pass `DB_USER`, `DB_PASSWORD` and the rest with `claude mcp add -e`, since the environment already wins over the file.

**Rationale**: no code change makes FR-003 hold. The process environment overriding `.env` is existing behavior.

**Alternatives considered**: a `CCCTX_ENV_FILE` setting, or looking in the user's home directory. Both add configuration that the editable install makes unnecessary.

## R3. Parameter descriptions and range checks

**Decision**: every parameter is `Annotated[<type>, Field(description=...)]`, which FastMCP copies into the input schema as `description` (probed: it appears next to `default`). Ranges (limit 1 to 50, depth 1 to 5) are stated in the description and checked in the core, not declared as `ge`/`le`. Every tool carries `ToolAnnotations(readOnlyHint=True)`.

**Rationale**: a `ge`/`le` constraint makes pydantic reject the call before the tool runs, as an `isError` result with a validation trace. Checking in the core keeps the step 7 contract that a refusal is a structured `status: "unavailable"` result with a plain reason, and gives the CLI the same check. A value of the wrong type (a string for `limit`) still fails pydantic validation, which is a refusal with a reason, not a crash. The read-only hint lets a client run the tools without asking for confirmation.

**Alternatives considered**: schema `minimum`/`maximum`. It is more visible to a model, but splits refusals into two shapes and duplicates the core's check.

**Unknown arguments**: FastMCP's argument model ignores keys it does not declare, so a client still sending the old `repos` or `question` would silently search everything. The server forbids extra keys on each tool's argument model (`extra="forbid"`), and such a call is refused by validation with the argument's name, like a wrong type.

## R4. What makes a description pick the right tool

**Decision**: each description follows one pattern, in this order:
1. The question it answers, in a developer's words.
2. When to use it, and which neighbor to use instead.
3. What comes back.
4. One hint for the next step, for example "call get_symbol with a hit's name for the full source".

The parameter descriptions carry the formats: a bare name versus `Class.method`, case-sensitivity, and the defaults. The six descriptions are written together in contracts/tools.md so they can be checked against each other for overlap.

**Rationale**: a model picks between tools by comparing their descriptions. Naming the neighbor removes the usual confusions: search versus get_symbol when the name is known, and callers versus impact. The next-step hint is what turns a single search into search, then read.

**Alternatives considered**: short one-line descriptions (the step 7 style). They state what a tool does, but not when to prefer it, which is the failure the user asked to watch for.

## R5. Snippets

**Decision**: the snippet is the first 10 lines of the symbol's stored source, cut to 800 characters. It is fetched in the same query that already loads each hit's path and lines, as `dbms_lob.substr(source, 800, 1)`, and cut to 10 lines in Python.

**Rationale**: a definition's opening lines (signature, docstring, first statements) say what it is, which is what a model needs to decide whether to read on. It costs no extra round trip.

**Alternatives considered**: lines around the matched keywords. A natural-language query often has no literal match, and the keyword side does not report positions.

## R6. Language filter and result count in the search core

**Decision**: `semantic.search` takes `language` and `limit` and applies them where the repository filter already applies. A hit is in scope when its repository and language both match. The pool-widening loop counts in-scope hits against `limit` instead of the fixed 10. A language is valid when it is one the chunker assigns (`python`, `go`, `javascript`, `markdown`, ..., `text`), checked before connecting. An unknown language is refused with the list of valid ones. `limit` must be 1 to 50.

**Rationale**: filtering inside the core keeps the CLI and the tool identical (FR-006). Widening the pool keeps a narrow filter from returning fewer hits than exist. The language list is static, so the check needs no database.

**Alternatives considered**: filtering after the core returns its 10. That returns fewer than asked for whenever a filter is set.

## R7. `get_symbol` lookup

**Decision**: `graph.definitions(conn, name, repos)` uses the same matching as `_targets`: case-sensitive, a bare name matches `x` and `*.x`, chunks are excluded, and an unknown repository is refused first. It returns the first 5 matches by repository, path and start line, each with its stored `source`, plus the total match count. A source longer than 400 lines is cut there and flagged. The full line range is still reported.

**Rationale**: the stored source is exactly what was indexed and what search ranked. The client has no file access, and reading the repository from the tool would break the read-only rule if the working tree had moved on. Sharing the name rules with `find_callers` means a name that works in one tool works in the other.

**Alternatives considered**: reading the file from disk (it can disagree with the index, and it touches the repository). Returning every match (an unbounded result for a name like `get`).

## R8. Measuring tool choice (SC-003, SC-004)

**Decision**: run Claude Code headless from an empty scratch directory, with only this server and no built-in tools:

```sh
claude -p "<question>" --strict-mcp-config --mcp-config ccctx.json --tools "" \
  --allowedTools "mcp__ccctx" --output-format stream-json --verbose
```

Read the `tool_use` events for the order of calls. Five questions, one per intended first tool:
- "using ccctx, how does Flask decide which view function handles a request?" (`search_code`)
- "show me the full source of Flask.dispatch_request" (`get_symbol`)
- "what calls url_for in flask?" (`find_callers`)
- "if I change Flask.url_for, what could break?" (`impact_of`)
- "what does Flask.full_dispatch_request call?" (`find_callees`)

The calls and the routing answer are recorded in the README.

**Rationale**: `--tools ""` removes file access, so the client must use the server, which is what the user's "unrelated directory" test is after. Stream JSON gives the exact tool sequence rather than a reading of the transcript. This runs once, in Polish. It is not a unit test, because it costs model calls and is not deterministic.

**Alternatives considered**: an interactive session observed by eye. The user will still do that, but it gives no record.
