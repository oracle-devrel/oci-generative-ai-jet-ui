# Module wiki

Search answers narrow questions such as "where is `url_for` defined?". It is weaker at "what does this module do?", because no single chunk says that. So the tool writes it down: one page for each directory whose own files hold at least 10 parsed definitions (line windows do not count).

```sh
uv run ccctx wiki build --repo flask      # without --repo: every indexed repository
uv run ccctx wiki list --repo flask
uv run ccctx wiki show flask/json
uv run ccctx wiki citations flask/json
```

**Page names.** A page is named after its directory, with a leading `src/` dropped, so `src/flask/json` is `flask/json`. The repository's root directory is named after the repository. When two repositories have a page with the same name, pass `--repo`. flask gets 7 pages and gin 7, each built in under 3 seconds.

**What a page says.** It is written from the index, by rules. No language model is involved and nothing leaves the database:
- **Opening sentence:** what the directory is and what it holds, counted from the index.
- **Purpose:** the directory's own documentation: module docstrings, Go package comments, or else the docs of its main types. A directory without documentation says so instead of guessing.
- **Key symbols:** up to 10, each with the first sentence of its doc.
  - Order: types first, then by how much code in other directories calls them.
  - Code in test files comes after the rest, and exported, documented symbols come before private ones.
- **Depends on:** the modules it imports, from the import edges, with the symbols it calls in each, then the packages it imports from outside the index.
- **Used by:** the modules that import it.

```text
flask/json (flask, src/flask/json) fresh, compiled 2026-10-11 21:51:36 by ccctx-wiki/1

# flask/json

`flask/json` is a Python package of 3 files and 62 definitions: 44 methods, 12 classes and 6 functions.
A compact representation for lossless serialization of non-standard JSON types. SecureCookieSessionInterface uses this to serialize the session data, but it may be useful in other places. It can be extended to support other types.

## Key symbols
- `TaggedJSONSerializer` (class): Serializer that uses a tag system to compactly represent objects that are not JSON types.
- `JSONProvider` (class): A standard set of JSON operations for an application.
- `jsonify` (function): Serialize the given arguments as JSON, and return a Response object with the application/json mimetype.
- `dumps` (function): Serialize data as JSON.
...

## Depends on
- `flask`: `_AppCtxGlobals.setdefault`
- Outside the index: `base64`, `dataclasses`, `datetime`, `decimal`, `json`, `markupsafe`, `typing`, `uuid`, `weakref`, `werkzeug`

## Used by
- `flask`, `flask/sansio`, `tests`

## Sources
- `JSONProvider` (class, key) src/flask/json/provider.py:19-105
- `dumps` (function, key) src/flask/json/__init__.py:13-44
...
```

**Citations are references, not text.** The stored page names symbols and modules but never contains a path or a line number. Every symbol or file a page names is a row in `ccctx_wiki_citations` with a foreign key to its `ccctx_symbols` or `ccctx_files` row, plus the commit and content hash it had when the page was compiled. The `Sources` list and `ccctx wiki citations` are read through those keys, so they always show where the code is now:

```text
NAME                 KIND      ROLE  REPO   PATH                        LINES    COMPILED      CURRENT
DefaultJSONProvider  class     key   flask  src/flask/json/provider.py  124-215  d086db856be1  d086db856be1
JSONProvider         class     key   flask  src/flask/json/provider.py  19-105   d086db856be1  d086db856be1
```

A citation can point at the right record or, once that record is deleted, at nothing. It cannot point at the wrong one.

**Stale pages are marked and rewritten.** When an ingestion changes the commit of a symbol a page cites, or removes it, that page is marked stale in the same transaction. After the ingest commits, the stale pages are recompiled. Pages that cite nothing that changed are left alone. If the recompile fails, the ingestion still stands, and the page stays marked stale wherever it is shown. Try it in the flask sample, then undo the tweak with `git revert HEAD` and ingest again:

```sh
cd ../ccctx-repos/flask
# edit a function the flask/json page cites, such as dumps in src/flask/json/__init__.py
git commit -am "tweak"
cd -
uv run ccctx ingest flask
uv run ccctx wiki list --repo flask
```

```text
Changed     1 files (0 added, 1 changed, 0 removed)
Unchanged 230 files
Skipped     0 files
Indexed     1 symbols in 4.1s
Wiki      flask/json stale: dumps changed (844a13f0be01 -> b2ca8484760e), recompiled
Wiki      tests stale: dumps changed (844a13f0be01 -> b2ca8484760e), recompiled
Wiki      2 stale, 2 recompiled, 0 added, 0 removed
```

Each `Wiki` line names a page that went stale and why: `<name> changed (<old> -> <new>)`, `<name> is gone`, or `<name> was re-indexed` after a full re-ingest. The `tests` page counts here because it cites `dumps` as a symbol it calls. `wiki list` keeps the last reason in its `LAST STALE` column. Ingestion only does this for repositories whose wiki was built once. It also adds pages for directories that now qualify and removes the ones that no longer do.

Ingestion stamps every symbol of a changed file with the new commit. So editing any function in a file a page cites marks the page stale, which errs toward rewriting a page rather than leaving it wrong.

**Pages in search.** Pages have their own hybrid index, built by `ccctx model load` or by the first `wiki build`, and search returns them beside symbols. A page hit has kind `page`, its directory as the path and no line range. `page (stale)` marks a page waiting to be rewritten. A page is placed above the first hit whose semantic similarity is lower than its own. A question that names a module, such as "the json module" or "package binding", puts that page first. The definitions of an exact identifier still come first.

| Question | First hit |
|---|---|
| what does the json module do | page `flask/json`, then gin's `codec/json` |
| what does the sansio module do (`--repo flask`) | page `flask/sansio` |
| what does the binding package do (`--repo gin`) | page `binding` |
| what does the render package do (`--repo gin`) | page `render` |

**Upgrading.** This version stores module docstrings and doc comments, which earlier versions did not. The first ingest of each repository after upgrading re-reads every file to fill them in. Unchanged symbols are kept, so nothing is re-embedded. Then run `ccctx wiki build` once.
