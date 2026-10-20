"""Helpers the test folders share: git with a test identity, and files written as given.

Test files import them by name (`from support import git`): pytest puts tests/ on the import path (pyproject.toml,
`pythonpath`). Fixtures live in conftest.py instead.
"""

import subprocess


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True,
                   capture_output=True)


def write(root, files):
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8", newline="\n")


def commit(root, message="change"):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
