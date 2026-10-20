# Feature Specification: Split Large Modules

**Feature Branch**: `013-split-large-modules`

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "the python files in src folder are so big. I want to organize them in better way as smaller and more manageable and readable files. the same for the tests in "tests" folder"

## Context

The project's source is 16 files. Nine of them are 360 to 920 lines long and mix several concerns. For example,
the memory file holds run recording, fact distillation, consolidation and fact search together. The language rules
file holds the rules of ten languages. The server file holds all nine tools with their result shapes. The tests mirror
this: the five largest test files are 700 to 930 lines each. A maintainer looking for one behavior has to read through
unrelated code to find it.

This feature reorganizes the code and the tests into smaller files, each with one clear purpose. It changes where code
lives, not what it does.

## Clarifications

### Session 2026-10-15

- Q: What's the most lines one source or test file may have after the split? → A: 300 lines.
- Q: How should the smaller source files be arranged? → A: In folders by area, with the tests mirroring them.

## User Scenarios & Testing *(mandatory)*

The users of this feature are the people who maintain the project: they read, change and review its code and tests.

### User Story 1 - Find and change one concern in a small source file (Priority: P1)

A maintainer wants to change how one thing works, such as how facts are distilled, how C# is parsed, or what the
`search_code` tool returns. They open the file named for that concern and find all of it there, in a file short enough
to read in one sitting, without code for unrelated concerns around it.

**Why this priority**: This is the request. The size of the source files is what the user finds hard to manage, and
every later change to the project benefits from it.

**Independent Test**: Measure every source file's length and check that each has one stated purpose. Then run the
whole test suite unchanged, and compare the tools, the command-line output and the stored index against the
version before the split. Everything is identical.

**Acceptance Scenarios**:

1. **Given** the reorganized source, **When** a maintainer lists its files, **Then** no file is longer than the size
   limit (FR-002) and each file states its purpose in its first lines.
2. **Given** a concern such as "fact distillation" or "the C# language rules", **When** a maintainer looks it up in the
   layout list of the README, **Then** it names the one file that holds it.
3. **Given** the reorganized source and the test suite as it was before the split, **When** the suite runs, **Then**
   every test passes, apart from tests skipped for a missing database, as before.
4. **Given** the same database state, **When** the MCP tools, the command-line commands and an ingest run against the
   version before and after the split, **Then** the tool list, the results, the printed output and the stored rows are
   the same.

---

### User Story 2 - Find the tests for one concern in a small test file (Priority: P2)

A maintainer who changed one concern wants to run and read just its tests. The tests are split the same way as the
source, so the tests of one concern are in a file named for it, and running that file alone checks that concern.

**Why this priority**: The tests are the second half of the request. Splitting them is most useful once the source
split has settled where each concern lives, so it follows User Story 1.

**Independent Test**: Measure every test file's length. Compare the list of tests before and after: every test still
exists, under a new name or file where it moved. Run the suite in a random order and file by file; it passes.

**Acceptance Scenarios**:

1. **Given** the reorganized tests, **When** a maintainer lists them, **Then** no test file is longer than the size
   limit (FR-002), and each test file is named for the source file or concern it tests.
2. **Given** the list of tests before the split, **When** it is compared with the list after, **Then** every test that
   existed before is found again, and the record of moves (FR-009) accounts for every renamed or merged one.
3. **Given** any one test file, **When** it runs alone, **Then** it passes, without depending on another test file
   having run first.
4. **Given** setup repeated across test files, such as connecting to the database or creating a throwaway repository,
   **When** the tests are reorganized, **Then** it is written once and shared.

---

### User Story 3 - Keep the documentation in step with the new layout (Priority: P3)

A maintainer new to the project reads the README's layout section to learn where things are. It lists every source
and test file with its purpose, and stays correct because a check fails when a file is added, removed or renamed
without updating it.

**Why this priority**: A new layout is only useful if people can find their way around it. It depends on the first
two stories being done.

**Independent Test**: Compare the README's layout list with the files on disk. Add a file without listing it and see
the check fail.

**Acceptance Scenarios**:

1. **Given** the reorganized project, **When** a maintainer reads the README's layout section, **Then** every source
   and test file is listed with a one-line purpose, and none that no longer exists is listed.
2. **Given** a file added without a layout entry, **When** the tests run, **Then** a check fails and names the file.

