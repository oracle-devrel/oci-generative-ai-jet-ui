"""golestan-clone-samples: clone the sample repositories outside this project. Never runs cloned code."""

import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from golestan_code_mcp.config import PROJECT_ROOT, environment, repos_dir


class Repo(NamedTuple):
    name: str
    language: str
    url: str


REPOS = [
    Repo("flask", "python", "https://github.com/pallets/flask.git"),
    Repo("gin", "go", "https://github.com/gin-gonic/gin.git"),
]


class InsideProject(Exception):
    pass


class CloneFailed(Exception):
    pass


def _head(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def clone(target: Path, repos: list[Repo]) -> list[tuple[str, str, str]]:
    """Clone each repo into target/<name>, skipping ones already there. Returns (status, name, commit)."""
    target = target.resolve()
    if target.is_relative_to(PROJECT_ROOT):
        raise InsideProject(f"refusing {target}: it is inside the project {PROJECT_ROOT}")
    target.mkdir(parents=True, exist_ok=True)
    results = []
    for repo in repos:
        path = target / repo.name
        if (path / ".git").exists():
            results.append(("present", repo.name, _head(path)))
            continue
        if path.exists():
            raise CloneFailed(f"{repo.name}: {path} exists but is not a git repository")
        done = subprocess.run(["git", "clone", "--quiet", repo.url, str(path)], capture_output=True, text=True)
        if done.returncode:
            raise CloneFailed(f"{repo.name}: clone of {repo.url} failed: {done.stderr.strip()}")
        results.append(("cloned", repo.name, _head(path)))
    return results


def main() -> int:
    try:
        for status, name, commit in clone(repos_dir(environment()), REPOS):
            print(f"{status} {name} {commit}")
    except InsideProject as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except CloneFailed as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
