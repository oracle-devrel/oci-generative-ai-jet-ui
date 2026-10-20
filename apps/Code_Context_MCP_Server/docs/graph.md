# Code relationships

Ingest records three relationships from the parse tree of every file in a language it understands (see the table under [Ingesting a codebase](indexing.md#ingesting-a-codebase)):

- **defines**: the file each symbol is in.
- **imports**: the files of the same repository a file imports.
- **calls**: the symbol (or, for a module-level call, the file) making each call, the symbol called, and the line.

They form `ccctx_graph`, a SQL property graph (`CREATE PROPERTY GRAPH`) over the existing tables: files and symbols are its vertices, and imports, calls and defines its edges. Nothing is copied. Three commands query it with `GRAPH_TABLE … MATCH`:

```sh
uv run ccctx callers url_for                 # what calls this?
uv run ccctx calls url_for                   # what does this call?
uv run ccctx impact url_for --depth 3        # what could break: transitive callers, with hop counts
```

```text
CALLER          KIND      REPO   PATH                              LINE  CALLS
login_required  function  flask  examples/tutorial/flaskr/auth.py    25  url_for
...
url_for         function  flask  src/flask/helpers.py               244  Flask.url_for

FROM           LINE  CALLEE                    KIND    REPO   PATH                 LINES
Flask.url_for  1182  Flask.create_url_adapter  method  flask  src/flask/app.py     507-558
url_for         244  Flask.url_for             method  flask  src/flask/app.py     1102-1222

HOPS  NAME            KIND      REPO   PATH                              LINES
   1  login_required  function  flask  examples/tutorial/flaskr/auth.py  19-29
```

- **Names** are case-sensitive. A bare name (`url_for`) matches every function, method, class or type named `url_for` or `<something>.url_for`. A qualified name (`Flask.url_for`) matches only that definition. `CALLS` says which definition each call reaches.
- **`--depth`** is 1 to 5, default 3. Each symbol appears once, at its shortest distance, nearest first. Recursion and cycles are safe.
- **`--repo`** limits a command to the named repositories, as in search. Calls never cross repositories.
- The model is not needed, and ingest keeps the graph current: an incremental ingest leaves the same relationships as `--full`.

On flask, `ccctx callers url_for` finds all 51 calls to `url_for` inside functions and methods. `grep -rn url_for` finds 187 lines, but 136 of them are documentation, templates, comments, docstrings, strings and imports, and none of those appear. `impact url_for` stays at 36 symbols from depth 1 to 5: they are tests and view functions, which pytest and the router call, never other code. `impact Flask.url_for` grows from 1 symbol at depth 1 to 36 at depth 3.

Calls are matched to definitions by name, not by type inference:

- `x()` reaches functions and classes named `x`. In C#, Java, Kotlin, Swift, C++ and Ruby, where a method can call its own type's methods without a receiver, `x()` first reaches the enclosing type's method `x`.
- `module.x()` on an imported module of the repository is treated the same way.
- `self.x()` (and `this.x()`, `$this->x()`, `base.x()`, `Self::x()`) prefers the method of the enclosing class. `::` and `->` receivers read as dots.
- `obj.x()` reaches every method named `x`.
- A definition in the same file wins, then one in a file the caller imports, then any in the repository.

Dynamic calls, calls through variables, and the code a framework calls for you are not edges. Files indexed as line windows have no relationships.

The first ingest after upgrading re-reads every file for its relationships. Unchanged symbols keep their rows, so nothing is re-embedded: flask took 1.7 s.
