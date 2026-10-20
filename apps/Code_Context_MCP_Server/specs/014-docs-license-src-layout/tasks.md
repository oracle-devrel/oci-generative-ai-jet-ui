---

description: "Task list for Docs, License and Source Layout"
---

# Tasks: Docs, License and Source Layout

**Input**: Design documents from `specs/014-docs-license-src-layout/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/interfaces.md, quickstart.md

**Tests**: Requested by the spec. FR-007 and FR-009 call for automated checks, and constitution VI requires test-first.
The checks are written first and fail before the work that satisfies them.

**Organization**: Tasks are grouped by user story. Each one can be checked on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

## Path Conventions

- **Until T023.** Source paths are `src/golestan_code_mcp/...`.
- **From T023 on.** Source paths are `src/...`, the same files one level up.
- **Old README.** Master's README is the source for the moved text: read it with `git show master:README.md`, never
  from the working copy, since the working copy is rewritten in T008.

---

## Phase 1: Setup (Checks First)

**Purpose**: The checks that later phases must turn green (research R5).

- [X] T001 [P] Create `tests/test_docs.py` with:
  - **One module docstring**, stating its purpose.
  - **A link test**, parametrized per document over `README.md`, `CLAUDE.md` and every `docs/*.md`:
    - find every Markdown link `[text](target)` whose target isn't `http://`, `https://` or `mailto:`, ignoring
      fenced code blocks;
    - check that the file part, resolved against the document's folder, exists;
    - when the target has a `#fragment`, check that it equals a heading slug of the target file;
    - the slug rules are GitHub's: lower-case, punctuation other than `-` and `_` dropped, spaces become `-`, and
      repeats get `-1`, `-2`.
  - **README tests:**
    - at most 150 lines;
    - the first 30 lines contain `https://codingchallenges.substack.com/p/coding-challenge-139-code-context`,
      `https://github.github.com/spec-kit/` and a link to `LICENSE`;
    - the word `MIT` appears.
  - **A license test:** `LICENSE` exists, its first line is `MIT License`, and it contains
    `Copyright (c) 2026 Mohammad Hossein Golestan` and the standard "Permission is hereby granted, free of charge"
    paragraph.

  Keep it under 300 lines, with stdlib only. Run `uv run pytest tests/test_docs.py -q` and confirm it fails: there is
  no LICENSE, no CLAUDE.md and no `docs/`, and the README is too long.
- [X] T002 [P] Create `specs/014-docs-license-src-layout/docscheck.py`.
  - **Inputs.** It reads `git show master:README.md`, drops the `## Layout` section and fenced-block markers, and
    keeps every other non-blank line.
  - **Normalizing.** Each line is normalized: `#` heading markers and surrounding whitespace are stripped, and
    Markdown links are reduced to their text, so `[Usage feedback](search.md#usage-feedback)` compares equal to
    `Usage feedback`.
  - **Searching.** It looks for each normalized line among the normalized lines of the working copy's `README.md`,
    `CLAUDE.md` and `docs/*.md`.
  - **Output.** It prints each missing line with its old line number, skipping the ones listed in
    `EXPECTED = {old line text: reason}`, and ends with `N lines missing`. It exits 1 when N > 0.

  Run it now: it should report nearly every line missing, since `docs/` doesn't exist yet.

---

## Phase 2: Foundational (Layout List Moves to CLAUDE.md)

**Purpose**: Today the layout test reads the README's `## Layout`. It must read CLAUDE.md before the README is
rewritten, so the suite stays green through every later phase.

**⚠️ CRITICAL**: T008 (README rewrite) must not start before T004 passes.

- [X] T003 Create `CLAUDE.md` with a heading `# CLAUDE.md` and a `## Layout` section. Move the README's whole
  `## Layout` section into it, intro sentence and `text` code block, unchanged. For now, leave the section in the
  README too; T008 drops it.
- [X] T004 Change `tests/test_layout.py` to read CLAUDE.md:
  - `readme_layout()` becomes `claude_md_layout()` and reads `ROOT / "CLAUDE.md"`, with the same `## Layout` regex and
    tree parsing;
  - `test_readme_lists_every_source_and_test_file` becomes `test_claude_md_lists_every_source_and_test_file`, with the
    assertion messages saying "CLAUDE.md's Layout";
  - the module docstring says CLAUDE.md instead of the README.

  Run `uv run pytest tests/test_layout.py -q`: it passes. Add an empty `src/golestan_code_mcp/search/extra.py`, see
  the test fail and name it, then delete the file.

**Checkpoint**: The layout list lives in CLAUDE.md, and the README can be rewritten freely.

---

## Phase 3: User Story 1 - Understand the project and whether it may be used (Priority: P1) 🎯 MVP

**Goal**: A short README with the purpose, the article, Spec Kit and the license, plus the MIT license file.

**Independent Test**: The README and LICENSE tests in `tests/test_docs.py` pass, and a reader finds the purpose,
the article, Spec Kit and the license in the first 30 lines. The README's links to `docs/` pass once US2 is done.

- [X] T005 [P] [US1] Create `LICENSE` with the standard MIT License text:
  - the first line is `MIT License`;
  - then `Copyright (c) 2026 Mohammad Hossein Golestan`;
  - then the permission paragraph, the notice condition and the warranty disclaimer, word for word, wrapped as
    choosealicense.com gives them.
- [X] T006 [P] [US1] Add the license metadata to `pyproject.toml` under `[project]`: `license = "MIT"` and
  `license-files = ["LICENSE"]`. Hatchling accepts both, so this stands before the backend switch in T023. Run
  `uv build --wheel -o %TEMP%\ccctx-wheel` and check that `METADATA` has `License-Expression: MIT` and that the wheel
  holds `licenses/LICENSE`. Delete the temp folder.
- [X] T007 [US1] Draft the new README outline in research R3's order and check it against FR-001–FR-005 before
  writing. The quick-start commands are taken verbatim from master's README Setup, Registering, Ingesting,
  Searching and The MCP server sections.
- [X] T008 [US1] Rewrite `README.md`, at most 150 lines:
  - **`# golestan_code_mcp`, then one purpose paragraph.** A code context MCP server backed by Oracle AI Database
    26ai. It indexes codebases inside the database, chunked at function and class boundaries, and searches them by
    name and meaning. It follows their calls, keeps a wiki page per module, and remembers what earlier sessions
    learned. It serves all of it to AI coding tools (Claude Code, Codex, Cursor) over MCP.
  - **Origin.** The idea was initiated by [Coding Challenge #139 - Code Context](https://codingchallenges.substack.com/p/coding-challenge-139-code-context).
    It was developed with the help of [GitHub Spec Kit](https://github.github.com/spec-kit/), and the specs are in
    `specs/`.
  - **License.** Free to use under the [MIT License](LICENSE), also stated at the end.
  - **`## Features`.** About 7 one-line bullets: 13 languages, hybrid search, the code graph, the module wiki, agent
    memory, usage feedback, nothing sent out for indexing.
  - **`## Quick start`:**
    - the prerequisites, one line each;
    - copy `.env.example` to `.env`;
    - `docker compose up -d`, `uv sync`, `uv run golestan-check-db`;
    - `uv run ccctx repo add <path> --name <name>`, `uv run ccctx model load`, `uv run ccctx ingest <name>`,
      `uv run ccctx search "..."`;
    - `uv tool install --editable .` and `claude mcp add ccctx -- ccctx mcp`.

    Each step gets a link to its docs page.
  - **`## MCP tools`.** The nine tool names, one line each, with a link to `docs/mcp-server.md`.
  - **`## Documentation`.** A list linking the seven `docs/` pages (data-model Section 1) and `CLAUDE.md`.
  - **`## License`.** "MIT, see [LICENSE](LICENSE)."

  Drop the `## Layout` section, which now lives in CLAUDE.md (T003). Run
  `uv run pytest tests/test_docs.py -q -k "readme or license"`: these pass. The link test still fails on the `docs/`
  links until US2.

**Checkpoint**: The README and LICENSE satisfy FR-001–FR-005, and the suite apart from the link test is green.

---

## Phase 4: User Story 2 - Keep the detailed reference, out of the way (Priority: P2)

**Goal**: Every section the README dropped is in a `docs/` page, nearly word for word, and every link resolves.

**Independent Test**: `docscheck.py` reports `0 lines missing`, and `tests/test_docs.py` passes.

Each page's text is cut from `git show master:README.md`:
- **Headings.** Each moved `## Section` becomes the page's `# Title`, or stays `## Section` under a `# Title` when the
  page holds several sections.
- **Wording.** Everything else is kept as it is, apart from the cross-reference edits listed per task.
- **Size.** Each page stays under about 200 lines.

- [X] T009 [P] [US2] Create `docs/setup.md`: `# Setup`, holding master's `## Prerequisites`, `## Setup` and
  `## Checking that data persists` as `##` sections.
- [X] T010 [P] [US2] Create `docs/indexing.md`: `# Indexing`, holding master's `## Registering codebases` and
  `## Ingesting a codebase`. In "see [Searching code](#searching-code)", the link becomes
  `[Searching code](search.md#searching-code)`.
- [X] T011 [P] [US2] Create `docs/search.md`: `# Search`, holding master's `## Searching code`, `## Usage feedback` and
  `## Evaluating retrieval`. "(see Usage feedback)" becomes "(see [Usage feedback](#usage-feedback))".
- [X] T012 [P] [US2] Create `docs/graph.md` from master's `## Code relationships`, titled `# Code relationships`.
  "(see the table under Ingesting a codebase)" becomes
  "(see the table under [Ingesting a codebase](indexing.md#ingesting-a-codebase))".
- [X] T013 [P] [US2] Create `docs/wiki.md` from master's `## Module wiki`, titled `# Module wiki`. The `## Key symbols`
  and other `##` lines inside its fenced example stay unchanged, since they are inside a code block.
- [X] T014 [P] [US2] Create `docs/memory.md` from master's `## Agent memory`, titled `# Agent memory`. Any "see Usage
  feedback" becomes a link to `search.md#usage-feedback`.
- [X] T015 [P] [US2] Create `docs/mcp-server.md` from master's `## The MCP server`, titled `# The MCP server`, with the
  tools table and all `**Changed in …**` entries. Cross-references become links:
  - "(see Agent memory)" → `memory.md`;
  - "(see Usage feedback)" → `search.md#usage-feedback`.
- [X] T016 [US2] Fill in `docscheck.py`'s `EXPECTED` with each line T009–T015 deliberately reworded and the reason,
  if the link normalization doesn't already cover it. Then run
  `uv run python specs/014-docs-license-src-layout/docscheck.py`: `0 lines missing`. Run
  `uv run pytest tests/test_docs.py -q`: all pass. Fix any page or link the tests name.

**Checkpoint**: SC-003 and SC-004 hold. No information is lost, and no link is broken.

---

## Phase 5: User Story 3 - Guide an AI coding agent working in the repository (Priority: P2)

**Goal**: CLAUDE.md holds the commands, rules, Spec Kit workflow and the layout list.

**Independent Test**: CLAUDE.md has every section of research R6, and `tests/test_layout.py` and `tests/test_docs.py`
pass.

- [X] T017 [US3] Fill in `CLAUDE.md` above its `## Layout` section, using the content of research R6:
  - **`## What this is`.** Two lines, with a link to `README.md`.
  - **`## Commands`.** `uv sync`, `docker compose up -d`, `uv run golestan-check-db`, `uv run pytest`,
    `uv run pytest tests/<area>/test_<x>.py -q`, `uv run ccctx <command>`, `ccctx mcp`. Say that database tests skip
    when the container is down, and that the MCP clients must be closed before `uv sync` (the `ccctx.exe` lock).
  - **`## Rules`.** Take them from `specs/013-split-large-modules/contracts/conventions.md` and the constitution:
    - files of at most 300 lines, each opening with a docstring;
    - one concern per file;
    - functions are reached through their module, as `runs.record`, so that patches hit;
    - tests mirror `src/`;
    - shared setup goes in `tests/conftest.py` and `tests/support.py`;
    - behavior is test-first, and ranking or chunking changes need `ccctx eval`;
    - indexing never sends code out;
    - `.env` is never printed or committed;
    - no new dependency without need;
    - every new file goes in the Layout list.
  - **`## Spec Kit`.** Features follow `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`,
    with specs in `specs/NNN-name/`, under `.specify/memory/constitution.md`. Link to
    <https://github.github.com/spec-kit/>.

  Keep the whole file readable at a glance: everything above the Layout section is at most about 60 lines.
- [X] T018 [US3] Extend CLAUDE.md's Layout tree:
  - add `README.md`, `LICENSE`, `CLAUDE.md` and `docs/` with its seven pages, each with a one-line purpose, beside
    `compose.yaml`;
  - add `tests/test_docs.py`, with the purpose "every relative link in the README, CLAUDE.md and docs/ resolves";
  - update `tests/test_layout.py`'s purpose to "file size, docstrings, and CLAUDE.md's Layout list".

  Run `uv run pytest tests/test_layout.py tests/test_docs.py -q`: all pass.

**Checkpoint**: Spec FR-008 and FR-009 hold.

---

## Phase 6: User Story 4 - Find the code directly under src/ (Priority: P3)

**Goal**: The source sits directly in `src/`. It is still installed as `golestan_code_mcp`, and nothing a user runs
changes.

**Independent Test**: Quickstart steps 1–3 and the full suite.

- [X] T019 [US4] Add `test_every_package_folder_is_listed_in_pyproject` to `tests/test_layout.py`.
  - **What it reads.** It reads `pyproject.toml` with `tomllib` and collects `tool.setuptools.packages`.
  - **The mapping.** It maps each package to a folder: `golestan_code_mcp` is `src/`, and `golestan_code_mcp.a.b` is
    `src/a/b`.
  - **The check.** That set must equal the set of folders under `src/` that hold an `__init__.py`.

  Keep the file under 300 lines. Run it: it fails, since `tool.setuptools` doesn't exist yet.
- [X] T020 [US4] Ask the user to close the MCP clients that run `ccctx` and `golestan-code-mcp` (research R8), and wait
  for their confirmation before T023 needs a reinstall.
- [X] T021 [US4] Move the source:
  - `git mv` each tracked entry of `src/golestan_code_mcp/` into `src/`, folders included;
  - delete the leftover `src/golestan_code_mcp/` (only `__pycache__` remains);
  - check that `git status` shows only renames.
- [X] T022 [US4] In `src/config.py`, change `PROJECT_ROOT = Path(__file__).resolve().parents[2]` to `parents[1]`. Leave
  everything else in `src/` unchanged.
- [X] T023 [US4] Update `pyproject.toml` (data-model Section 4):
  - `[build-system]` becomes `requires = ["setuptools>=77"]`, `build-backend = "setuptools.build_meta"`;
  - delete `[tool.hatch.build.targets.wheel]`;
  - add `[tool.setuptools]` with `package-dir = {"golestan_code_mcp" = "src"}` and `packages` listing the 10 packages.

  Run `uv lock`.
- [X] T024 [US4] Reinstall, with the clients closed:
  - `uv sync`;
  - `uv tool install --editable . --reinstall`;
  - check that `.venv\Lib\site-packages` has a `__editable___golestan_code_mcp_*_finder.py` and no
    `_editable_impl_golestan_code_mcp.pth`.
- [X] T025 [US4] Update the paths in the documents:
  - CLAUDE.md's Layout: the `src/golestan_code_mcp/` level goes, its entries move up one level under `src/`, and `src/`
    is described as "the package `golestan_code_mcp`, installed from here";
  - the `tests/` line becomes "its folders mirror src/";
  - grep `README.md`, `CLAUDE.md` and `docs/` for `golestan_code_mcp/` and fix any path that's left.

  Add the one-time reinstall note to the README's quick start and to `docs/mcp-server.md`: close the clients, then
  `uv sync` and `uv tool install --editable . --reinstall`.
- [X] T026 [US4] Verify quickstart steps 2 and 3:
  - `Test-Path src\golestan_code_mcp` is False;
  - `git diff master -M --stat -- src` shows renames apart from `config.py`;
  - `import golestan_code_mcp.search.query` resolves to `src\search\query.py`;
  - `import config` fails;
  - `uv run golestan-check-db` finds `.env`;
  - `ccctx --help` and `ccctx repo list` work from another directory;
  - the MCP Inspector, or `tests/cli/test_entry.py`, lists the nine tools.
- [X] T027 [US4] Run `uv run pytest -q` in the foreground, in chunks of under 10 minutes by folder if needed.
  - **Expected.** Master's results, plus the new tests. The known `test_search_code_matches_core` failure, which
    depends on feedback state, may remain.
  - **If a run is killed for memory.** Report it rather than restarting it in the background.

**Checkpoint**: FR-010–FR-013 and SC-005 hold.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T028 Bump the version to 1.4.2:
  - in `pyproject.toml` and `src/__init__.py` (`__version__`);
  - run `uv lock`;
  - add `**Changed in 1.4.2.**` at the top of the changes in `docs/mcp-server.md`: "The source moved from
    `src/golestan_code_mcp/` to `src/` and the build backend is now setuptools; reinstall once. No tool, command or
    stored value changed."

  Then `uv sync` again.
- [X] T029 [P] Grep the whole repository, apart from `specs/`, `.venv`, `.git` and caches, for
  `src/golestan_code_mcp` and `hatch`. Only `uv.lock` history is acceptable. Check that `.gitignore` still covers
  `*.egg-info/` and `build/` (setuptools' outputs) and add them if missing.
- [X] T030 Run the whole quickstart from top to bottom, plus `docscheck.py`, `tests/test_layout.py`,
  `tests/test_docs.py` and the full suite.
  - **Results.** Record them in `specs/014-docs-license-src-layout/quickstart.md` under a final "Verified" note.
  - **Status.** Set the spec's `**Status**` to `Implemented`.

---

## Dependencies & Execution Order

- **Setup (T001–T002).** No dependencies; both can run in parallel.
- **Foundational (T003–T004).** It blocks US1's README rewrite (T008).
- **US1 (T005–T008).** It needs Phase 2. Its README links to `docs/`, so the link test turns green only after US2.
- **US2 (T009–T016).** It needs only T001 and T002, since it reads master's README, so it can run alongside US1. Its
  checkpoint (T016) needs T008.
- **US3 (T017–T018).** It needs Phase 2. It can run alongside US1 and US2.
- **US4 (T019–T027).** It needs US1–US3 done, so that the path updates (T025) see the final documents. T020 has to
  come before T024.
- **Polish (T028–T030).** It needs everything.

## Parallel Opportunities

- **Setup.** T001 and T002 together.
- **US1.** T005 and T006 together.
- **US2.** T009–T015 together: seven separate files cut from the same read-only source.
- **Across stories.** US2's pages and US3's CLAUDE.md sections can be written alongside the README rewrite.

## Implementation Strategy

1. **MVP.** Phases 1–3, giving a licensed project with a short front page. The docs links point at pages still to
   come, so finish US2 before merging anything.
2. **Then.** US2 and US3 make the documentation complete and checked.
3. **Last.** US4 is the only part that touches installs. Do it once the docs are settled, with the MCP clients closed.
