# Memory UI

A read-only, browser-facing view of the second brain: an Obsidian-style **graph** (wiki
topics + the content they cite, with semantic edges you can grow on demand), plus **search**,
a **wiki reader**, a **recent feed**, and a **health** panel.

It is served from the same Fly app as the MCP server — there is no separate build step and no
Node toolchain. `oracle/agent/webui.py` serves this directory's static files and a small
read-only JSON API (`/api/*`); every content query it makes is limited to `visibility='content'`,
exactly like the MCP tools.

## Enabling it

Off by default. Set on the deployment:

| Env | Meaning |
|-----|---------|
| `UI_ENABLED=1` | turn the UI on (unset → every `/` `/assets` `/api` path 404s) |
| `UI_AUTH_TOKEN` | ≥32-char bearer; the browser prompts for it once and stores it locally |
| `UI_PUBLIC_READ=1` | **explicit** anonymous read (public showcase only) — use instead of a token |
| `UI_TITLE` | display name in the header (default "Second Brain") |

`UI_ENABLED=1` with neither `UI_AUTH_TOKEN` nor `UI_PUBLIC_READ` refuses to start.

```
fly secrets set UI_ENABLED=1 UI_AUTH_TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')" -a <app>
```

## Layout

- `index.html` — the shell (nav + view containers + token overlay)
- `assets/app.js` — token gate, API client, router, search/wiki/feed/status views
- `assets/graph.js` — the force-directed graph (nodes, edges, lazy semantic expansion)
- `assets/style.css` — dark theme (brand-neutral; no personal defaults)
- `assets/vendor/force-graph.min.js` — [force-graph](https://github.com/vasturiano/force-graph)
  v1.49.5 by Vasco Asturiano, MIT license. Vendored (not a CDN) so the UI works offline.
