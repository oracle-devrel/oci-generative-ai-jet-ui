# Research: Docs, License and Source Layout

## R1. Installing `src/` as the package `golestan_code_mcp`

**Decision**: Switch the build backend from hatchling to setuptools, with `package-dir = {"golestan_code_mcp" = "src"}`
and an explicit `packages` list of the ten packages (`golestan_code_mcp`, `golestan_code_mcp.cli`, …,
`golestan_code_mcp.parsing.languages`).

**Rationale**: Both backends were tried on a throwaway project in the scratchpad (2026-10-16):

| | Wheel | Editable install |
|---|---|---|
| hatchling, `sources = {"src" = "golestan_code_mcp"}` | correct: `golestan_code_mcp/__init__.py`, … | **refused**: "Dev mode installations are unsupported when any path rewrite in the `sources` option changes a prefix rather than removes it" (also with `dev-mode-exact`) |
| setuptools, `package-dir` mapping | correct | works: an import finder maps `golestan_code_mcp` to `src/`; `import sub` fails (nothing leaks as a top-level module); `src` is not on `sys.path`; a new subfolder is found without reinstalling; `__file__` is the real file in `src/` |

The project depends on editable installs twice: `uv sync` installs it editable into `.venv`, and the MCP setup uses
`uv tool install --editable .`. So hatchling can't do it, and setuptools can.

**Alternatives considered**:
- **A `.pth` adding `src/` to `sys.path`** (what hatchling does today): it would expose `config`, `db`, `cli`,
  `search` and the rest as top-level modules and not provide `golestan_code_mcp`. Rejected.
- **Flat top-level modules**: rejected in clarification.
- **Automatic package discovery** (`packages.find`): with the mapping it finds `cli`, `search`, … without the prefix.
  The explicit list is 10 lines, and R5 adds a check so a new folder can't be forgotten.

## R2. License

**Decision**: The MIT License, in `LICENSE` at the root, with `Copyright (c) 2026 Mohammad Hossein Golestan`. The
metadata declares it the PEP 639 way: `license = "MIT"` and `license-files = ["LICENSE"]`, which setuptools 77 and
later support (so `requires = ["setuptools>=77"]`).

**Rationale**: The user asked for free use and left the choice open. MIT is the shortest widely recognized permissive
license: anyone may use, change and share, including commercially, keeping only the notice. It has no patent clause
or notice-file rules to manage.

**Alternatives considered**: Apache-2.0 (adds a patent grant, but longer and needs NOTICE handling); BSD-3-Clause
(near-identical to MIT, less common); GPL (requires derived work to stay open, not "free to use" as the user put it).

## R3. What the README keeps

**Decision**: About 120 lines, in this order:
1. **Title and purpose.** One paragraph: what the server does for an AI coding tool.
2. **Origin.** The idea came from the Coding Challenges article, linked, and the project was built with GitHub Spec
   Kit, linked.
3. **Features.** One line each: structure-aware indexing in 13 languages, hybrid search, the code graph, the module
   wiki, agent memory and usage feedback, all inside the database.
4. **Quick start.** Prerequisites, `.env`, `docker compose up -d`, `uv sync`, `golestan-check-db`, `repo add`,
   `model load`, `ingest`, `search`, `claude mcp add`.
5. **The MCP tools.** The nine tools, one line each.
6. **Documentation.** Links to each `docs/` page and to CLAUDE.md.
7. **License.** MIT, linked.

**Rationale**: It covers what the user asked for: the purpose, the necessary information, the origin, Spec Kit and
the license. Everything else is reference, so it moves out (R4).

The article URL is given without its `utm_` tracking parameters: they only track where a reader came from.

## R4. The docs pages

**Decision**: The README's sections move, almost word for word, into seven pages:

| Page | From the README's sections |
|---|---|
| `docs/setup.md` | Prerequisites, Setup, Checking that data persists |
| `docs/indexing.md` | Registering codebases, Ingesting a codebase |
| `docs/search.md` | Searching code, Usage feedback, Evaluating retrieval |
| `docs/graph.md` | Code relationships |
| `docs/wiki.md` | Module wiki |
| `docs/memory.md` | Agent memory |
| `docs/mcp-server.md` | The MCP server, including the "Changed in" entries |

Layout goes to CLAUDE.md (R6).

**How the pages are written:**
- **Headings.** Each `##` section becomes its page's `#` title, or a `##` heading on a page that holds several
  sections.
- **Links.** Cross-references like "see Usage feedback" and `[Searching code](#searching-code)` become links to the
  page that now holds the section.

**Rationale**: Grouped by what a reader is doing (setting up, indexing, searching, …), as the README already is. Seven
pages, each under about 200 lines.

**Alternatives considered**: one `docs/reference.md` (just the old README under a new name); one page per section (15
small pages, several under 20 lines).

