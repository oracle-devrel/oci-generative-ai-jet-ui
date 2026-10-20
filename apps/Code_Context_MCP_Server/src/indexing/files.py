"""Ingest, files: list a repository's files with read-only git, and read the ones to index.

Files are only read. Git runs without a shell, without optional locks and with the repository's fsmonitor
and hooks disabled, so nothing configured inside the repository can run.
"""

import os
import subprocess
from collections import Counter
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from golestan_code_mcp.config import max_file_bytes, vendor_dirs


class IngestError(Exception):
    """Refused ingest. The message is safe to show the user."""


GIT_SAFE = ["-c", "core.fsmonitor=false", "-c", f"core.hooksPath={os.devnull}", "--no-optional-locks"]


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *GIT_SAFE, "-C", str(root), *args], capture_output=True)
    if done.returncode:
        reason = done.stderr.decode(errors="replace").strip().splitlines()
        raise IngestError(f"git {args[0]} failed in {root}: {reason[0] if reason else done.returncode}")
    return done.stdout.decode("utf-8", "surrogateescape")


def _paths(root: Path, *args: str) -> list[str]:
    """Paths printed NUL-separated (-z) by a git command, de-duplicated in order."""
    return list(dict.fromkeys(p for p in git(root, *args).split("\0") if p))


def _ls(root: Path, *flags: str) -> list[str]:
    return _paths(root, "ls-files", "-z", *flags)


def _read(root: Path, rel: str, limit: int, vendored: set[str]) -> tuple[str | None, str | None]:
    """(text, None) for a file worth indexing, (None, reason) for a skipped one, (None, None) for a gone one."""
    path = root / rel
    if vendored & set(PurePosixPath(rel).parts[:-1]):
        return None, "vendored"
    if path.is_symlink():
        return None, "ignored"
    if not path.is_file():  # tracked but deleted from the working tree
        return None, None
    if path.stat().st_size > limit:
        return None, "too large"
    data = path.read_bytes()
    if b"\0" in data:
        return None, "binary"
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError:
        return None, "binary"


def discover(root: Path, env: Mapping[str, str], only: list[str] | None = None) -> tuple[dict[str, str], Counter]:
    """Text of every file worth indexing, keyed by its repository-relative path, and skip counts per reason.

    `only` limits the read to those listed paths; ignored files are then not counted.
    """
    limit, vendored = max_file_bytes(env), vendor_dirs(env)
    if only is None:
        skipped = Counter(ignored=len(_ls(root, "--others", "--ignored", "--exclude-standard")))
        only = _ls(root, "--cached", "--others", "--exclude-standard")
    else:
        skipped = Counter()
    files = {}
    for rel in only:
        text, reason = _read(root, rel, limit, vendored)
        if reason:
            skipped[reason] += 1
        elif text is not None:
            files[rel] = text
    return files, +skipped
