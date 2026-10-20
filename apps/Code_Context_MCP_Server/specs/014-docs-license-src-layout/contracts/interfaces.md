# Contract: What Must Not Change

This feature moves files and rewrites documentation. Everything a user or client touches stays as it is.

## Program interfaces (unchanged)

| Interface | Contract |
|---|---|
| Import name | Every module is still `golestan_code_mcp.<dotted path>`: `golestan_code_mcp.cli`, `golestan_code_mcp.search.query`, and so on. Nothing new becomes importable at the top level: `import config`, `import cli` and the like fail. |
| Installed commands | `ccctx`, `golestan-check-db`, `golestan-clone-samples` and `golestan-code-mcp`, with the same `[project.scripts]` targets |
| `python -m` | `python -m golestan_code_mcp.cli` and `python -m golestan_code_mcp.server` |
| MCP registrations | `claude mcp add ccctx -- ccctx mcp` and any existing `golestan-code-mcp` registration work without being re-added. A one-time reinstall is allowed (research R8). |
| MCP tools | The nine tools, with the same names, schemas, results and listing order: 013's [interfaces contract](../../013-split-large-modules/contracts/interfaces.md) still holds |
| CLI | The same subcommands, options, output and exit codes |
| `.env` lookup | The settings come from the environment first, then from `.env` at the checkout root, whatever the current directory |
| Logger names | `golestan_code_mcp.ingest`, `.memory`, `.server`, `.wiki` and the rest |
| Database | The same schema version, migrations and stored values. Nothing is re-indexed. |

## Documentation interfaces (new)

| Rule | Checked by |
|---|---|
| Every relative link in `README.md`, `CLAUDE.md` and `docs/*.md` names an existing file, and its `#fragment`, if any, names a heading of that file, using GitHub's slug rules | `tests/test_docs.py` |
| CLAUDE.md's `## Layout` tree lists exactly the `.py` files under `src/` and `tests/` (fixtures excepted), each with a purpose | `tests/test_layout.py` |
| Every `src/` folder with `__init__.py` is a package listed in `pyproject.toml`, and every package listed there has its folder | `tests/test_layout.py` |
| Every line of master's README, apart from its Layout section, reappears in the README, `docs/` or CLAUDE.md, or is named in `EXPECTED` | `specs/014-docs-license-src-layout/docscheck.py` (one-off) |
| The README names the article, Spec Kit and the license, and is at most 150 lines | `tests/test_docs.py` |
