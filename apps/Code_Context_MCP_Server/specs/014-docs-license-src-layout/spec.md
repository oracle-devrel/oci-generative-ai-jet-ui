# Feature Specification: Docs, License and Source Layout

**Feature Branch**: `014-docs-license-src-layout`

**Created**: 2026-10-16

**Status**: Completed

**Input**: User description: "I want to rewrite README.md and mention that it is a free code to use so choose a license
for it. in README.md just add necessary information and the main purpose of the code. also mention that the idea was
initiated from this article: https://codingchallenges.substack.com/p/coding-challenge-139-code-context. I also want to
add a CLAUDE.md file. also remove golestan_code_mcp folder and move all of its content to src folder. also mention that
it was developed with the help of GitHub Spec Kit (https://github.github.com/spec-kit/)"

## Context

The README is about 800 lines. It mixes what the project is for with setup steps, every command's output, ranking
rules, settings tables, the MCP tool reference, a changelog and a list of every file. A visitor has to read a long way
to learn what the project does and whether they may use it. The project has no license, so legally nobody may reuse
it. It doesn't say where the idea came from or how it was built. There is no CLAUDE.md to tell an AI coding agent how
to work in the repository.

The source also sits one folder deeper than it needs to: all of it is under `src/golestan_code_mcp/`, and `src/` holds
nothing else.

This feature gives the project a short README, a free-use license, a CLAUDE.md, a `docs/` folder for the detailed
reference, and a flatter source folder. The program's behavior doesn't change.

## Clarifications

### Session 2026-10-16

- Q: When the code moves from `src/golestan_code_mcp/` into `src/` itself, what should the import name and the
  installed commands be? → A: The package keeps the name `golestan_code_mcp`, and the installed commands and MCP
  registrations keep working unchanged.
- Q: Where should the README's detailed reference go? → A: Into a few topic files under `docs/`, nearly unchanged and
  linked from the README. CLAUDE.md gets the file layout and the working rules.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand the project and whether it may be used (Priority: P1)

A visitor opens the repository. In the first screen of the README they learn what the project is for, where the idea
came from, that it was built with GitHub Spec Kit, and that they may use it freely under a named license. They also
find the minimum steps to get it running, and links to the detailed docs.

**Why this priority**: It is the main request. Without a license nobody may legally reuse the code, and the README is
the first thing every visitor reads.

**Independent Test**: Read the README and the license file. The purpose, the article link, the Spec Kit link, the
license name and the quick start are all there, and the README is a fraction of its current length.

**Acceptance Scenarios**:

1. **Given** the repository, **When** a visitor opens the README, **Then** its opening paragraph states the project's
   main purpose, and the README names the license and links to the license file.
2. **Given** the README, **When** a visitor looks for the origin of the idea, **Then** it links to the Coding
   Challenges article "Coding Challenge #139 - Code Context" and says the idea started there.
3. **Given** the README, **When** a visitor looks for how it was built, **Then** it says it was developed with the help
   of GitHub Spec Kit and links to it.
4. **Given** the repository root, **When** anyone checks the license, **Then** a license file holds the full,
   unmodified text of a recognized free-use open-source license, with the copyright year and holder.
5. **Given** the README's quick start, **When** a new user follows it from a fresh clone, **Then** they have the
   database running, the project installed, a repository indexed and searchable, and the MCP server registered.

---

### User Story 2 - Keep the detailed reference, out of the way (Priority: P2)

A user who needs a detail, such as a setting, an exit code, a tool's parameters or how ranking works, follows a link
from the README to a topic page under `docs/` and finds the same information the README has today.

**Why this priority**: Shortening the README must not lose information that users and maintainers rely on. It
depends on the short README (User Story 1) deciding what stays.

**Independent Test**: Take each section of today's README and find its content in the new README or in one of the
`docs/` pages. Follow every link in the README and docs; each one resolves.

**Acceptance Scenarios**:

1. **Given** any fact in today's README (a setting, an exit code, a tool parameter, a ranking rule, a changelog
   entry), **When** a user looks for it, **Then** it is in the new README or in exactly one `docs/` page.
2. **Given** the README and the `docs/` pages, **When** every relative link is followed, **Then** each one leads to
   a file or heading that exists.

---

### User Story 3 - Guide an AI coding agent working in the repository (Priority: P2)

A developer opens the repository with Claude Code. The agent reads CLAUDE.md and learns how to set up and run the
tests, where each area of the code lives, the project's working conventions, and how features are built with Spec Kit.

**Why this priority**: It is an explicit request, and it is where the file layout moves to from the README.

**Independent Test**: Read CLAUDE.md. It has the commands to install, test and run, the layout of every source and
test file, and the project rules. The layout check passes against it.

**Acceptance Scenarios**:

1. **Given** CLAUDE.md, **When** an agent starts a session, **Then** it finds the commands to install, run the tests
   and start the server, and the rules for changing code (the size limit on files, how modules import each other,
   tests mirroring source).
2. **Given** CLAUDE.md, **When** an agent looks for where a concern lives, **Then** its layout section lists every
   source and test file with its purpose.
3. **Given** a file added without a layout entry, **When** the tests run, **Then** a check fails and names the file,
   as the README's layout check does today.
4. **Given** CLAUDE.md, **When** an agent starts a new feature, **Then** it learns that features go through the Spec
   Kit steps and that the specs live under `specs/`.

---

### User Story 4 - Find the code directly under src/ (Priority: P3)

A maintainer opens `src/` and finds the code's folders and files right there, with no extra folder in between.
Everything works as before, without any change on the user's side.

**Why this priority**: It is requested, but it changes no behavior and has the most risk of breaking the installed
commands, so it comes last.

