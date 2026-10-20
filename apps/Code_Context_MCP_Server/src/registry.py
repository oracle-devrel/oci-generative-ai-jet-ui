"""Repository registry: the core shared by the ccctx CLI and the MCP server.

Registering only checks that the path is a directory. It never reads, runs or changes its contents.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import oracledb

NAME_RE = re.compile(r"[a-z0-9_-]{1,64}")


class RegistryError(ValueError):
    """Refused input. The message is safe to show the user."""


@dataclass(frozen=True)
class Repo:
    name: str
    path: str
    files: int
    symbols: int


def validate_name(name: str) -> str:
    if not NAME_RE.fullmatch(name):
        raise RegistryError(f"invalid name '{name}': use 1-64 of a-z 0-9 - _")
    return name


def resolve_dir(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise RegistryError(f"{resolved} does not exist")
    if not resolved.is_dir():
        raise RegistryError(f"{resolved} is not a directory")
    return resolved


def _conflict(cur, name: str, path: str) -> RegistryError | None:
    row = cur.execute("select path from ccctx_repos where name = :n", n=name).fetchone()
    if row:
        return RegistryError(f"name '{name}' is already registered to {row[0]}")
    row = cur.execute("select name from ccctx_repos where path = :p", p=path).fetchone()
    if row:
        return RegistryError(f"{path} is already registered as '{row[0]}'")
    return None


def add_repo(conn, path: str | Path, name: str) -> Repo:
    validate_name(name)
    resolved = str(resolve_dir(path))
    with conn.cursor() as cur:
        if error := _conflict(cur, name, resolved):
            raise error
        try:
            cur.execute("insert into ccctx_repos (name, path) values (:n, :p)", n=name, p=resolved)
        except oracledb.IntegrityError:  # lost a race to a concurrent add
            conn.rollback()
            raise _conflict(cur, name, resolved) or RegistryError(f"could not register '{name}'")
    conn.commit()
    return Repo(name, resolved, 0, 0)


def repo_id(conn, name: str) -> int:
    """The id of a registered repository, whether or not its directory still exists."""
    with conn.cursor() as cur:
        row = cur.execute("select id from ccctx_repos where name = :n", n=name).fetchone()
    if row is None:
        raise RegistryError(f"no repository named '{name}'")
    return row[0]


def get_repo(conn, name: str) -> tuple[int, Path]:
    """The id and directory of a registered repository. The directory must still exist."""
    validate_name(name)
    with conn.cursor() as cur:
        row = cur.execute("select id, path from ccctx_repos where name = :n", n=name).fetchone()
    if row is None:
        raise RegistryError(f"no repository named '{name}'")
    return row[0], resolve_dir(row[1])


def list_repos(conn) -> list[Repo]:
    with conn.cursor() as cur:
        cur.execute(
            """select r.name, r.path, count(distinct f.id), count(s.id)
                 from ccctx_repos r
                 left join ccctx_files f on f.repo_id = r.id
                 left join ccctx_symbols s on s.file_id = f.id
                group by r.name, r.path
                order by r.name"""
        )
        return [Repo(*row) for row in cur]
