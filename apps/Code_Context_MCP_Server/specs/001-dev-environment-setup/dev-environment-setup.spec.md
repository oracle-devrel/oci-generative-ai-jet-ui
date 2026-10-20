# Feature Specification: Development Environment Setup

**Feature Branch**: `001-dev-environment-setup`
**Created**: 2026-10-10
**Status**: Draft
**Input**: Introductory step of the code context challenge: prepare a reproducible local environment (Python, a local Oracle AI Database in a container, a code parser, an MCP client) and two sample repositories in different languages, for the server called `golestan_code_mcp`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start the local database with one command (Priority: P1)

A developer clones the project, copies the example environment file, and starts the local Oracle AI Database with a single documented command. The database comes up, reports healthy, and accepts a login from the credentials in the environment file. Stopping and restarting keeps the data.

**Why this priority**: every later feature (ingestion, vector search, MCP tools) stores and queries data here. Nothing else can be tested without it.

**Independent Test**: on a machine with only a container runtime and Python installed, follow the README, start the database, and run the provided connectivity check. It prints the database version and confirms the vector type is available.

**Acceptance Scenarios**:

1. **Given** a fresh clone and a running container runtime, **When** the developer runs the documented start command, **Then** the database reaches a healthy state and the connectivity check succeeds.
2. **Given** a running database with a test table, **When** the developer stops and starts it again, **Then** the test table still exists.
3. **Given** the environment file is missing or a credential is blank, **When** the developer runs the connectivity check, **Then** it fails with a message naming the missing setting and never prints a password.

### User Story 2 - Python project that installs and runs its checks (Priority: P1)

The developer creates the project's Python environment with one command, which installs the database driver, the code parser with Python and Go grammars, the MCP SDK, and the test runner. A smoke test suite runs and passes.

**Why this priority**: the constitution requires test-first work, so a working test command must exist before any feature code.

**Independent Test**: run the install command, then the test command. The suite reports the parser smoke test passing, and the database test passing when the database is up (skipped with a clear reason when it is not).

**Acceptance Scenarios**:

1. **Given** a supported Python version, **When** the developer runs the install command, **Then** all dependencies install from pinned versions without manual steps.
2. **Given** an installed environment, **When** the developer parses a small Python file and a small Go file with the parser smoke test, **Then** each reports the start and end lines of its functions and classes or types.
3. **Given** the database is not running, **When** the developer runs the test command, **Then** database tests are skipped with a reason and the parser tests still run.

### User Story 3 - Sample repositories ready to index (Priority: P2)

The developer runs one script that clones Flask (Python) and Gin (Go) into a shared repositories folder outside this project. Running it again does not fail or re-download.

**Why this priority**: two real projects in two languages exercise multi-repository and multi-language support from the start, but they are only needed once ingestion work begins.

**Independent Test**: run the script on an empty folder, confirm both repositories exist with a recorded commit; run it again and confirm it reports them as already present.

**Acceptance Scenarios**:

1. **Given** the repositories folder does not exist, **When** the developer runs the clone script, **Then** it creates the folder and clones both repositories.
2. **Given** both repositories are already cloned, **When** the developer runs the script again, **Then** it skips them and exits successfully.
3. **Given** no network access, **When** the developer runs the script, **Then** it exits with an error naming the repository that failed.

### User Story 4 - Reach a stub MCP server from an MCP client (Priority: P2)

The developer starts a minimal `golestan_code_mcp` server that exposes one health tool. They connect with the MCP Inspector, list tools, and call the health tool, which reports the server version and whether the database is reachable.

**Why this priority**: it proves the client-to-server loop works before real tools exist, so later failures point at tool logic, not wiring.

**Independent Test**: launch the Inspector against the documented server command, list tools, call the health tool, and see a structured result.

**Acceptance Scenarios**:

1. **Given** an installed environment, **When** the developer connects the MCP Inspector to the server, **Then** the tool list contains the health tool with a description and input schema.
2. **Given** the database is running, **When** the health tool is called, **Then** it returns the server name, version, and database status "reachable".
3. **Given** the database is stopped, **When** the health tool is called, **Then** it returns database status "unreachable" with a short reason instead of failing the call.
4. **Given** the README's client configuration snippet, **When** the developer adds it to Claude Code, **Then** Claude Code lists the server's tools.

