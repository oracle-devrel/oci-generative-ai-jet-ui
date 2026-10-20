# golestan_code_mcp

A code context MCP server backed by Oracle AI Database 26ai. It indexes codebases into the database, cut at function
and class boundaries. It searches them by name and by meaning, follows their calls, keeps a wiki page about each
module, and remembers what earlier sessions learned. It serves all of it to AI coding tools such as Claude Code, Codex
and Cursor over the Model Context Protocol (MCP), so an agent can find and understand code without reading whole files.

The source code is on GitHub at [mhgolestan/code-context-mcp](https://github.com/mhgolestan/code-context-mcp).

The idea was initiated by the article [Coding Challenge #139 - Code Context](https://codingchallenges.substack.com/p/coding-challenge-139-code-context)
from Coding Challenges. The project was developed with the help of [GitHub Spec Kit](https://github.github.com/spec-kit/):
every feature went through a specification, a plan and a task list, kept in [`specs/`](specs/).

It is free to use, change and share under the [MIT License](LICENSE).

## Features

- **Structure-aware indexing** of 13 languages (Python, Go, JavaScript, TypeScript, C#, C, C++, Java, Kotlin, Rust,
  PHP, Ruby, Swift): one chunk per definition, with its exact lines and documentation. Re-ingesting only reads what
  changed.
- **Hybrid search**: keyword and semantic matching fused in one database index, with each result's scores shown.
- **Code graph**: callers, callees and the transitive impact of a change, as a SQL property graph.
- **Module wiki**: one page per module, written from the index, with citations that follow the code and pages that
  are rewritten when it changes.
- **Agent memory**: every tool call is recorded and distilled into facts a new session can recall.
- **Usage feedback**: results that clients used rank a little higher, with a bounded, decaying boost.
- **Private by default**: embeddings are computed inside the database, so no source code is sent out to be indexed
  and no API key is needed.

## Quick start

You need Docker (tested with Rancher Desktop) with about 12 GB free, [uv](https://docs.astral.sh/uv/) and git.
The commands are run from the project root; [Setup](docs/setup.md) has the details and the PowerShell variants.

**1. Configure and start the database.** Copy `.env.example` to `.env` and replace both passwords. Then:

```sh
docker compose up -d
uv sync
uv run golestan-check-db       # waits for the first start, then checks the connection
```

**2. Index a repository.** [Indexing](docs/indexing.md) explains what is read and how re-ingesting works.

```sh
uv run golestan-clone-samples                         # optional: flask and gin, into ../ccctx-repos
uv run ccctx repo add ../ccctx-repos/flask --name flask
uv run ccctx model load                               # once: the embedding model and the search index
uv run ccctx ingest flask
```

**3. Search it.** See [Search](docs/search.md) and [Code relationships](docs/graph.md).

```sh
uv run ccctx search "how are incoming requests routed to handlers"
uv run ccctx callers url_for
uv run ccctx wiki build --repo flask
```

**4. Connect an AI coding tool.** Install the command once, then register it. For Claude Code:

```sh
uv tool install --editable .
claude mcp add ccctx -- ccctx mcp
```

Any MCP client can start `ccctx mcp` the same way. [The MCP server](docs/mcp-server.md) has the details.

**Upgrading from 1.4.1 or earlier.** The source moved from `src/golestan_code_mcp/` to `src/`, so an existing install must be refreshed once: close the MCP clients that run `ccctx` (on Windows they keep `ccctx.exe` locked), then run `uv sync` and `uv tool install --editable . --reinstall`. Registrations stay as they are.

**5. Run the tests.** Database tests are skipped, with a reason, when the database is down.

```sh
uv run pytest
```

## MCP tools

| Tool | Answers |
|---|---|
| `search_code` | Find code, wiki pages and remembered facts by name or by meaning |
| `get_symbol` | The full source of a definition |
| `find_callers` | What calls a function or method |
| `find_callees` | What a function or method calls |
| `impact_of` | What could break if a definition changes |
| `read_wiki` | What a module does, from its wiki page |
| `list_repositories` | The indexed repositories |
| `recall` | What earlier sessions worked out |
| `mark_used` | Record that a result helped |

Parameters, results and the change history are in [The MCP server](docs/mcp-server.md).

## Documentation

- [Setup](docs/setup.md): prerequisites, the database, installing, checking that data persists
- [Indexing](docs/indexing.md): registering and ingesting codebases, the languages and their limits
- [Search](docs/search.md): search modes and ranking, usage feedback, evaluating retrieval
- [Code relationships](docs/graph.md): callers, calls and impact
- [Module wiki](docs/wiki.md): the module pages, their citations and how they stay current
- [Agent memory](docs/memory.md): runs, facts, recall and the optional distilling model
- [The MCP server](docs/mcp-server.md): the tools, registering clients, the change history
- [CLAUDE.md](CLAUDE.md): commands, conventions and the file layout, for AI coding agents and contributors

## License

MIT, see [LICENSE](LICENSE).
