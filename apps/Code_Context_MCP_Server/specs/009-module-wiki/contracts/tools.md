# Contract: MCP tools (server 1.1.0)

Extends `specs/008-mcp-tools/contracts/tools.md`. Every rule there (refusals are results, input validation, database down, bounded, located, logging, read-only annotation, `Annotated[..., Field(description=...)]` parameters) applies unchanged. `get_symbol`, `find_callers`, `find_callees`, `impact_of` and `list_repositories` are unchanged.

The server lists exactly seven tools. The contract only gains things (a tool, a hit kind, a nullable widening, a field), so the version is `1.1.0` (MINOR, constitution III).

| Tool | Core call | CLI twin | Change |
|---|---|---|---|
| `search_code` | `semantic.search` (hybrid) | `ccctx search` | page hits, `state` field, line range nullable, description |
| `read_wiki` | `wiki.read` / `wiki.pages` | `ccctx wiki show`, `ccctx wiki list` | new |

## `search_code`

### Description

**`search_code`**: Find code by what it does or by name: "how are requests routed?", "where are sessions saved?", "url_for". Use this first when you do not yet know which symbol to look at. If you already know the name, use get_symbol to read it, find_callers for its call sites, or impact_of for what a change would affect. Returns up to limit hits (default 10), best first. Each hit has the repository, path, symbol name, kind, language, line range, a snippet of the symbol's opening lines, and the scores behind its rank: the fused score, the keyword rank and the semantic rank (null when that side did not find it). Keyword and semantic search are fused, and the definitions of an exact identifier come first. A hit of kind page is a wiki page about a whole module: its name is the page name, its path is the module's directory, its line range is null and its state says whether it is fresh or stale; read it with read_wiki. Next step: call get_symbol with a hit's name to read its full source, or read_wiki with a page hit's name.

Parameters are unchanged.

### Hits

Same hits, same order and same scores as `ccctx search "<query>" --repo <repo> --language <language> --limit <limit>`. Symbol hits are unchanged except for the new `state` field, which is `null` for them.

```json
{"rank": 1, "score": 41.7, "keyword_rank": 1, "semantic_rank": 1, "similarity": 0.6312,
 "repo": "flask", "kind": "page", "name": "flask/json", "language": "python",
 "path": "src/flask/json", "start_line": null, "end_line": null, "state": "fresh",
 "snippet": "# flask/json\n\n`flask/json` is a Python package of 3 files and 62 definitions: ..."}
```

| Field | Type | Page hit |
|---|---|---|
| `kind` | `string` | `page` |
| `name` | `string` | The page name |
| `path` | `string` | The page's directory |
| `language` | `string` | The most common language of the page's symbols |
| `start_line`, `end_line` | `int \| null` | `null`: a page has no lines in the code. Symbol hits keep their integers. |
| `state` | `"fresh" \| "stale" \| null` | The page's state. `null` for symbol hits. |
| `snippet` | `string` | The page text's first 10 lines, at most 800 characters, no trailing newline |
| `score`, `keyword_rank`, `semantic_rank` | as before | The page's values within the page index |
| `similarity` | `float \| null` | Cosine similarity from the same model as symbols; it decides the page's place (research R8) |

`repo` and `language` filters apply to pages with the same rules as symbols. When the page index does not exist, only symbol hits are returned, still `ok`. Failures are unchanged.

## `read_wiki`

Core: `wiki.read(conn, page, repo)` with a name, `wiki.pages(conn, repo)` without one. No model needed. Same page and citations as `ccctx wiki show <page> --repo <repo>`; same list as `ccctx wiki list --repo <repo>`.

### Description

**`read_wiki`**: What does this module do? Reads the tool's wiki page about a module (a directory of indexed code): its purpose, its key symbols with one line each, the modules it depends on and the modules that use it. Use it when a question is about a module as a whole rather than one function, or after search_code returns a hit of kind page. Pass page to read one page; it returns the text, whether it is fresh or stale (and what made it stale), when and by what it was compiled, and its citations, each with the repository, path and line range of the symbol or file it names. Omit page to list the pages, optionally for one repo, with each page's name, state and first purpose line. A stale page describes code that has changed since; check its citations. Next step: get_symbol on a key symbol to read its source.

### Parameters

| Parameter | Type, default | Description |
|---|---|---|
| `page` | `string \| null`, `null` | The page name, for example flask/json, as returned by search_code or by listing. Case-sensitive. Default: list the pages instead. |
| `repo` | `string \| null`, `null` | Look only in this registered repository, for example flask. list_repositories gives the valid names. Needed when two repositories have a page of the same name. Default: all repositories. |

