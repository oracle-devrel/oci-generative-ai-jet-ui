# Contract: CLI changes (`ccctx mcp`, `ccctx search --language --limit`)

Extends `specs/007-code-graph/contracts/cli.md`. Every other command is unchanged.

## `ccctx mcp`

```text
ccctx mcp
```

- Takes no arguments. Runs `server.main()`: the MCP server over stdio (see `tools.md`) until the client closes standard input.
- Dispatched before `main()` connects to the database or runs migrations, so it starts with the database down. Each tool connects per call and reports an outage as a result.
- Writes nothing to standard output except protocol messages. Logs go to standard error.
- Finds its settings from any working directory: process environment first, then `.env` at `config.PROJECT_ROOT` (the checkout, for an editable install).
- `golestan-code-mcp` stays as an alias of the same entry point, so a client registered in an earlier step keeps working.

Registration and inspection (documented in the README, FR-016):

```sh
uv tool install --editable .
claude mcp add ccctx -- ccctx mcp
npx @modelcontextprotocol/inspector ccctx mcp
```

For a non-editable install, settings go in the client's environment: `claude mcp add ccctx -e DB_USER=... -e DB_PASSWORD=... -- ccctx mcp`.

## `ccctx search`

```text
ccctx search QUESTION [--repo NAME]... [--mode vector|text|hybrid] [--language LANG] [--limit N]
```

| Option | Default | Meaning |
|---|---|---|
| `--language LANG` | all | Keep only hits from files of this language. One of the values listed in `tools.md` (`batch` ... `yaml`). |
| `--limit N` | `10` | Return at most `N` hits, 1 to 50. |

- Both are passed to `semantic.search(conn, question, repos, mode, env, language=..., limit=...)`, the call `search_code` makes, so `ccctx search "<q>" --repo flask --language L --limit N` and `search_code` with the same `query`, `repo`, `language` and `limit` return the same symbols in the same order (FR-006, SC-002).
- Output columns are unchanged: `RANK SCORE KEYWORD SEMANTIC REPO KIND NAME PATH LINES`.
- Checked before connecting, after the empty-question and mode checks. A bad value exits `1` (not argparse's `2`):

| Cause | stderr |
|---|---|
| `--limit` not an integer, or outside 1 to 50 | `error: limit must be between 1 and 50` |
| Unknown `--language` | `error: unknown language '<language>'; valid languages: batch, css, go, html, ini, javascript, json, markdown, proto, python, rst, shell, sql, text, toml, yaml` |

## Version

`pyproject.toml` `version` and `golestan_code_mcp.__version__` are `1.0.0`.
