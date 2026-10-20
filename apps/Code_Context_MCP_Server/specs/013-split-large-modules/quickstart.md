# Quickstart: Validating Split Large Modules

How to check the feature is done and changed nothing. Run from the project root on the branch. The database steps
need the `oracle26ai` container running, with the model loaded and flask, gin and selenium-e2e indexed.

## 1. The layout holds

```powershell
uv run pytest tests/test_layout.py -q
```

Expected:
- **Line limit.** Every source and test file is at most 300 lines.
- **Docstrings.** Every file opens with a docstring.
- **README.** The README's Layout section lists exactly the files on disk.

To see the check work, add an empty `src/golestan_code_mcp/search/extra.py`. The test fails and names it. Then remove
the file.

## 2. Every definition moved unchanged

```powershell
git worktree add $env:TEMP\ccctx-master master
uv run python specs/013-split-large-modules/movecheck.py $env:TEMP\ccctx-master .
```

Expected:
- **Unchanged definitions.** Every top-level definition of master's source and every test function appears once on
  the branch with an equal syntax tree.
- **Exceptions.** The only exceptions are those in [data-model.md, Section 3](data-model.md).
- **Output.** The script ends with `0 missing, 0 changed, 0 duplicated`.

## 3. Every module loads on its own

```powershell
uv run python specs/013-split-large-modules/movecheck.py --imports
```

Expected: each module imports alone in a fresh interpreter, with no import cycle and no incomplete language table.

## 4. The installed commands are untouched

```powershell
git diff master -- pyproject.toml     # [project.scripts] unchanged
.venv\Scripts\ccctx.exe --help        # the existing wrapper, without uv sync
.venv\Scripts\python -m golestan_code_mcp.cli repo list
```

Expected:
- **Entry points.** The script section is unchanged.
- **Help.** `ccctx --help` prints the same help as on master.
- **`python -m`.** The CLI form lists the repositories.

The server's `python -m` form is not run by hand, since it would wait on stdin. The baseline (step 5) starts the
server that way to list its tools.

## 5. Behavior is the same, on the same database state

Copy `.env` into the worktree. Then record master and the branch one after the other:

```powershell
Copy-Item .env $env:TEMP\ccctx-master\
$env:PYTHONPATH = "$env:TEMP\ccctx-master\src"; uv run python specs/013-split-large-modules/baseline.py --out $env:TEMP\before
Remove-Item Env:PYTHONPATH;                     uv run python specs/013-split-large-modules/baseline.py --out $env:TEMP\after
uv run python specs/013-split-large-modules/baseline.py --compare $env:TEMP\before $env:TEMP\after
```

Expected: no difference in any of these:
- the tool listing;
- the CLI output;
- the parse output and language tables;
- the stored rows;
- the eval result.

If one step hit ORA-51815 (stale vector index, research R10), rerun that step for both, one after the other.

## 6. The suite passes, in any order

```powershell
uv run pytest -q
uv run --with pytest-randomly pytest -q -p randomly
uv run pytest tests/memory/test_runs.py -q      # any one file alone
```

Expected:
- **Test count.** The same number of tests as on master, plus the new layout tests.
- **Order.** All pass in random order and file by file.
- **Runtime.** The suite takes at most 10% longer than master's on the same database (research R14).

## 7. Clean up

```powershell
git worktree remove --force $env:TEMP\ccctx-master    # also removes the copied .env
```
