# Contract: `ccctx` command line

Entry point: `ccctx`, installed by the project (`uv run ccctx …`). Settings come from `.env` and the environment, as in phase 1 (`DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_SERVICE`). Errors go to stderr as `error: <reason>`. No output ever contains a password.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Refused input or missing setting. Nothing was written. |
| `2` | Database unreachable or still starting. Nothing was written. |

## `ccctx repo add <path> --name <name>`

Registers an existing directory. Applies any missing migrations first.

- `<path>`: `~` is expanded, then the path is resolved to an absolute path with no `..` or symlinks. It must be an existing directory.
- `--name <name>`: required. It must match `^[a-z0-9_-]{1,64}$`.

Success, exit `0`, stdout:

```text
registered flask /home/you/ccctx-repos/flask
```

Refusals, exit `1`, nothing recorded:

| Cause | stderr |
|---|---|
| Path missing | `error: <path> does not exist` |
| Not a directory | `error: <path> is not a directory` |
| Bad name | `error: invalid name '<name>': use 1-64 of a-z 0-9 - _` |
| Name taken | `error: name '<name>' is already registered to <existing path>` |
| Directory taken | `error: <path> is already registered as '<existing name>'` |

The order of checks is: name, then path, then database. A bad name is reported before the path is checked.

## `ccctx repo list`

Applies any missing migrations, then prints every repository sorted by name. Exit `0`.

```text
NAME   PATH                         FILES  SYMBOLS
flask  /home/you/ccctx-repos/flask      0        0
gin    /home/you/ccctx-repos/gin        0        0
```

- The header columns are `NAME`, `PATH`, `FILES`, `SYMBOLS`, in that order.
- `NAME` and `PATH` are left-aligned and padded to their widest value. `FILES` and `SYMBOLS` are right-aligned to the width of the header or the widest number. Columns are separated by two spaces.
- `FILES` is the number of `ccctx_files` rows for the repository. `SYMBOLS` is the number of `ccctx_symbols` rows in those files.
- With nothing registered the output is `no repositories registered`.

## `ccctx db migrate`

Applies every missing migration in order, then prints what it did. Exit `0`.

```text
applied 1 core tables
```

or, when nothing was missing:

```text
schema up to date (version 1)
```