Parameter order in the schema: `read_wiki(page, repo)`.

### Result: `WikiResults`

Reading a page:

```json
{
  "status": "ok",
  "reason": null,
  "page": {
    "name": "flask/json", "repo": "flask", "directory": "src/flask/json", "language": "python",
    "state": "fresh", "compiled_at": "2026-10-11T14:02:33Z", "compiler": "ccctx-wiki/1",
    "stale_reason": null, "symbols": 62,
    "text": "# flask/json\n\n`flask/json` is a Python package of 3 files and 62 definitions: ...",
    "citations": [
      {"name": "JSONProvider", "kind": "class", "role": "key", "repo": "flask",
       "path": "src/flask/json/provider.py", "start_line": 17, "end_line": 107,
       "commit": "5f2c1a9e04b7c3d8e1f0a2b4c6d8e0f1a3b5c7d9", "current_commit": "5f2c1a9e04b7c3d8e1f0a2b4c6d8e0f1a3b5c7d9"}
    ],
    "truncated": false
  },
  "pages": [],
  "truncated": false
}
```

Listing (no `page`):

```json
{
  "status": "ok",
  "reason": null,
  "page": null,
  "pages": [
    {"name": "flask/json", "repo": "flask", "state": "fresh",
     "summary": "A compact representation for lossless serialization of non-standard JSON types."}
  ],
  "truncated": false
}
```

| Field | Type | Meaning |
|---|---|---|
| `status` | `"ok" \| "unavailable"` | |
| `reason` | `string \| null` | `null` when `ok`. |
| `page` | object \| `null` | The page read. `null` when listing or refused. |
| `page.name`, `page.repo`, `page.directory`, `page.language` | `string` | `directory` is the path inside the repository (`.` for the root). |
| `page.state` | `"fresh" \| "stale"` | |
| `page.compiled_at` | `string` | ISO 8601 in UTC, `YYYY-MM-DDTHH:MM:SSZ`. |
| `page.compiler` | `string` | Who compiled it: the wiki compiler and its version, `ccctx-wiki/<n>`. |
| `page.stale_reason` | `string \| null` | What last made the page stale (`<name> changed (<old12> -> <new12>)`, `<name> was re-indexed` or `<name> is gone`), kept after a recompile. `null` if it never was. |
| `page.symbols` | `int` | Named definitions in the directory's own files. |
| `page.text` | `string` | The stored Markdown, at most 8000 characters. Contains no path and no line number. |
| `page.citations` | array, at most `200` | In citation order (role `key`, `file`, `depends`, `uses`, `calls`, then name). |
| `citation.name` | `string` | The symbol's qualified name, or the file's base name. |
| `citation.kind` | `string` | The symbol's kind, or `file`. |
| `citation.role` | `"key" \| "file" \| "depends" \| "uses" \| "calls"` | Why the page cites it (research R6). |
| `citation.repo`, `citation.path` | `string \| null` | Read through the citation's key. `null` when the record is gone. |
| `citation.start_line`, `citation.end_line` | `int \| null` | A symbol's current range, 1-based inclusive. `null` for a file or a gone record. |
| `citation.commit` | `string` | The commit the record had when the page was compiled. |
| `citation.current_commit` | `string \| null` | The record's current commit. `null` when it is gone. |
| `page.truncated` | `bool` | `true` when the page has more than 200 citations. |
| `pages` | array, at most `200` | Listing only, ordered by repository name then page name. Empty when reading or refused. |
| `pages[].name`, `pages[].repo` | `string` | |
| `pages[].state` | `"fresh" \| "stale"` | |
| `pages[].summary` | `string` | The first sentence of the page's purpose. |
| `truncated` | `bool` | `true` when more than 200 pages exist for the listing. |

A registered repository with no wiki (or not indexed) lists no pages, still `ok`.

### Failures

| Cause | `reason` |
|---|---|
| `page` empty or whitespace-only | `the page name is empty` |
| Unknown repository (checked first) | `no repository named '<repo>'` |
| Unknown page | `no wiki page named '<page>'` (with `repo`: `no wiki page named '<page>' in '<repo>'`) |
| Name in more than one repository, no `repo` | `wiki page '<page>' is in more than one repository: <repo>, <repo>; pass repo` |
| Database down | the driver's message, e.g. `DPY-6005: cannot connect to database ...` |

Refusals return `page: null`, `pages: []`, `truncated: false`, `isError: false`. The page name is checked before connecting.

## Version

`pyproject.toml` `version` and `golestan_code_mcp.__version__` are `1.1.0` (see `cli.md`).
