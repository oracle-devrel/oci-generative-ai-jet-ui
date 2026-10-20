# Data Model: Language Coverage

## Migration 10, "language coverage"

| Change | Type | Rules |
|---|---|---|
| `ccctx_files.namespaces` | JSON, null | The namespaces the file declares, as a list of strings (`["EATestFramework.Driver"]`). Set for C# files; null for every other language. Written by ingest with the file row. |
| `ccctx_symbols.exported` | boolean, null | Whether the definition is public in its language (research R9). Null for line windows (`kind = 'chunk'`). |

**Backfill**, in the same migration, so pages compiled from rows written before it rank as before:

```sql
update ccctx_symbols s
   set exported = case
         when (select f.language from ccctx_files f where f.id = s.file_id) = 'go'
           then regexp_like(regexp_substr(s.name, '[^.]+$'), '^[A-Z]')
         else not regexp_like(regexp_substr(s.name, '[^.]+$'), '^_') end
 where s.kind <> 'chunk' and s.exported is null
```

Both statements are re-runnable: the alters tolerate "already exists" (ORA-01430), and the update touches only null
rows.

## Chunker output

### `Chunk` (one definition or window)

| Field | Change |
|---|---|
| `name`, `kind`, `start_line`, `end_line`, `source`, `doc` | unchanged; the names and kinds follow research R4 and R5 |
| `exported` | new: `bool \| None`. Set by every walker, including Python, Go and JavaScript by their existing rule. None for windows. |

### `parse(language, text)`

It returns `(chunks, calls, imports, doc, namespaces)`, or None when the language has no rules or the file doesn't
parse.
- **New**: `namespaces`, the declared namespaces as a list of strings. Empty for every language but C#.
- **Unchanged**: `Call` and `Import` (research R6, R7). C and C++ store an angled include with its brackets
  (`<vector>`), so it never resolves and becomes an outside dependency.

### Language tables (`chunker` plus `languages.py`)

| Table | Key | Value |
|---|---|---|
| `EXTENSIONS` | extension | language (research R2) |
| `NAMES` | file name | language (`Rakefile`, `Gemfile`) |
| `GRAMMARS` | language | `(module, function)`, loaded on first use (research R3) |
| `WALKERS` | language | definitions: `(name, kind, node, exported)` |
| `CALLS` | language | `root, scopes -> list[Call]` for the new languages; the existing table form for the three old ones |
| `IMPORTS` | language | `root -> Iterator[Import]` |
| `SYMBOL_DOCS` | language | `(node, data) -> str \| None` |
| `FILE_DOCS` | language | `(root, data) -> str \| None` (replaces `_file_doc`'s if-chain; the Python and Go entries keep today's behavior) |
| `NAMESPACES` | language | `root -> list[str]`; C# only |

## Ingest

- **`_lock`**: returns `{path: (content_hash, language)}`. The hash is used as today.
- **Re-read rule**: an unchanged file is re-read when its stored language differs from `detect_language(path)` now
  (research R10).
- **`Summary.reparsed`**: new, `Counter[str]`. Files re-read only because their language gained rules, by new
  language. Empty in full mode and when there are none.
- **The ingest log record** gains `"reparsed": {language: n}`.
- **`_write`**: stores `namespaces` on the file row and `exported` on each symbol row.
- **`_keep_unchanged`**: updates `exported` alongside `doc`.

## Graph

- **`_files`**: returns `{file_id: (path, language, namespaces)}`.
- **`_imports`**: resolves the new languages by research R6, and records unresolved ones as outside.
- **Two new indexes**, built once per rebuild:
  - path suffix to files, for C/C++, Java, Kotlin, PHP and Ruby
  - namespace to files, for C#
- **`SELF`**: `{"self", "cls", "this", "Self", "base"}`.

## Wiki

- **`LANGUAGE_NAMES`**: gains the eleven new values.
- **The key-symbol rank**: reads `exported` from `ccctx_symbols`. The symbol query adds the column.
- **`_is_test`**: gains the patterns of research R11.

## State

Nothing new has a lifecycle:
- **A file's language** changes only when a rule for its extension is added. The next ingest then re-reads it.
- **`namespaces` and `exported`** are rewritten whenever the file is.