## R5. Checks

**Decision**:
- **`tests/test_layout.py`:**
  - The layout list is read from CLAUDE.md's `## Layout` section, using the same tree format.
  - A new test checks that every folder under `src/` with an `__init__.py` has its package in `pyproject.toml`'s
    `packages`, and that every package listed there has a folder. This keeps R1's explicit list honest.
- **`tests/test_docs.py`** (new) checks every relative link in `README.md`, `CLAUDE.md` and `docs/*.md`:
  - the file it names exists;
  - a `#fragment` matches a heading of the target, slugged as GitHub does: lower-case, punctuation other than `-` and
    `_` dropped, spaces become `-`, and repeated slugs get `-1`, `-2`.
  - Links to `http(s)://` and `mailto:` aren't followed.
- **`specs/014-docs-license-src-layout/docscheck.py`** (one-off, like 013's movecheck) checks that nothing was lost
  from the README:
  - every non-blank line of master's README, outside its Layout section, appears in the new README, `docs/` or
    CLAUDE.md;
  - leading `#` characters and the link edits from R4 are normalized before comparing;
  - an `EXPECTED` list names the lines that were deliberately rewritten.

**Rationale**: FR-007, FR-009 and SC-003 each get one check that fails when they break. Python's standard library is
enough for all three; nothing new is installed.

## R6. CLAUDE.md

**Decision**: CLAUDE.md is at the root, with these sections:
1. **What this is.** Two lines, with a link to the README.
2. **Commands.** `uv sync`, `docker compose up -d`, `uv run golestan-check-db`, `uv run pytest`, running one file,
   `uv run ccctx …`, `ccctx mcp`.
3. **Rules.** From 013's `contracts/conventions.md` and the constitution:
   - files of at most 300 lines, opening with a docstring;
   - one concern per file;
   - functions are reached through their module;
   - tests mirror `src/`;
   - shared test setup lives in `conftest.py` and `support.py`;
   - no new dependency without need;
   - behavior changes need tests first, and ranking changes need `ccctx eval`;
   - never send source code out for indexing;
   - `.env` is never printed or committed.
4. **Spec Kit.** Features go through `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`,
   under `specs/NNN-name/`, and the constitution in `.specify/memory/constitution.md` governs.
5. **Layout.** The README's current tree, with the source paths moved up one level.

**Rationale**: Claude Code loads the root CLAUDE.md into every session. A few lines of rules and commands, plus the
layout the agent needs to find code, is what it can act on. The long reference stays in `docs/`, linked.

## R7. Code changes from the move

**Decision**:
- **Move.** `git mv` every tracked file from `src/golestan_code_mcp/` to `src/`, so git follows each file's history.
  Then delete the leftover folder, which holds only `__pycache__`.
- **`config.py`.** `PROJECT_ROOT = Path(__file__).resolve().parents[1]`: it was `parents[2]`, and the file is now one
  level higher.
- **Nothing else in `src/`.** No other source file names its own path. The imports use the package name, which doesn't
  change.
- **Tests.** Their `Path(__file__)` paths point inside `tests/` or at the root, which don't move. Logger names and
  `-m golestan_code_mcp.…` strings stay the same.
- **`pyproject.toml`.** The build system, the package mapping, the license fields and the version, 1.4.2.
- **`src/__init__.py`.** `__version__ = "1.4.2"`.
- **`uv.lock`.** It is refreshed by `uv lock`.

**Rationale**: A grep for `src/golestan_code_mcp` outside `specs/` found only `pyproject.toml` and the README. The
`.env` lookup is the one path computed from a file's location (spec edge case).

## R8. Existing installs and MCP registrations

**Decision**: Document a one-time reinstall in the README's quick start and in `docs/mcp-server.md`:
- close the MCP clients;
- `uv sync`;
- `uv tool install --editable . --reinstall`.

The registrations (`claude mcp add ccctx -- ccctx mcp`) and the command names don't change.

**Rationale**: The old editable install is a `.pth` file pointing at `src/`. After the move, that would make
`golestan_code_mcp` impossible to import until the project is installed again. The rebuild can't happen while a
running server holds `ccctx.exe` open, which is the same lock that blocked `uv sync` in feature 013.

## R9. Verification that behavior didn't change

**Decision**: The import names don't change, and every file moves unchanged apart from `config.py`'s one line. So
these checks are enough:
- the full test suite;
- `git diff -M` showing only renames, plus the listed edits;
- `ccctx --help` and `ccctx repo list` after the reinstall;
- the MCP server listing its nine tools through the existing registration;
- `golestan-check-db` finding `.env`.

013's `baseline.py` doesn't need to run again.

**Rationale**: 013 needed a behavior baseline because it moved definitions between files. Here no definition moves
relative to the others, so a rename-only diff is a stronger check than comparing outputs.
