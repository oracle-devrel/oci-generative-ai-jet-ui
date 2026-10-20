"""Listing a repository's files: skip reasons, the vendor setting, and read-only git."""

import pytest

from collections import Counter

from golestan_code_mcp.indexing import files as indexing_files

from indexing.helpers import APP_PY, ENV, head, try_symlink

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


# --- discovery: no database -------------------------------------------------------------------------------


def test_discover_assigns_skip_reasons(repo):
    linked = try_symlink(repo)
    files, skipped = indexing_files.discover(repo, ENV)
    assert set(files) == {".gitignore", "app.py", "main.go", "web.js", "broken.py", "notes.txt", "empty.txt"}
    assert skipped == Counter({"ignored": 2 + linked, "vendored": 1, "binary": 2, "too large": 1})
    assert files["app.py"] == APP_PY
    assert not any(p.startswith(".git/") for p in files)


def test_discover_honours_vendor_setting(repo):
    files, skipped = indexing_files.discover(repo, {**ENV, "CCCTX_VENDOR_DIRS": ""})
    assert "vendor/dep.go" in files and "vendored" not in skipped


def test_git_helper_is_read_only(repo):
    before = (repo / ".git" / "index").read_bytes()
    indexing_files.discover(repo, ENV)
    indexing_files.git(repo, "status", "--porcelain")
    indexing_files.git(repo, "diff", "--name-only", "-z", "--no-renames", head(repo), "--")
    indexing_files.git(repo, "rev-parse", "--verify", "--quiet", f"{head(repo)}^{{commit}}")
    assert (repo / ".git" / "index").read_bytes() == before
