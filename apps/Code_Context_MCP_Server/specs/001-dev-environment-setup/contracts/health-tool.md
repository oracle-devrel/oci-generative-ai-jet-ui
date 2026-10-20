# Contract: `health` MCP tool

Server: `golestan_code_mcp` (MCP server name, as reported in the initialize handshake)
Transport: stdio
Launch: `uv run golestan-code-mcp`
Inspector: `uv run mcp dev src/golestan_code_mcp/server.py`

## Tool listing

| Field | Value |
|---|---|
| `name` | `health` |
| `description` | non-empty; states that it reports server name, version and database reachability |
| `inputSchema` | `{"type": "object", "properties": {}}` (no arguments) |

## Result

Returned as structured content (and mirrored as JSON text content). `isError` is always `false`, including when the database is down (FR-009).

```json
{
  "server": "golestan_code_mcp",
  "version": "0.1.0",
  "database": "reachable",
  "reason": null
}
```

| Field | Type | Rule |
|---|---|---|
| `server` | string | always `golestan_code_mcp` |
| `version` | string | equals `golestan_code_mcp.__version__` |
| `database` | string enum | `reachable` or `unreachable` |
| `reason` | string or null | `null` when `reachable`; a short one-line cause when `unreachable` (e.g. `connection refused on localhost:1521`, `missing setting DB_PASSWORD`). Never contains a password. |

## Behavior

- A database probe is one connect with `tcp_connect_timeout` 3 s; the call returns within 5 s when the database is down.
- Missing or blank configuration yields `database: "unreachable"` with the missing setting named in `reason`, not a tool error.

## Test hooks (`tests/test_server.py`)

- `list_tools()` contains exactly one tool named `health` with the schema above.
- With the DB up: `database == "reachable"`, `reason is None`.
- With `DB_PORT` pointing at a closed port: `database == "unreachable"`, `reason` non-empty, `isError` false, call completes in under 5 s.
