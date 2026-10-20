"""The repository tool: list_repositories."""

from typing import Literal

import oracledb
from pydantic import BaseModel

from golestan_code_mcp import db, registry, schema
from golestan_code_mcp.config import ConfigError, load
from golestan_code_mcp.server import app


class RepoInfo(BaseModel):
    name: str
    path: str
    files: int
    symbols: int


class RepoList(BaseModel):
    database: Literal["reachable", "unreachable"]
    reason: str | None
    repositories: list[RepoInfo]


@app.mcp.tool(
    description="Which codebases can I ask about? Lists the registered repositories with their paths and how many "
    "files and symbols each holds. Use it to learn the valid repo values for the other tools, or after a repo was "
    "refused. A repository with 0 files is registered but not indexed yet.",
    annotations=app.READ_ONLY,
)
@app._logged
def list_repositories() -> RepoList:
    try:
        with db.connect(load()) as conn:
            schema.migrate(conn)
            repos = registry.list_repos(conn)
    except ConfigError as e:
        return RepoList(database="unreachable", reason=str(e), repositories=[])
    except oracledb.Error as e:
        return RepoList(database="unreachable", reason=db.describe(e), repositories=[])
    return RepoList(database="reachable", reason=None, repositories=[RepoInfo(**vars(r)) for r in repos])
