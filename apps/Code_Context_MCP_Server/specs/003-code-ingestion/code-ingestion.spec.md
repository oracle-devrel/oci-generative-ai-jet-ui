# Feature Specification: Code Ingestion and Chunking

**Feature Branch**: `003-code-ingestion`
**Created**: 2026-10-10
**Status**: Draft
**Input**: Walk a registered repository's working tree, skip ignored, binary, vendored and oversized files, and cut the remaining files into chunks at function, method and class boundaries, with 60-line windows overlapping by 10 lines when a file cannot be parsed. Support at least three languages. Record the commit each symbol was indexed at, and report what was scanned, skipped and indexed, and how long it took.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest a repository and see what happened (Priority: P1)

A developer runs `ccctx ingest flask`. The tool walks the repository and decides which files are worth indexing. It cuts each file into chunks and stores them. It then prints a short summary: files scanned, files skipped and why, symbols indexed, and the time taken.

**Why this priority**: nothing can be searched until code is in the index. The summary is how the developer knows the run did something sensible.

**Independent Test**: run `ccctx ingest flask` on the sample repository, check the three summary lines, and check that `ccctx repo list` now shows non-zero files and symbols for flask.

**Acceptance Scenarios**:

1. **Given** flask is registered, **When** the developer runs `ccctx ingest flask`, **Then** the output has a `Scanned` line with the file count, a `Skipped` line with the count broken down by reason, and an `Indexed` line with the symbol count and the elapsed time.
2. **Given** an ingest has finished, **When** the developer runs `ccctx repo list`, **Then** flask's file and symbol counts match the ingest summary.
3. **Given** flask was already ingested, **When** the developer ingests it again, **Then** the index holds one copy of each file and symbol, not two.
4. **Given** a name that is not registered, **When** the developer runs `ccctx ingest <name>`, **Then** the command fails, names the missing repository and changes nothing.
5. **Given** an ingest that fails partway, for example because the database stops, **When** the developer looks at the index, **Then** the repository's previous index is still there unchanged.

---

### User Story 2 - Chunks follow the code's structure (Priority: P1)

Each stored chunk is one complete function, method or class, with its real name and the exact lines it spans in the file. A developer lists a few symbols and checks one against the file on disk.

**Why this priority**: whole, named units are what make later search results precise and citable. Arbitrary text blocks would cut answers in half.

**Independent Test**: run `ccctx symbols --repo flask --limit 5`, pick one row, open the file and confirm the code at that line range is exactly that function or class.

**Acceptance Scenarios**:

1. **Given** flask is ingested, **When** the developer runs `ccctx symbols --repo flask --limit 5`, **Then** 5 rows appear, each naming a real function, method or class with its kind, file, and start and end lines.
2. **Given** any listed symbol, **When** the developer opens its file, **Then** the first line of the range is the start of that definition (including any decorators) and the last line is its end.
3. **Given** a method defined inside a class, **When** it is indexed, **Then** it is stored as a method named with its class, for example `Flask.route`. The class is also stored as its own symbol.
4. **Given** a Go method with a receiver, **When** it is indexed, **Then** it is stored as a method named with its receiver type, for example `Engine.Use`.

---

### User Story 3 - Files that cannot be parsed are still indexed (Priority: P1)

Some files have no grammar, such as YAML, Markdown or reStructuredText, and some code is broken. The tool does not skip them. It cuts them into 60-line windows that overlap by 10 lines, and marks those chunks as fallback chunks.

**Why this priority**: skipping unparseable files would silently drop content. The overlap stops a boundary from slicing a relevant section in half.

**Independent Test**: ingest a fixture with a 130-line text file and a Python file with a syntax error. Check that both come back as fallback chunks at lines 1-60, 51-110 and 101-130.

**Acceptance Scenarios**:

