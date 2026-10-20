# Quickstart: Validating Docs, License and Source Layout

Run these from the project root on the branch. The test suite needs the `oracle26ai` container running.

## 1. Reinstall once

Close the MCP clients first (Claude Code sessions using `ccctx`), so that `ccctx.exe` isn't locked. Then:

```powershell
uv sync
uv tool install --editable . --reinstall
```

Expected: both finish without errors, and `.venv\Lib\site-packages` holds a `__editable___golestan_code_mcp_*_finder.py`
and no `_editable_impl_golestan_code_mcp.pth`.

## 2. The source sits directly under src/

```powershell
Test-Path src\golestan_code_mcp                 # False
git diff master -M --stat -- src                # only renames, plus config.py and __init__.py
uv run python -c "import golestan_code_mcp.search.query as q; print(q.__file__)"   # ...\src\search\query.py
uv run python -c "import config"                # ModuleNotFoundError
```

## 3. Installed commands and the MCP server still work

```powershell
uv run golestan-check-db          # finds .env, prints the connection and version
ccctx --help                      # the uv tool install, run from anywhere
ccctx repo list
npx @modelcontextprotocol/inspector ccctx mcp    # Tools → List Tools: the same nine tools
```

In Claude Code, run `/mcp`: `ccctx` is connected without being registered again.

## 4. Docs and checks

```powershell
uv run pytest tests/test_layout.py tests/test_docs.py -q
uv run python specs/014-docs-license-src-layout/docscheck.py
```

Expected:
- **The layout test passes.** It reads CLAUDE.md's layout list. To see it fail, add an empty `src/search/extra.py`;
  the test names the file. Then remove it.
- **The link test passes.** To see it fail, break one link in a `docs/` page; the test names the page and the link.
- **The docs check finds nothing missing.** `docscheck.py` ends with `0 lines missing`.

## 5. Read the front page

Open `README.md`. Expected:
- **The first 30 lines.** The purpose, a link to the Coding Challenge #139 article, a link to GitHub Spec Kit, and
  that it is MIT-licensed.
- **License.** `LICENSE` holds the MIT text with 2026 and the author.
- **Length.** The README is at most 150 lines.

## 6. The suite passes

```powershell
uv run pytest -q
```

Expected: the same results as master, plus the new tests in `tests/test_docs.py` and the new package-list test.

## Verified (2026-10-16)

- **1. Reinstall.**
  - The two running servers (`ccctx.exe`, `golestan-code-mcp.exe`) were stopped with the user's approval.
  - `uv sync` installed 1.4.2 editable, through `__editable___golestan_code_mcp_1_4_2_finder.py`, and the old `.pth` is
    gone.
  - `uv tool install --editable . --reinstall` installed the 4 commands.
- **2. Layout.**
  - `src/golestan_code_mcp` is gone.
  - Of 69 files, 67 are pure renames. `config.py` (`parents[1]`) and `__init__.py` (version) change one line each.
  - `golestan_code_mcp.search.query` resolves to `src\search\query.py`, and `import config` fails.
- **3. Commands.**
  - `golestan-check-db` finds `.env` and connects.
  - `ccctx --help` and `ccctx repo list` work from the home directory.
  - `tests/cli/test_entry.py` lists the nine tools over stdio.
  - The MCP Inspector and Claude Code's `/mcp` reconnect are left to the user, since they are interactive.
- **4. Docs.**
  - `test_layout.py` passes, and fails naming an unlisted `search/extra.py`.
  - `test_docs.py` passes.
  - `docscheck.py` reports `0 lines missing`; one line is in `EXPECTED`: the old intro sentence, rewritten as the
    purpose paragraph.
- **5. README.** 104 lines. The article, Spec Kit, the MIT license and the `LICENSE` link are in the first 30 lines.
- **6. Suite.** 1,009 passed and 1 failed, run in four folder chunks.
  - **The failure.** `tests/server/test_search_tools.py::test_search_code_matches_core[arguments0]` depends on stored
    feedback and fails the same way on master (013 `moves.md`, bug 3).
  - **The count.** Master had 995 tests; the 15 new ones are 12 in `test_docs.py`, its 2 layout checks, and the
    package-list test.
