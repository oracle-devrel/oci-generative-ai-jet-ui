# Contract: `list_repositories` MCP tool

Server: `golestan_code_mcp`, next to `health`. After this change the server lists exactly two tools, `health` and `list_repositories`.

**Description**: "List the registered repositories with their paths and how many files and symbols each holds."

**Input schema**: no properties.

**Result** (`structuredContent`):

```json
{
  "database": "reachable",
  "reason": null,
  "repositories": [
    {"name": "flask", "path": "/home/you/ccctx-repos/flask", "files": 0, "symbols": 0},
    {"name": "gin",   "path": "/home/you/ccctx-repos/gin",   "files": 0, "symbols": 0}
  ]
}
```

| Field | Type | Rule |
|---|---|---|
| `database` | `"reachable"` \| `"unreachable"` | `unreachable` when settings are missing or the database cannot be reached or is still starting |
| `reason` | string \| null | null when reachable, else one line naming the cause, never a secret |
| `repositories` | list | sorted by `name`; empty when nothing is registered or the database is unreachable |
| `name`, `path` | string | as stored by `ccctx repo add` |
| `files`, `symbols` | integer ≥ 0 | same counts as `ccctx repo list` |

- `isError` is always false. A down database is a result, not an error.
- The tool applies missing migrations before reading, as the CLI does.
- The repositories match `ccctx repo list` field for field (SC-007), because both call `registry.list_repos`.
