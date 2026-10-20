# Contract: Layout Conventions

The rules the new layout follows. `tests/test_layout.py` checks the first three; review checks the rest.

## Checked by a test

1. **Size.** No `.py` file under `src/` or `tests/` is longer than 300 lines. `tests/fixtures/` is exempt.
2. **Purpose.** Every such file opens with a module docstring whose first line states what the file holds.
3. **README.** The README's Layout section lists every source and test file with a one-line purpose, and nothing
   that is not on disk.

## Checked by review

4. **One home per name.** A definition lives in exactly one file. `__init__.py` files hold only a docstring. The
   exceptions are `cli/__init__.py` and `server/__init__.py`, which expose `main`; `server/__init__.py` also loads
   the tool files in order and applies the strict-arguments rule (research R2, R6).
5. **Imports.** Functions and module-level values from another file are used through their module, as `runs.record`.
   Classes, exceptions and result types may be imported by name. Imports are absolute (research R4).
6. **No new cycles.** Every module imports on its own in a fresh interpreter. A late import is allowed only where it
   was before, with its reason in a comment (research R5).
7. **Names unchanged.** Definitions keep their names, apart from `register` (research R8).
8. **Logger names.** Each area keeps its current logger name (research R7).
9. **Tests mirror the source.** The tests of `src/golestan_code_mcp/<area>/<file>.py` are in
   `tests/<area>/test_<file>.py`, or in `test_<file>_<concern>.py` files when they exceed the limit.
10. **Tests patch the defining file.** A test that replaces a function or value patches the module that defines it.
11. **Shared setup once.** Database connection, throwaway repositories and git helpers come from `tests/conftest.py`
    and `tests/support.py`. A fixture used by several files of one folder is in that folder's `conftest.py`.
