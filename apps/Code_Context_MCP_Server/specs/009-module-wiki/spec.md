# Feature Specification: Module Wiki

**Feature Branch**: `009-module-wiki`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Have the tool write and maintain its own architecture notes: a wiki page for each module or directory with at least 10 indexed symbols, covering what it is for, its key symbols and what it depends on. Citations stored as references to real file and symbol records, pages marked stale when a cited symbol's commit changes and recompiled on the next ingestion, a `read_wiki` MCP tool, and wiki pages in hybrid search."

Search answers narrow questions well, such as where `url_for` is defined. It does badly at "what does this module do?", because no single chunk says that. This step has the tool write the answer down: one page per directory that holds enough code. The page says what the directory is for, names its key symbols and lists the modules it uses and is used by.

A page is only worth reading if it is current. Every symbol a page names is stored as a reference to that symbol's record, never as a path or line number in the text. When a cited symbol changes, the page is marked stale, and the next ingestion rewrites it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build the wiki and read a page (Priority: P1)

A developer runs `ccctx wiki build --repo flask`, then `ccctx wiki list --repo flask` to see the pages, and `ccctx wiki show flask/json` to read one. The page says what the json directory does, names its key symbols such as `dumps`, `loads`, `jsonify` and `JSONProvider` with one line on each, and lists the modules it depends on and the modules that use it.

**Why this priority**: the pages are the feature. Everything else keeps them correct or makes them easy to find.

**Independent Test**: build the flask wiki, show `flask/json`, and check that every symbol it names is defined in `src/flask/json` and that its purpose matches the directory's own documentation.

**Acceptance Scenarios**:

1. **Given** flask is indexed, **When** the developer runs `ccctx wiki build --repo flask`, **Then** there is one page for each directory with at least 10 named definitions directly in its files, and none for the others.
2. **Given** the wiki is built, **When** the developer runs `ccctx wiki list --repo flask`, **Then** each page is listed with its name, repository, state (fresh or stale), symbol count and when it was compiled.
3. **Given** the wiki is built, **When** the developer runs `ccctx wiki show flask/json`, **Then** the page has a purpose, up to 10 key symbols with a one-line description each, the modules it depends on, and the modules that use it. Every symbol named is a real definition from that directory.
4. **Given** the wiki is built and nothing changed, **When** the developer builds again, **Then** the pages and their citations are the same.
5. **Given** an unknown or not yet indexed repository, or an unknown page, **When** the developer runs a wiki command, **Then** it exits 1 with the reason.

---

### User Story 2 - Check that citations are real (Priority: P1)

The developer runs `ccctx wiki citations flask/json`. Each line is one citation: the symbol or file cited, its kind, its current path and line range, and the commit it was at when the page was compiled. Each one points at a record that exists.

**Why this priority**: this is what makes a page trustworthy. A citation that is a reference cannot point at something that is not there.

**Independent Test**: list the citations of every flask page and check that each resolves to an existing symbol or file in the index, and that no page's text contains a path or a line number.

**Acceptance Scenarios**:

1. **Given** the wiki is built, **When** the developer lists a page's citations, **Then** every citation resolves to an existing symbol or file record, with its current path and line range.
2. **Given** a page, **When** its text is read, **Then** it names symbols and modules but contains no file paths or line numbers. Locations come only from the citations, read when the page is shown.
3. **Given** a page that names a symbol, **When** its citations are listed, **Then** that symbol is among them. Nothing is named that is not cited.

---

### User Story 3 - Stale pages are marked and rewritten (Priority: P1)

The developer edits a function the `flask/json` page cites, commits, and runs `ccctx ingest flask`. The ingest summary says `flask/json` went stale because that function changed, and that it was recompiled. `ccctx wiki list --repo flask` shows the page fresh again, compiled just now, with what made it stale.

**Why this priority**: a wiki that quietly goes out of date is worse than none, because people keep believing it.

**Independent Test**: in a copy of the flask repository, edit and commit a function that `flask/json` cites, ingest, and check the summary and the page list. Pages that cite nothing in the changed file stay as they were.

**Acceptance Scenarios**:

