# The MCP server

`ccctx mcp` runs the server over standard input and output. There is no network port and no login: the client starts it as a child process. It finds its database settings the same way the CLI does, from the environment and then `.env` in this checkout, whatever directory the client starts it in.

**Install the command once**, from the project root, so a client can start `ccctx` from any directory:

```sh
uv tool install --editable .
```

The editable install keeps `.env` in reach. With a non-editable install there is no `.env` next to the package, so give the settings to the client instead: `claude mcp add ccctx -e DB_USER=... -e DB_PASSWORD=... -- ccctx mcp`.

**Upgrading from 1.4.1 or earlier.** The source moved from `src/golestan_code_mcp/` to `src/`, so an existing install must be refreshed once: close the MCP clients that run `ccctx` (on Windows they keep `ccctx.exe` locked), then run `uv sync` and `uv tool install --editable . --reinstall`. Registrations stay as they are.

**Tools.** Each tool's description says what it answers and when to use one of the others instead. All but `mark_used` are read-only.

| Tool | Parameters | Returns |
|---|---|---|
| `search_code` | `query`, `repo`, `language`, `limit` (default 10, 1 to 50), `feedback` (default true) | Hits with repository, path, symbol name, kind, language, line range, a snippet (the first 10 lines, at most 800 characters) and the scores: `score`, `relevance` (the score before feedback), `feedback` (the boost, 0 to 0.2), and the keyword and semantic ranks. `feedback: false` ranks without usage feedback. The same hits as `ccctx search`, wiki pages included: a page hit has kind `page`, a `state`, its directory as `path` and a null line range. A fact hit has kind `fact`, its subject as the name, the subject's location, and the fact's text as the snippet. |
| `get_symbol` | `name`, `repo` | Up to 5 definitions with that name, each with its full indexed source, path and line range. A source over 400 lines is cut and marked `cut`. `total` and `truncated` say whether more matched. |
| `find_callers` | `name`, `repo` | The rows of `ccctx callers`. |
| `find_callees` | `name`, `repo` | The rows of `ccctx calls`. |
| `impact_of` | `name`, `depth` (default 3, 1 to 5), `repo` | The rows of `ccctx impact`, with hop counts. |
| `read_wiki` | `page`, `repo` | With `page`: the page's text, state, compile time and compiler, and its citations, each with repository, path and line range, the same as `ccctx wiki show`. Without `page`: the pages with their state and first purpose sentence, at most 200. |
| `list_repositories` | none | The registered repositories, the same as `ccctx repo list`. |
| `recall` | `repo`, `topic`, `limit` (default 20, 1 to 50) | What earlier sessions worked out: the facts, fresh and most confident first or most related to `topic`, each with its text, confidence, state, run IDs and the location of its code, and the 10 newest runs. Never calls a model. |
| `mark_used` | `repo`, `path`, `name` (all required) | Records that a hit helped (a cited use, see [Usage feedback](search.md#usage-feedback)). Returns the result's `kind` and `linked`: whether a search in this session returned it. An unknown result is `unavailable` with `not found`. Idempotent. |

- **Names** work as in the graph commands: a bare `url_for` matches every `url_for`, and `Flask.url_for` only that method.
- **Limits:** the graph tools return at most 200 rows, with `truncated` set when there were more.
- **Refusals:** bad input, an unknown repository or language, a missing model and a stopped database all come back as `"status": "unavailable"` with a reason. A call with an argument the tool does not take is refused.
- **Logging:** each call writes one line to standard error with the tool, time, status and result count.
- **Memory:** each call is also recorded as a run (see [Agent memory](memory.md)). The server's instructions tell clients to call
  `recall` first.

**Changed in 1.4.2.** The source moved from `src/golestan_code_mcp/` to `src/`, and the build backend is now setuptools; reinstall once (see above). The project is MIT-licensed. No tool, command or stored value changed.

**Changed in 1.4.1.** The code is reorganized into smaller files; no tool, command or stored value changed.

**Changed in 1.4.0.** Ten more languages are understood: TypeScript, TSX, C#, C, C++, Java, Kotlin, Rust, PHP, Ruby and Swift. Their definitions are hits, `get_symbol`, `find_callers`, `find_callees` and `impact_of` find them, and `read_wiki` has pages for their folders. `search_code`'s `language` accepts the new values. No tool's shape changed.

**Changed in 1.3.0.** `mark_used` is new. `search_code` hits have `relevance` and `feedback`, `score` includes the
feedback boost, and `search_code` takes `feedback`. `get_symbol` and `read_wiki` record opened uses; their answers
are unchanged. Nothing was removed or renamed.

**Changed in 1.2.0.** `recall` is new, `search_code` can return `fact` hits, and the server sends instructions.
Nothing was removed or renamed.

**Changed in 1.1.0.** `read_wiki` is new, and `search_code` can return page hits: `start_line` and `end_line` may be null, and every hit has a `state` (null for a symbol). Nothing was removed or renamed.

**Changed in 1.0.0.**
- **Renamed tools:** `search` is now `search_code`, `callers` is now `find_callers`, `calls` is now `find_callees`, and `impact` is now `impact_of`.
- **Removed:** `health`. A failed call says when the database is unreachable.
- **Parameters:** the `repos` list became one `repo`, and `search` lost `question` (now `query`) and `mode` (always hybrid).
- **Old registrations:** `golestan-code-mcp` still starts the same server.

**MCP Inspector**: lists the tools and calls them by hand.

```sh
npx @modelcontextprotocol/inspector ccctx mcp
```

Open the URL it prints, connect, then **Tools → List Tools**. To compare with the CLI, call `search_code` with `{"query": "how are requests routed", "repo": "flask"}`: it returns the same 10 symbols in the same order as `ccctx search "how are requests routed" --repo flask`.

**Claude Code**:

```sh
claude mcp add ccctx -- ccctx mcp
```

Start a session in any other directory and ask, for example, "using ccctx, how does Flask decide which view function handles a request?".

**Which tool a client picks.** Five questions were run through Claude Code with `claude -p`, its built-in tools turned off and only this server connected. Each question was written so one tool is the right first step. The client called that tool first every time:

| Question | First call | Then |
|---|---|---|
| using ccctx, how does Flask decide which view function handles a request? | `search_code` | `get_symbol` ×6, a narrower `search_code`, `find_callers` |
| show me the full source of Flask.dispatch_request | `get_symbol` | none |
| what calls url_for in flask? | `find_callers` | none |
| if I change Flask.url_for, what could break? | `impact_of` | `get_symbol`, `find_callers`, `search_code` |
| what does Flask.full_dispatch_request call? | `find_callees` | `get_symbol` |

Its routing answer traced registration through `App.add_url_rule` into `url_map` and `view_functions`. It then traced each request through `Flask.wsgi_app`, `AppContext.match_request` and `Flask.dispatch_request`, citing paths and lines. It never asked to open a file.
