# Contract: What Must Not Change

The feature moves code, so its contract is a list of what users and tools outside the package can observe, all of
which stays identical (spec FR-001, FR-008). The baseline (research R10) and the existing tests check each item.

## Installed commands

| Command | Entry point string in `pyproject.toml` | After |
|---|---|---|
| `ccctx` | `golestan_code_mcp.cli:main` | unchanged string; resolves to `cli/__init__.py`'s `main` |
| `golestan-code-mcp` | `golestan_code_mcp.server:main` | unchanged string; resolves to `server/__init__.py`'s `main` |
| `golestan-check-db` | `golestan_code_mcp.db:main` | unchanged |
| `golestan-clone-samples` | `golestan_code_mcp.samples:main` | unchanged |

`python -m golestan_code_mcp.cli` and `python -m golestan_code_mcp.server` keep working, through the packages'
`__main__.py`. `python -m golestan_code_mcp.db` and `python -m golestan_code_mcp.samples` stay as they are.

There is no reinstall: an existing editable install, and an MCP client registered with `ccctx mcp`, keep working
without `uv sync`.

## MCP server

- **Tools.** The same nine tools, listed in the same order: `search_code`, `get_symbol`, `find_callers`,
  `find_callees`, `impact_of`, `read_wiki`, `list_repositories`, `recall`, `mark_used`. Each keeps the same
  description, input schema (unknown arguments still refused), output schema and annotations.
- **Server details.** The server name `golestan_code_mcp` and its instructions text stay the same.
- **Results.** Results and error messages for the same inputs on the same database state stay the same.
- **Logs.** The stderr log records keep their logger name (`golestan_code_mcp.server`), fields and order.

## `ccctx` command

- **Arguments.** The same subcommands, options, defaults, help text and argument errors.
- **Output.** The same stdout and stderr output for the same inputs and database state, timings and timestamps aside.
- **Exit codes.** The same exit codes.
- **Logs.** Structured records on stderr keep the logger names `golestan_code_mcp.ingest`, `.memory` and `.wiki`.

## Database

- **Schema.** The same schema version (10) and the same migrations. No migration is added.
- **Stored rows.** The same rows after `ingest --full` and `wiki build`, with the same extraction version and wiki
  compiler version.
- **Memory facts.** Their consolidator value still reads `memory/<version>`. It changes only with the version bump,
  which comes last (research R13).

## Parsing

- **Parse output.** The same chunks, calls, imports, file docs and namespaces for every file.
- **Language tables.** The same keys in the same order, for every language table.
- **Language list.** `search`'s language list, built from the tables, is the same tuple.

## Not a contract

These may change, since only this project uses them:
- the import paths of the project's own modules, such as `golestan_code_mcp.memory.runs` in place of
  `golestan_code_mcp.memory`;
- the location of test files and fixtures.