1. **Given** a page cites a symbol, **When** an ingestion changes that symbol's commit or removes it, **Then** the page is marked stale before anything else reads it.
2. **Given** pages were marked stale, **When** that same ingestion finishes, **Then** each stale page is recompiled from the current code and marked fresh. The ingest summary names each page that went stale, why, and that it was recompiled.
3. **Given** the change crossed the threshold, **When** the ingestion finishes, **Then** a directory that now has at least 10 named definitions gets a page, and a page whose directory no longer qualifies is removed.
4. **Given** a stale page could not be recompiled, **When** anyone reads it or finds it in search, **Then** it is shown as stale with what changed. The ingestion itself still succeeds.
5. **Given** a repository that never had a wiki built, **When** it is ingested, **Then** no pages are created.

---

### User Story 4 - Pages in search and over MCP (Priority: P2)

A developer runs `ccctx search "what does the json module do"`. The `flask/json` page is the top hit, above the json functions. In an AI client, `search_code` returns the same page, and the client calls `read_wiki` with `flask/json` to read it with its citations.

**Why this priority**: a page nobody finds is not used. It depends on the pages existing, so it comes after them.

**Independent Test**: run the search above and check the page ranks first. In the MCP Inspector, call `read_wiki` with `{"page": "flask/json"}` and compare with `ccctx wiki show flask/json`.

**Acceptance Scenarios**:

1. **Given** the flask wiki is built, **When** the developer searches "what does the json module do", **Then** the `flask/json` page ranks above every symbol from the json directory. The hit is marked as a page and shows its name, repository and directory.
2. **Given** a question naming an exact identifier, such as `url_for`, **When** the developer searches, **Then** the definitions of that identifier still come first.
3. **Given** a repository or language filter, **When** the developer searches, **Then** pages are filtered with the same rules as symbols. A page's language is the language of most of its symbols.
4. **Given** the wiki is built, **When** a client calls `read_wiki` with a page name, **Then** it gets the page text, its state, when it was compiled, and its citations with repository, path and line range.
5. **Given** no page name, **When** a client calls `read_wiki`, **Then** it gets the list of pages, optionally for one repository, with name, state and the first line of each.

---

### Edge Cases

- **Line windows are not symbols.** Files indexed as line windows (docs, config, lock files) do not count toward the 10 and are never cited. The flask `docs` directory gets no page.
- **Nested directories count separately.** `src/flask` and `src/flask/json` are two pages. A directory's count is the named definitions in its own files only.
- **Names.** A page is named after its directory inside the repository, with a leading `src/` dropped, so `src/flask/json` is `flask/json`. The repository's root directory is named after the repository. If two pages in different repositories share a name, commands take `--repo` and an ambiguous name is refused with the repositories that have it.
- **No documentation in the code.** A directory whose code has no docstrings or doc comments still gets a page. Its purpose is stated from its structure: what kinds of symbols it holds and what uses it. It does not invent a purpose.
- **A cited symbol is removed.** Its page is marked stale first. A citation is never silently dropped from a page that stays fresh.
- **The search model is not loaded.** The wiki builds, lists and shows. Pages become searchable once the model is loaded, like symbols.
- **A repository is removed.** Its pages and citations go with it.
- **Unchanged ingestion.** An ingestion that changes nothing marks nothing stale and recompiles nothing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `ccctx wiki build [--repo NAME]` MUST compile one page for each directory of an indexed repository whose own files hold at least 10 named definitions. Without `--repo` it builds every indexed repository. Line windows MUST NOT count.
- **FR-002**: A page MUST have a purpose, up to 10 key symbols with one line each, the modules it depends on, and the modules that use it. Dependencies come from the import edges between indexed files, grouped by directory. Imports of packages outside the index are listed by name.
- **FR-003**: A page's text MUST be compiled from the index alone: the symbols, their documentation, and the call and import edges. It MUST NOT be produced by sending code to an outside service, and it MUST NOT state anything the index does not support.
- **FR-004**: Key symbols MUST be chosen by how much the rest of the code uses them, with the directory's main types first. Every key symbol MUST be a named definition in that directory.
- **FR-005**: Each page MUST store its citations as references to existing symbol and file records, one for each symbol or module it names. The page text MUST NOT contain file paths or line numbers.
- **FR-006**: Each citation MUST record the commit and content hash of what it cites at compile time. Each page MUST record who compiled it (the wiki compiler and its version) and when.
- **FR-007**: `ccctx wiki list [--repo NAME]` MUST show each page's name, repository, state, symbol count, compile time, and, for a recompiled page, what last made it stale.
- **FR-008**: `ccctx wiki show PAGE [--repo NAME]` MUST print the page with the current path and line range of each cited symbol, read from the citations.
- **FR-009**: `ccctx wiki citations PAGE [--repo NAME]` MUST print one line per citation: what is cited, its kind, its repository, path and line range, the commit recorded at compile time, and its current commit.
- **FR-010**: An ingestion MUST mark a page stale when the commit of a symbol it cites changes or the symbol is removed. It MUST then recompile every stale page of that repository, add pages for directories that now qualify, and remove pages for directories that no longer do. This applies only to repositories whose wiki was built.
- **FR-011**: The ingest summary MUST name each page that went stale, the cited symbol that caused it, and whether it was recompiled.
- **FR-012**: A page that could not be recompiled MUST stay stale. Every command, tool and search hit that shows it MUST show it as stale. A recompile failure MUST NOT undo the ingestion.
- **FR-013**: Hybrid search MUST return pages alongside symbols, ranked by the same fusion and with the same component scores. A page MUST rank above that directory's symbols for a question about the module as a whole, and exact identifier matches MUST still come first.
- **FR-014**: The `--repo` and `--language` filters MUST apply to pages. A page's language is the language of most of its symbols.
- **FR-015**: `search_code` MUST return page hits marked as pages, with the page name, repository, directory and a snippet. Its description MUST say that page hits can be read with `read_wiki`.
- **FR-016**: A `read_wiki` MCP tool MUST take an optional page name and an optional `repo`. With a name it returns the page text, state, compile time, provenance and citations, each with repository, path and line range. Without one it lists the pages, at most 200. Unknown pages, ambiguous names and unknown repositories MUST come back as a result with a reason, like the other tools.
- **FR-017**: Adding `read_wiki` and page hits extends the tool contract without breaking it. The server's version MUST move to 1.1.0, and the README MUST describe the wiki commands, the tool, and how staleness works.
- **FR-018**: Building and recompiling MUST be logged to standard error: repository, pages built, stale, recompiled and removed, and duration, never page text or source.

