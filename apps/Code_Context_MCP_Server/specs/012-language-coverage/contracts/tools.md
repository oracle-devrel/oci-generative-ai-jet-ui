# Contract: MCP tools (server 1.4.0)

Extends `specs/011-usage-feedback/contracts/tools.md`. Every rule there still applies. The server still lists exactly
nine tools. No tool's name, parameters, defaults, annotations or result fields change. The version is `1.4.0`, because
the new language values are an additive capability (MINOR, constitution III).

## `search_code`

**Parameter description** of `language`: the 008 text, with the list replaced by every value the chunker assigns,
sorted:

| Parameter | Description |
|---|---|
| `language` | Search only files of this language: one of batch, c, cpp, csharp, css, go, html, ini, java, javascript, json, kotlin, markdown, php, proto, python, rst, ruby, rust, shell, sql, swift, text, toml, tsx, typescript, yaml. Default: all languages. |

**Refusal**: an unknown value answers `unavailable` with `unknown language '<v>'; valid languages: <the list above>`.

**Hits**: definitions of the new languages are hits like any other. Their `kind` is one of the existing kinds, and
their `language` is one of the new values.

## `get_symbol`, `find_callers`, `find_callees`, `impact_of`

Their descriptions and shapes are unchanged. They now find the new languages' definitions by the names of research
R4 (`DriverFixture.GetWebDriver`, `Engine.start`, `Acme.Parser.parse`).

One sentence of `get_symbol`'s description stays true and unchanged: "Unparsed files indexed as line windows have no
names and are not found here". It now covers fewer files.

## `read_wiki`

Pages of the new languages name their language in plain words ("`EATestFramework/Driver` is a C# directory of ...").
The shape is unchanged.

## Contract tests (`tests/test_server.py`)

- **The tool list**: the existing test still passes against the 008 to 011 contracts. The `language` description is
  read from this contract instead of 008's.
- **Refusal**: an unknown `language` lists the new values.
- **Core match**: a `search_code` hit for a C# fixture definition matches the core's result.