### Edge Cases

- The container runtime is not installed or not running: the start command says so instead of a raw error.
- The database container is still initializing on first start (can take minutes): the connectivity check waits up to a bounded time, then reports "still starting".
- The chosen database port is already in use: the port is configurable through the environment file.
- The machine is Windows: every documented command has a form that works in PowerShell, and paths with spaces work.
- The repositories folder path is set to a location inside this project: the clone script refuses, so sample code is never committed or indexed as project code.
- Grammar for a language is missing: the parser smoke test names the missing grammar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST provide a container definition that starts Oracle AI Database 26ai locally with persistent storage, using one documented command.
- **FR-002**: Database credentials, host, port, and service name MUST be read from environment variables, with an example environment file committed and the real one ignored by version control.
- **FR-003**: The project MUST provide a connectivity check that confirms login, prints the database version, and confirms the vector type is usable, without ever printing secrets.
- **FR-004**: The project MUST define a Python project with pinned dependencies covering the database driver, the code parser with Python and Go grammars, the MCP SDK, and the test runner, installable with one command.
- **FR-005**: The project MUST include a parser smoke test that extracts function and class/type boundaries (start and end lines) from a Python file and a Go file.
- **FR-006**: The test command MUST run parser tests always and skip database tests with a stated reason when the database is unreachable.
- **FR-007**: The project MUST provide an idempotent script that clones Flask and Gin into a configurable repositories folder outside this project, and refuses a folder inside it.
- **FR-008**: The project MUST provide a runnable stub MCP server named `golestan_code_mcp` exposing a health tool that reports server name, version, and database reachability.
- **FR-009**: The health tool MUST return a result, not an error, when the database is unreachable.
- **FR-010**: The README MUST document prerequisites, setup steps in order, the MCP Inspector command, and a client configuration snippet for Claude Code, in forms that work on Windows PowerShell and a POSIX shell.

### Key Entities

- **Environment configuration**: the set of settings (database user, password, host, port, service name, repositories folder) that every script reads. Password is secret.
- **Sample repository**: a cloned third-party project with its name, language, source URL, local path, and checked-out commit.
- **Health result**: server name, server version, database status (reachable or unreachable), and an optional reason.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer with only a container runtime, Python, and git installed goes from fresh clone to a passing test suite in under 30 minutes of hands-on time, following only the README.
- **SC-002**: The connectivity check passes on 3 of 3 consecutive cold starts of the database.
- **SC-003**: Data written before a database restart is present after it in 100% of trials.
- **SC-004**: The parser smoke test finds 100% of the top-level functions and classes/types in its Python and Go fixtures.
- **SC-005**: The MCP Inspector lists and successfully calls the health tool on the first attempt, with the database up and with it down.
- **SC-006**: Running the clone script twice in a row succeeds both times and downloads nothing the second time.
- **SC-007**: No secret value appears in any committed file or in the output of any provided script.

## Assumptions

- Python 3.11 or newer is the language (3.11.8 is installed on the reference machine).
- Docker is the container runtime; the definition should also work with compatible runtimes but is only tested on Docker.
- The database image is Oracle's free Oracle AI Database 26ai container image, which includes AI Vector Search.
- Tree-sitter is the code parser, since it covers both Python and Go.
- The default repositories folder is a sibling of this project, `../ccctx-repos`, matching the challenge text; the user's sample commands mix `~/ccctx-repos` and a Windows path, so the sibling path is the single default and it is configurable.
- The health tool is the only tool in this step; real indexing and search tools are later features.
- The MCP server communicates over standard input/output for local clients.

## Verbatim Constraints

- MCP server name: `golestan_code_mcp`
- Sample repository URLs: `https://github.com/pallets/flask.git`, `https://github.com/gin-gonic/gin.git`
- Repositories folder name: `ccctx-repos`
- Database column type to verify: `VECTOR`
