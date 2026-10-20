# Feature Specification: Database Schema and Repository Registry

**Feature Branch**: `002-repo-registry`
**Created**: 2026-10-10
**Status**: Draft
**Input**: Run Oracle AI Database 26ai Free locally with persistent storage, create a schema for repositories, files and symbols, and let the user register a local codebase by name and list what is registered with its file and symbol counts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The index has a home that survives restarts (Priority: P1)

A developer starts the database container and finds the tables for repositories, files and symbols already in place. They stop and start the container, and everything recorded before is still there.

**Why this priority**: nothing can be registered or indexed until the schema exists, and an index that vanishes on restart is useless.

**Independent Test**: start the container, wait for the ready message, connect and list the tables. Insert a row, restart the container, and read the row back.

**Acceptance Scenarios**:

1. **Given** no container is running, **When** the developer starts it, **Then** a container named `oracle26ai` is running, publishes port 1521, and its log ends with `DATABASE IS READY TO USE!`.
2. **Given** the database is ready, **When** the developer runs the schema setup, **Then** tables for repositories, files and symbols exist under the application user.
3. **Given** the schema already exists, **When** the schema setup runs again, **Then** it succeeds, changes nothing and loses no data.
4. **Given** a registered repository, **When** the container is stopped and started, or removed and recreated without deleting its volume, **Then** the repository is still registered.

---

### User Story 2 - Register a codebase by name (Priority: P1)

A developer points the tool at a local directory and gives it a short name. The tool records it, so later steps can index it and searches can filter by that name.

**Why this priority**: registration is the entry point for every later indexing and search step.

**Independent Test**: run `ccctx repo add ~/ccctx-repos/flask --name flask` and confirm the repository is recorded with its absolute path.

**Acceptance Scenarios**:

1. **Given** an existing directory, **When** the developer runs `ccctx repo add <path> --name <name>`, **Then** the repository is recorded under that name with the directory's absolute path, and the command confirms it.
2. **Given** a path that starts with `~` or is relative, **When** it is registered, **Then** the stored path is the absolute, resolved path.
3. **Given** a path that does not exist or is not a directory, **When** the developer registers it, **Then** nothing is recorded and the error names the path.
4. **Given** the name `flask` is already registered, **When** the developer registers another directory as `flask`, **Then** nothing changes and the error says the name is taken and by which path.
5. **Given** a directory already registered under one name, **When** the developer registers it under a second name, **Then** nothing changes and the error names the existing registration.
6. **Given** the database is down, **When** the developer registers a repository, **Then** the command fails within a few seconds with a message saying the database is unreachable, and no password appears in the output.

---

### User Story 3 - List what is registered (Priority: P1)

A developer lists the registered repositories and sees, for each, its name, its path, and how many files and symbols it holds.

**Why this priority**: it is how the developer confirms registration worked and, later, that indexing did.

**Independent Test**: register flask and gin, run `ccctx repo list`, and compare the output to the expected table.

**Acceptance Scenarios**:

1. **Given** flask and gin are registered and nothing is indexed, **When** the developer runs `ccctx repo list`, **Then** the output has the header `NAME PATH FILES SYMBOLS` and one row per repository, sorted by name, each showing 0 files and 0 symbols.
2. **Given** a repository with recorded files and symbols, **When** the developer lists repositories, **Then** its counts equal the number of its files and symbols in the database.
3. **Given** nothing is registered, **When** the developer lists repositories, **Then** the command succeeds and says no repositories are registered.

---

### User Story 4 - Agents can see the registry (Priority: P3)

An MCP client can list the registered repositories, with the same names, paths and counts the command line shows.

**Why this priority**: the project serves agents through MCP. This is cheap now and needed before search, but nothing in this step depends on it.

**Independent Test**: call the listing tool from the MCP Inspector and compare it with `ccctx repo list`.

**Acceptance Scenarios**:

1. **Given** flask and gin are registered, **When** a client calls the repository listing tool, **Then** it returns both, with name, path, file count and symbol count matching the command line.
2. **Given** the database is down, **When** a client calls the listing tool, **Then** it returns a clear "database unreachable" result, not a crash.

### Edge Cases

