# Implementation Plan: Docs, License and Source Layout

**Branch**: `014-docs-license-src-layout` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/014-docs-license-src-layout/spec.md`

## Summary

The project gets:
- **A short README.** About 120 lines: purpose, the Coding Challenge #139 article it came from, built with GitHub Spec
  Kit, features, quick start, tools, doc links and the license.
- **An MIT `LICENSE`.**
- **A `docs/` folder.** Seven topic pages holding the README's current reference text almost word for word.
- **A `CLAUDE.md`.** The commands, the rules, the Spec Kit workflow, and the file layout the layout test now reads.

The source moves from `src/golestan_code_mcp/` to `src/` by `git mv`. It still installs as `golestan_code_mcp`.
Hatchling refuses an editable install of that mapping, so the build backend becomes setuptools, with `package-dir`
(research R1). The only code change is one line in `config.py`, so `.env` is still found.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**:
- **Runtime.** No change.
- **Build backend.** Hatchling becomes `setuptools>=77`, for PEP 639 license fields (R1, R2). It's needed only at
  build time.

**Storage**: Oracle AI Database 26ai, unchanged. No migration, no re-index.

**Testing**: pytest. It gains a new `tests/test_docs.py`, a package-list test in `tests/test_layout.py`, and a one-off
`docscheck.py` (R5).

**Target Platform**: Windows and Linux developer machines. The editable installs (`uv sync`, `uv tool install
--editable .`) must keep working.

**Project Type**: a single Python package, with a CLI and an MCP server over stdio.

**Performance Goals**: none. Nothing that runs changes.

**Constraints**:
- **Behavior frozen.** Nothing a user runs or receives changes (FR-012).
- **Import name.** It stays `golestan_code_mcp`, and nothing new becomes importable at the top level.
- **No re-registration.** MCP clients aren't registered again; a one-time reinstall is allowed (R8).

**Scale/Scope**:
- **Source.** 69 source files are renamed and 2 are edited.
- **Documents.** One README is split into a short README and seven pages. `LICENSE` and `CLAUDE.md` are new.
- **Tests.** 2 test files change, and 1 is new.

## Constitution Check

*GATE: checked before Phase 0 research, and again after Phase 1 design.*

| Principle | Effect | Status |
|---|---|---|
| I. Database-Native Intelligence | Nothing new is sent anywhere. The docs keep the statement of what memory distillation may send. | Pass |
| II. Structure-Aware Ingestion | Indexing code is renamed, not changed. | Pass |
| III. MCP as the Single Interface | Same tools and schemas, and the same registrations (contracts/interfaces.md). The tool reference moves to `docs/mcp-server.md` unchanged. | Pass |
| IV. Hybrid, Explainable Retrieval | Ranking code isn't changed. The documented defaults move to `docs/search.md` unchanged. | Pass |
| V. Self-Improvement with Provenance | Unchanged. | Pass |
| VI. Measured Quality (Test-First) | The link test and the package-list test are written first: on master, the link test fails (no `docs/` pages, no CLAUDE.md), and the layout test fails once it reads CLAUDE.md. The full suite is the regression net. | Pass |
| VII. Safety & Simplicity | No new runtime dependency or layer. A build backend is swapped, not added, and only because hatchling can't install the required layout in editable mode (R1). `.env` is still never printed; CLAUDE.md says so. | Pass |
| Workflow & Quality Gates | CLAUDE.md restates the Spec Kit flow and points to the constitution. No tool contract changes, so no contract-test changes. `ccctx eval` isn't needed: ranking, chunking and embedding are unchanged. | Pass |

**Re-check after Phase 1**: Pass. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/014-docs-license-src-layout/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R9: backend, license, README, docs pages, checks, CLAUDE.md, move, reinstall
├── data-model.md        # where each document and file comes from
├── quickstart.md        # how to validate
├── contracts/interfaces.md
├── checklists/requirements.md
├── docscheck.py         # created by /speckit-implement (R5)
└── tasks.md             # created by /speckit-tasks
```

### Repository after the feature

```text
README.md  LICENSE  CLAUDE.md  pyproject.toml  compose.yaml  gold.json
docs/        setup.md  indexing.md  search.md  graph.md  wiki.md  memory.md  mcp-server.md
src/         __init__.py  config.py  db.py  registry.py  samples.py  schema.py      # the package golestan_code_mcp
             parsing/ (languages/)  indexing/  search/  graph/  wiki/  memory/  server/  cli/
tests/       unchanged, plus test_docs.py
```

**Structure Decision**: One package, whose source root is `src/` itself, mapped to `golestan_code_mcp` by setuptools'
`package-dir` (R1). [data-model.md](data-model.md) gives every document's contents and the `pyproject.toml` changes.

### Order of work

1. **Checks first.**
   - `tests/test_docs.py`, failing.
   - `test_layout.py` reading CLAUDE.md, plus the package-list test.
   - `docscheck.py`.
2. **License and docs.**
   - `LICENSE`.
   - The seven `docs/` pages, cut from the README with cross-references turned into links.
   - The new README.
   - CLAUDE.md with the layout tree. At this point it still lists `src/golestan_code_mcp/`.
   - Run `docscheck.py` and the doc tests.
3. **The move.**
   - `git mv` into `src/`.
   - `config.py` gets `parents[1]`.
   - `pyproject.toml` switches to setuptools, with the license fields.
   - CLAUDE.md's tree is updated.
   - `uv lock`.
   - Reinstall (R8). Run the suite, the commands and the MCP listing.
4. **Version and wrap-up.**
   - Version 1.4.2 in `pyproject.toml` and `src/__init__.py`, with a "Changed in 1.4.2" entry in
     `docs/mcp-server.md`.
   - The full suite, then the quickstart from the top.

## Complexity Tracking

Empty: no Constitution Check violation needs justifying.