1. **Given** a 130-line file with no grammar, **When** it is ingested, **Then** it becomes 3 fallback chunks covering lines 1-60, 51-110 and 101-130.
2. **Given** a file of 60 lines or fewer with no grammar, **When** it is ingested, **Then** it becomes one fallback chunk covering the whole file.
3. **Given** a source file in a supported language that fails to parse, **When** it is ingested, **Then** it is chunked into windows like a file with no grammar, and the summary counts it as a parse failure.
4. **Given** both repositories are ingested, **When** the developer runs `ccctx stats --by-language`, **Then** flask shows Python symbols, gin shows Go symbols, and each shows how many fallback chunks it has.

---

### User Story 4 - Every symbol is tied to a commit (Priority: P2)

Every stored symbol records the commit the repository was at when it was indexed, so each chunk can be traced to an exact revision. The next step will use it to make re-ingestion cheap.

**Why this priority**: nothing uses it yet, but adding it later would mean re-indexing everything.

**Independent Test**: ingest flask, read the commit recorded on any symbol, and compare it with the repository's current commit.

**Acceptance Scenarios**:

1. **Given** flask is at commit X, **When** it is ingested, **Then** every symbol stored for flask records commit X.
2. **Given** the working tree has uncommitted changes, **When** it is ingested, **Then** the current file contents are indexed, the symbols record the current commit, and the summary warns that the tree had uncommitted changes.
3. **Given** a registered directory that is not a git repository, **When** the developer ingests it, **Then** the command fails, says a git repository is required, and changes nothing.

### Edge Cases

- **Gitignored files**: files matched by the repository's `.gitignore` files, including nested ones, are skipped and counted as ignored.
- **Vendored directories**: files under dependency directories such as `vendor/`, `node_modules/` and `third_party/` are skipped as vendored, even when they are committed. The list of these directories can be configured.
- **Binary files**: a file is binary if it contains a NUL byte or is not valid UTF-8 text. Binary files such as images and certificates are skipped as binary.
- **Large files**: files over 1 MB are skipped as too large.
- **The repository's own metadata**: the `.git` directory is never walked and never counted.
- **Symbolic links**: they are not followed and are skipped as ignored, so ingestion cannot read outside the repository.
- **Empty files**: an empty file is recorded with no symbols.
- **Nested functions**: a function defined inside another function stays part of its parent's chunk, and is not stored on its own.
- **Code outside any definition**: imports, constants and other top-level statements in a parsed file are not stored as symbols in this step.
- **Deleted directory**: if the registered directory has been deleted, ingest fails with a message naming the path, and the previous index is kept.
- **Database down**: ingest fails within a few seconds with no password in the output, and the previous index is kept.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `ccctx ingest <name>` MUST index the working tree of the registered repository with that name.
- **FR-002**: Ingestion MUST skip files matched by the repository's `.gitignore` rules, files under vendored dependency directories, binary files, files over 1 MB, and symbolic links. Each skip MUST be counted under its reason.
- **FR-003**: The vendored directory list MUST be configurable, with defaults including `vendor`, `node_modules` and `third_party`.
- **FR-004**: Python, Go and JavaScript files MUST be cut into one chunk per function, method and class (Go: function, method, struct or interface type), each with its name, kind, start line, end line and source.
- **FR-005**: A chunk's line range MUST cover the whole definition, including decorators, and nothing outside it.
- **FR-006**: Methods MUST be named with their class or receiver type, as `<Type>.<method>`.
- **FR-007**: Files with no grammar, and supported-language files that fail to parse, MUST be cut into 60-line windows that start every 50 lines, so neighbouring windows overlap by 10 lines. The last window ends at the last line of the file.
- **FR-008**: Fallback chunks MUST be marked as fallback, so they can be told apart from parsed symbols.
- **FR-009**: Every stored symbol MUST record the commit the repository was at when it was ingested.
- **FR-010**: Each file MUST be stored with its path relative to the repository root, its detected language and a hash of its contents. Each symbol MUST be stored with a hash of its source.
- **FR-011**: Re-ingesting a repository MUST replace its previous files and symbols, so the index holds exactly one copy of the current state.
- **FR-012**: An ingest that fails MUST leave the repository's previous index unchanged.
- **FR-013**: Ingest MUST print `Scanned`, `Skipped` (with a count per reason) and `Indexed` (with the symbol count and the elapsed time) lines. It MUST also say how many files fell back to windows, split into no grammar and parse errors.
- **FR-014**: Each ingest MUST also write one structured log record with the same counts, the commit and the duration.
- **FR-015**: `ccctx symbols --repo <name> --limit <n>` MUST list stored symbols with name, kind, file and line range. Parsed symbols come before fallback chunks, then rows are ordered by file and start line.
- **FR-016**: `ccctx stats --by-language` MUST show, per repository and language, the number of files, parsed symbols and fallback chunks.
- **FR-017**: Ingestion MUST only read files. It MUST NOT run, import or modify anything in the repository.
- **FR-018**: Ingest MUST refuse an unregistered name, a directory that is missing or not a git repository, and an unreachable database, with a non-zero exit, a message naming the cause, and no change to the index.