- A name with spaces, slashes or uppercase letters: names are short identifiers. Allowed characters are lowercase letters, digits, `-` and `_`, from 1 to 64 characters.
- A trailing slash, `..`, or a symlink in the path: these resolve to one canonical path, so the same directory is never registered twice.
- A path inside this project: allowed. Registration never reads, runs or changes the directory's contents.
- A registered directory deleted later: listing still shows it. Detecting this belongs to indexing.
- Running `repo add` twice with the same name and path: the second run fails as a duplicate and changes nothing.
- Two `repo add` commands racing on the same name: exactly one succeeds. The database enforces uniqueness.
- A file's path within a repository, and a symbol's name within a file, can repeat across repositories without conflict.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The development database MUST run as a container named `oracle26ai` from `container-registry.oracle.com/database/free:latest`, publishing port 1521, with its data on a named volume.
- **FR-002**: Data MUST survive stopping, starting, removing and recreating the container, as long as the volume is kept.
- **FR-003**: A schema setup MUST create the repository, file and symbol tables under the application user, and running it again MUST succeed without changing or losing data.
- **FR-004**: Schema changes MUST be recorded as ordered migrations, each applied once, with the applied set visible in the database.
- **FR-005**: A repository record MUST hold a unique name, a unique absolute path and the time it was registered.
- **FR-006**: A file record MUST belong to one repository and hold its path relative to the repository root, its language and a content hash. A path MUST be unique within its repository.
- **FR-007**: A symbol record MUST belong to one file, and through it one repository, and hold its name, its kind, its start and end lines, its source code and a content hash.
- **FR-008**: A symbol's kind MUST be one of a fixed set that includes at least function, method and class.
- **FR-009**: Removing a repository or a file from the database MUST remove the records that belong to it.
- **FR-010**: `ccctx repo add <path> --name <name>` MUST register an existing directory under the given name, storing its resolved absolute path.
- **FR-011**: `ccctx repo add` MUST refuse a missing path, a path that is not a directory, an invalid name, a name already taken, or a directory already registered. It MUST exit non-zero, record nothing, and name the cause.
- **FR-012**: `ccctx repo list` MUST print the header `NAME PATH FILES SYMBOLS` and one row per repository, sorted by name, with counts taken from the database.
- **FR-013**: Registering or listing MUST NOT read, execute or modify anything inside the registered directory, beyond checking that it exists and is a directory.
- **FR-014**: The command line MUST report an unreachable database within 5 seconds with a non-zero exit and no secret in its output.
- **FR-015**: An MCP tool MUST list the registered repositories with name, path, file count and symbol count, using the same core code as `ccctx repo list`.

### Key Entities

- **Repository**: a registered codebase. A unique short name, a unique absolute path, and when it was registered. It owns many files.
- **File**: one source file within a repository. Its path relative to the repository root, its language and a content hash. It belongs to one repository and owns many symbols.
- **Symbol**: one indexed chunk of code. Its name, its kind (function, method, class and similar), its start and end lines, its source code and a content hash. It belongs to one file and, through it, one repository.
- **Migration**: one applied schema change, with its number and when it was applied.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a stopped database, a developer gets to the ready message and all tables present in under 5 minutes on a first start, and under 1 minute after that.
- **SC-002**: The schema setup runs 3 times in a row without error, and the table contents are identical after each run.
- **SC-003**: After registering flask and gin, `ccctx repo list` shows exactly those 2 rows with the correct absolute paths and 0 files and 0 symbols each.
- **SC-004**: 100% of registered repositories are still listed after a container restart and after a recreate with the volume kept.
- **SC-005**: Each of the 5 invalid registrations (missing path, not a directory, bad name, duplicate name, duplicate directory) exits non-zero and leaves the repository count unchanged.
- **SC-006**: Each command answers within 2 seconds when the database is up, and fails within 5 seconds when it is down.
- **SC-007**: The repository list from the MCP tool matches `ccctx repo list` field for field.

## Assumptions

- This builds on the phase 1 environment: the same container, application user, `.env` settings and Python package. The container is renamed from `ccctx-db` to `oracle26ai` and keeps its volume, so existing data stays.
- `ccctx` is the command-line entry point. It is installed by the project and run through `uv run ccctx` until the developer installs it on their PATH.
- The schema is created by an explicit command, and `ccctx repo add` and `ccctx repo list` apply any missing migrations before they run, so a fresh database works without an extra step.
- A symbol's repository is reached through its file, so it is stored once. Symbols also carry their language and path through their file.
- Removing a repository from the command line is out of scope for this step. The schema supports it, so it can be added later.
- The sample repositories live where phase 1 cloned them, `../ccctx-repos` next to this project. `~/ccctx-repos/...` in the examples stands for that location, and any path works.
- Names are compared exactly. Since only lowercase is allowed, `Flask` is rejected, not merged into `flask`.

## Verbatim Constraints

- Image: `container-registry.oracle.com/database/free:latest`
- Container name: `oracle26ai`
- Port: `1521`
- Ready message: `DATABASE IS READY TO USE!`
- Commands: `ccctx repo add <path> --name <name>`, `ccctx repo list`
- List header columns, in order: `NAME`, `PATH`, `FILES`, `SYMBOLS`
- Example paths: `~/ccctx-repos/flask`, `~/ccctx-repos/gin`
- Example names: `flask`, `gin`