### Key Entities

- **Wiki page**: one per qualifying directory. Repository, name, directory, language, text, state (fresh or stale), compile time, compiler version, what last made it stale.
- **Citation**: one per symbol or file a page names. A reference to that record, with the commit and content hash it had when the page was compiled.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `ccctx wiki build --repo flask` builds a page for every directory with at least 10 named definitions, and none for the others, in under 1 minute. At this step's index that is 7 flask pages (`tests`, `flask`, `flask/sansio`, `flask/json`, `tests/type_check`, `examples/tutorial/tests`, `examples/tutorial/flaskr`) and 7 gin pages.
- **SC-002**: The `flask/json` page states the directory's purpose and names at least 5 real symbols from it.
- **SC-003**: Across all flask and gin pages, 100% of citations resolve to an existing symbol or file, and no page text contains a path or line number.
- **SC-004**: After a cited function in `flask/json` is edited, committed and ingested, the ingest summary reports the page stale and recompiled, and its citations point at the new version. Pages that cite nothing in the changed file are not recompiled.
- **SC-005**: `ccctx search "what does the json module do"` returns a wiki page first, and `flask/json` ranks above every symbol from its directory. gin has a `codec/json` page too, so either json page may be first. For three more module questions ("what does the sansio module do" for flask, "what does the binding package do" and "what does the render package do" for gin), the page is in the top 3.
- **SC-006**: The retrieval evaluation's top-5 hit rate does not drop.
- **SC-007**: `read_wiki` returns the same page as `ccctx wiki show` within 3 seconds.

## Assumptions

- **A page is a directory.** The user's example, `flask/json`, is a directory of three files. A single large file such as `app.py` is covered by its directory's page.
- **Pages are written from the code, not by a language model.** The constitution forbids sending code to an outside service, and the database has no text generator. The purpose comes from the directory's own documentation (module docstrings, package comments, the docstrings of its main types), and the rest comes from the index. Pages are as good as the code's documentation. An agent-written page is a later step.
- **Staleness follows the user's rule, the cited symbol's commit.** Ingestion stamps every symbol of a changed file with the new commit, so editing any function in a cited file marks the page stale. Rewriting a page is cheap, so a page rewritten too often is acceptable and one left stale is not.
- **Ingestion recompiles in the same run.** "Recompile on the next re-ingestion" is read as the ingestion that found the change. The user's test expects the page stale and then recompiled after one `ccctx ingest`.
- **The staleness test runs on a copy.** The tool never modifies indexed code, so the live check edits and commits in a scratch clone of flask, not in `../ccctx-repos/flask`.
- **The threshold of 10 is fixed.** It can become a setting when a repository needs another value.