**Independent Test**: List `src/`: the area folders and top-level files are directly in it, and
`src/golestan_code_mcp/` no longer exists. Run the test suite, the installed commands and the MCP server as before;
everything works and the results are unchanged.

**Acceptance Scenarios**:

1. **Given** the reorganized source, **When** a maintainer lists `src/`, **Then** it holds the package's files and
   area folders directly, and no `golestan_code_mcp` folder.
2. **Given** an existing install and MCP registration, **When** the user starts `ccctx`, `golestan-check-db`,
   `golestan-clone-samples`, `golestan-code-mcp` or the MCP server after updating the project, **Then** each starts and
   works with no change to how it is called or registered.
3. **Given** the moved source, **When** the test suite runs, **Then** it passes as before, and a fresh install also
   works.
4. **Given** the moved source, **When** the program looks for its `.env` file, **Then** it finds the same file in the
   checkout as before.

---

### Edge Cases

- **Paths written into code and docs.** Tests, checks and docs that name `src/golestan_code_mcp/...` must name the new
  places, or the layout and size checks would silently check nothing.
- **The `.env` lookup.** The program finds `.env` relative to its own files; after the move it must still find the
  checkout's `.env`, not a file one folder higher or lower.
- **Running installs.** An MCP client may have the server running while the project is updated. The update must not
  need the user to re-register anything; at most a reinstall of the project, which the docs then say.
- **Specs and history.** Earlier feature specs name the old paths. They are records of past work and are left as they
  are.
- **Spec Kit's own files.** `.specify/` and `.claude/` aren't documentation of the program and aren't listed in the
  layout.
- **Copyright holder.** The license names the author as the copyright holder. If an employer owns work done on its
  time, the author must confirm the license is theirs to grant.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The README MUST open with the project's main purpose in one short paragraph, and MUST be at most about
  150 lines.
- **FR-002**: The README MUST say the idea was initiated by the article "Coding Challenge #139 - Code Context" and link
  to `https://codingchallenges.substack.com/p/coding-challenge-139-code-context`.
- **FR-003**: The README MUST say the project was developed with the help of GitHub Spec Kit and link to
  `https://github.github.com/spec-kit/`.
- **FR-004**: The repository MUST have a license file at its root holding the full text of the MIT License, with the
  year 2026 and the author as copyright holder. The README MUST name the license and link to the file, and the
  project's package metadata MUST declare it.
- **FR-005**: The README MUST contain a quick start: prerequisites, starting the database, installing, indexing a
  repository, searching it, and registering the MCP server, plus links to the detailed docs.
- **FR-006**: Every piece of information in today's README that the new README leaves out MUST appear, nearly
  unchanged, in a topic page under `docs/`, so no information is lost.
- **FR-007**: Every relative link in the README, the `docs/` pages and CLAUDE.md MUST resolve to an existing file or
  heading, and an automated check MUST fail when one doesn't.
- **FR-008**: The repository MUST have a CLAUDE.md at its root, holding: the commands to set up, test and run the
  project; the project's working rules; how features are built with Spec Kit; and the layout of every source and test
  file with its purpose.
- **FR-009**: The automated layout check MUST read the layout from CLAUDE.md instead of the README, and still fail when
  a source or test file is missing from it or listed but absent.
- **FR-010**: The source MUST live directly under `src/`, with no `golestan_code_mcp` folder, while the installed
  package keeps the import name `golestan_code_mcp`.
- **FR-011**: The installed commands (`ccctx`, `golestan-check-db`, `golestan-clone-samples`, `golestan-code-mcp`) and
  existing MCP registrations MUST keep working with no change to how they are called or registered.
- **FR-012**: The program MUST behave exactly as before: the same tools, commands, output, schema, stored values and
  `.env` lookup.
- **FR-013**: Every check and test that names source paths MUST name the new ones, and every existing test MUST still
  pass.

### Key Entities

- **README**: the short front page: purpose, origin, how it was built, license, quick start and links.
- **License file**: the full MIT License text, with year and holder.
- **Docs page**: one topic of the detailed reference, moved from today's README.
- **CLAUDE.md**: the guide for AI coding agents: commands, rules, Spec Kit workflow and the file layout.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time visitor finds the project's purpose, its license and the article it came from within the
  first screen of the README (the first 30 lines).
- **SC-002**: The README is at most 150 lines, against about 800 today.
- **SC-003**: 100% of today's README sections are accounted for: kept in the README or found in a `docs/` page.
- **SC-004**: 0 broken relative links across the README, the `docs/` pages and CLAUDE.md.
- **SC-005**: 0 files under `src/golestan_code_mcp/`, and every installed command and the MCP server start with no
  change to their registration.
- **SC-006**: The test suite passes with the same number of tests as before, apart from the new link check.

## Assumptions

- **License choice.** MIT is chosen: it is the shortest widely recognized license that lets anyone use, change and
  share the code, including commercially, with only the notice kept. The copyright holder is the author, Mohammad
  Hossein Golestan.
- **Behavior frozen.** No tool, command, output or stored value changes. The version gets a patch bump, since nothing
  a user sees changes apart from the documentation.
- **Docs are moved, not rewritten.** The detailed reference keeps its wording, apart from headings and links fixed
  for its new place.
- **CLAUDE.md is for Claude Code.** It follows Claude Code's convention of a CLAUDE.md at the repository root that
  every session loads, so it stays short apart from the layout list.
- **Old specs stay.** `specs/001` to `specs/013` keep naming the old paths, as records of past work.
- **Reinstall.** Users may need to reinstall the project once (`uv sync`, or `uv tool install --editable .` again) for
  the moved files to be found. Their MCP registrations don't change.