### Key Entities

- **File** (extended from step 2): one indexed file in a repository. Its path relative to the root, its detected language and a content hash.
- **Symbol** (extended from step 2): one chunk. Its name, its kind (function, method, class, type, interface, or a fallback chunk), its line range, its source, a content hash, and now the commit it was indexed at.
- **Ingest summary**: the result of one run. Files scanned, files skipped per reason, files that fell back to windows per cause, symbols indexed, the commit, whether the tree had uncommitted changes, and the elapsed time. It is printed and logged, not stored.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ingesting flask and ingesting gin each finish in under 60 seconds on a development laptop with the database running locally.
- **SC-002**: For 10 parsed symbols picked at random across both repositories, 100% have line ranges that start at the definition's first line (decorator included) and end at its last line.
- **SC-003**: The parser fixtures for Python, Go and JavaScript yield 100% of their top-level functions, classes and types and their methods, and nothing else.
- **SC-004**: A 130-line unparseable file yields exactly 3 windows: 1-60, 51-110 and 101-130.
- **SC-005**: Ingesting the same repository twice in a row leaves the same file and symbol counts as ingesting it once.
- **SC-006**: 100% of stored symbols carry the repository's commit at ingest time.
- **SC-007**: The summary's scanned count equals files indexed plus files skipped. The indexed symbol count equals the repository's symbol count afterwards.
- **SC-008**: No file under `.git`, a vendored directory or a gitignored path appears in the index.

## Assumptions

- **The third language is JavaScript.** It is common and has a maintained grammar. Neither sample repository contains JavaScript, so it is checked with a fixture.
- **"Scanned" counts every file in the working tree** outside `.git`, including the skipped ones. Skipped reasons are listed in the order ignored, vendored, binary, too large, and only reasons with a non-zero count appear.
- **Text files with no grammar are indexed as fallback windows**, including Markdown, reStructuredText, YAML, TOML, HTML and plain text. Their language is taken from the file extension, or `text` when it is unknown.
- **A file counts as failing to parse** when the parser reports any syntax error in it. The whole file then falls back to windows.
- **A class is stored as one symbol covering the whole class, and each of its methods is stored as well**, so a method's lines also fall inside its class's range.
- **The commit is the repository's current commit** (HEAD). A detached HEAD works the same way.
- **The 1 MB limit and the vendored directory list are settings with defaults.** They are not command-line flags.
- **No MCP tool is added in this step.** The constitution allows ingestion and administration through the CLI. Symbol lookup over MCP belongs to the search step.
- **`ccctx symbols` defaults to 20 rows** when `--limit` is not given. It also accepts `--kind` to show only one kind.

## Verbatim Constraints

- Commands: `ccctx ingest flask`, `ccctx ingest gin`, `ccctx symbols --repo flask --limit 5`, `ccctx stats --by-language`
- Summary line labels, in order: `Scanned`, `Skipped`, `Indexed`, shaped like:
  ```
  Scanned   214 files
  Skipped    38 files (12 ignored, 24 binary, 2 too large)
  Indexed  1,847 symbols in 9.2s
  ```
- Fallback windows: `60` lines with `10` lines of overlap
- Ignore rules come from the repository's `.gitignore`
