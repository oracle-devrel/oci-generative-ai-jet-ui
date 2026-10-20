# Data Model: Docs, License and Source Layout

There is no stored data. The "entities" are files, and this is where each one comes from.

## 1. Documents

| File | Status | Holds | Size |
|---|---|---|---|
| `README.md` | rewritten | purpose, origin (article), built with Spec Kit, features, quick start, tool list, doc links, license (research R3) | ≤ 150 lines |
| `LICENSE` | new | MIT License text, `Copyright (c) 2026 Mohammad Hossein Golestan` (R2) | 21 lines |
| `CLAUDE.md` | new | what this is, commands, rules, Spec Kit workflow, `## Layout` tree (R6) | ~200 lines, mostly the tree |
| `docs/setup.md` | new, moved | README: Prerequisites, Setup, Checking that data persists | ~70 |
| `docs/indexing.md` | new, moved | README: Registering codebases, Ingesting a codebase | ~120 |
| `docs/search.md` | new, moved | README: Searching code, Usage feedback, Evaluating retrieval | ~135 |
| `docs/graph.md` | new, moved | README: Code relationships | ~50 |
| `docs/wiki.md` | new, moved | README: Module wiki | ~95 |
| `docs/memory.md` | new, moved | README: Agent memory | ~70 |
| `docs/mcp-server.md` | new, moved | README: The MCP server, its "Changed in" entries, the reinstall note (R8) | ~85 |

### Rules for the moved text
- **Wording.** Every non-blank line is kept, apart from heading levels and the cross-reference edits below.
  `docscheck.py` checks this (R5).
- **Cross-references.** Each one becomes a relative link to the page that now holds the target:

  | README text today | Becomes |
  |---|---|
  | "see [Searching code](#searching-code)" (in Ingesting) | `[Searching code](search.md#searching-code)` |
  | "(see Usage feedback)" (in Searching) | `(see [Usage feedback](search.md#usage-feedback))` |
  | "(see the table under Ingesting a codebase)" (in Code relationships) | link to `indexing.md#ingesting-a-codebase` |
  | "(see Agent memory)", "(see Usage feedback)" (in The MCP server) | links to `memory.md`, `search.md#usage-feedback` |

  Each changed line is listed in `docscheck.py`'s `EXPECTED`.
- **Paths.** Commands keep running from the project root. Paths inside the text, such as `db/startup/...`,
  `gold.json` and `tests/search/test_evaluation.py`, stay as written, since they name files, not links.

## 2. CLAUDE.md layout tree

This is the same format the README's `## Layout` uses today, which `test_layout.py` parses:
- a name ending in `/` is a folder;
- a deeper-indented line is inside the folder above it;
- the text after the name is the purpose.

The changes from today's tree:
- **Source files.** The `src/golestan_code_mcp/` level goes, so the entries under it move one level up, under `src/`.
- **Package line.** `src/` is described as "the package `golestan_code_mcp` (installed from here, see pyproject)".
- **New entries.** `tests/test_docs.py`, with the purpose "every relative link in the README, CLAUDE.md and docs/
  resolves".
- **Root files.** `LICENSE`, `CLAUDE.md`, `README.md` and `docs/` with its seven pages are added beside
  `compose.yaml`. The check reads only the `.py` entries, so these are for the reader.

## 3. Source moves

| From | To |
|---|---|
| `src/golestan_code_mcp/<path>` (all 69 tracked files) | `src/<path>`, unchanged |
| `src/golestan_code_mcp/config.py` | `src/config.py`, with `parents[2]` → `parents[1]` |
| `src/golestan_code_mcp/__init__.py` | `src/__init__.py`, with `__version__ = "1.4.2"` |

The import name `golestan_code_mcp.<path as dotted name>` is unchanged for every module.

## 4. `pyproject.toml`

| Key | Today | After |
|---|---|---|
| `project.version` | `1.4.1` | `1.4.2` |
| `project.license` | absent | `"MIT"` |
| `project.license-files` | absent | `["LICENSE"]` |
| `build-system` | hatchling | `requires = ["setuptools>=77"]`, `build-backend = "setuptools.build_meta"` |
| `tool.hatch.build.targets.wheel.packages` | `["src/golestan_code_mcp"]` | removed |
| `tool.setuptools.package-dir` | absent | `{"golestan_code_mcp" = "src"}` |
| `tool.setuptools.packages` | absent | the 10 packages: `golestan_code_mcp` and its `.cli`, `.graph`, `.indexing`, `.memory`, `.parsing`, `.parsing.languages`, `.search`, `.server`, `.wiki` |
| `project.scripts` | 4 entry points | unchanged |
| `tool.pytest.ini_options` | as is | unchanged |