---

### Edge Cases

- **Code shared by two new files.** A helper used by two of the split files lives in one place and is imported by
  both. It is never copied.
- **Circular dependencies.** Splitting must not create two files that need each other to load. Where the old file
  relied on order inside it, the new files keep that order explicit.
- **A long function in a short file.** File length is the target, not function length. A function is not cut in two
  just to move lines between files.
- **Tests that replace a function during the test.** Some tests swap a function for a stand-in, such as recording
  for memory or the clock. After the split they must still replace the function the code actually calls, or they
  would pass without testing anything.
- **Entry points and configuration.** The installed commands (`ccctx`, `golestan-check-db`, `golestan-clone-samples`,
  `golestan-code-mcp`) and the MCP client registration keep working without any change on the user's side.
- **Database-dependent results.** Some search results depend on the state of the database's indexes. Comparisons
  between before and after are made on the same database state, one run after the other.
- **Files that are already small.** Files under the limit with one clear purpose stay as they are.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST behave exactly as before. The same MCP tools with the same names, inputs and results;
  the same commands, options and printed output; the same database schema, migrations and stored rows; and the same
  retrieval evaluation results.
- **FR-002**: No source file and no test file may be longer than 300 lines. Test data files (the sample code the
  parser tests read) are exempt.
- **FR-003**: Each source and test file MUST hold one concern and MUST state that concern in its opening lines.
- **FR-004**: The source MUST be grouped into folders by area, such as indexing, search, graph, wiki, memory and
  server, each folder holding the small files of that area. Small files that belong to no area (configuration, the
  database connection) may stay at the top level.
- **FR-005**: The tests MUST mirror the source folders, and each test file MUST be named for the source file or
  concern it tests, so that a maintainer can find the tests of a source file from its name and place.
- **FR-006**: Every test that exists before the split MUST exist after it, with the same check. A test may move,
  be renamed, or be merged with an identical one; none may be dropped or weakened.
- **FR-007**: Setup repeated across test files (database connection, throwaway repositories, git helpers) MUST be
  written once and shared.
- **FR-008**: The installed commands and the MCP server registration MUST keep working with no change on the
  user's side.
- **FR-009**: The feature MUST keep a record of where each source concern and each test moved, so a reviewer can
  check that nothing was lost.
- **FR-010**: The README's layout section MUST list every source and test file with its purpose, and an automated
  check MUST fail when a file is missing from it or listed but absent.
- **FR-011**: An automated check MUST fail when a source or test file exceeds the size limit, so the files stay small.
- **FR-012**: No code may be duplicated to make the split. Code needed by more than one file lives in one place.

### Key Entities

- **Source file**: one file of the program's code, with one concern, a stated purpose and a length.
- **Test file**: one file of tests, named for the source file or concern it covers.
- **Concern**: one coherent responsibility, such as "the C# language rules", "fact distillation" or "the
  `read_wiki` tool".
- **Move record**: the mapping of each concern and test from its old file to its new one.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of source and test files are within the size limit (FR-002), against 9 of 16 source files and
  11 of 17 test files over 300 lines today.
- **SC-002**: The longest source file is at most half the length of today's longest (916 lines).
- **SC-003**: The test suite passes with the same number of tests as before the split, plus only the new checks
  (FR-010, FR-011).
- **SC-004**: On the same database state, before and after give identical tool listings, tool results, command output,
  stored rows and retrieval recall.
- **SC-005**: For each of 10 concerns picked from the README, a maintainer finds the single file holding it from the
  layout section alone, without searching the code.
- **SC-006**: Every test file passes when run on its own and when the suite runs in a random order.

## Assumptions

- **Behavior is frozen.** This is a reorganization only. No feature is added and no bug is fixed. Bugs found along
  the way are recorded, not changed.
- **Who it is for.** The audience is the project's maintainers. Users of the tools and commands should notice nothing.
- **Internal imports may change.** Only this project imports its own modules, so the paths code uses to import other
  code inside the project may change. The installed commands may not.
- **Constitution unchanged.** No principle is affected: nothing about indexing, retrieval, tools or memory changes.
- **Verification.** Before and after are compared on the same database, one run after the other, because search
  results depend on the state of the database's indexes.
- **Version.** The release number gets a patch bump, since nothing a user sees changes.
