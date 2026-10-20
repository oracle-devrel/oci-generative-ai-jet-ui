"""Cloning the sample repositories: where they go, skipping what is there, and refusals."""

import subprocess

import pytest

from golestan_code_mcp import samples
from golestan_code_mcp.config import PROJECT_ROOT


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def origin(tmp_path):
    """A local repository with one commit, standing in for GitHub."""
    repo = tmp_path / "origin"
    repo.mkdir()
    git("init", "-q", cwd=repo)
    (repo / "README").write_text("hi\n")
    git("add", ".", cwd=repo)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init", cwd=repo)
    return [samples.Repo("demo", "python", repo.as_uri())]


def test_clone_then_present(tmp_path, origin):
    target = tmp_path / "repos dir"
    first = samples.clone(target, origin)
    assert [(status, name) for status, name, _ in first] == [("cloned", "demo")]
    assert len(first[0][2]) == 40
    second = samples.clone(target, origin)
    assert second == [("present", "demo", first[0][2])]


def test_refuses_folder_inside_project(origin):
    target = PROJECT_ROOT / "ccctx-repos-should-not-exist"
    with pytest.raises(samples.InsideProject):
        samples.clone(target, origin)
    assert not target.exists()


def test_non_git_folder_is_an_error(tmp_path, origin):
    (tmp_path / "repos" / "demo").mkdir(parents=True)
    with pytest.raises(samples.CloneFailed, match="demo"):
        samples.clone(tmp_path / "repos", origin)


def test_failed_clone_names_repo(tmp_path):
    missing = [samples.Repo("ghost", "go", (tmp_path / "nope").as_uri())]
    with pytest.raises(samples.CloneFailed, match="ghost"):
        samples.clone(tmp_path / "repos", missing)


def test_main_exit_codes(tmp_path, monkeypatch, origin, capsys):
    monkeypatch.setattr(samples, "REPOS", origin)
    monkeypatch.setenv("CCCTX_REPOS_DIR", str(tmp_path / "repos"))
    assert samples.main() == 0
    assert capsys.readouterr().out.startswith("cloned demo ")
    monkeypatch.setenv("CCCTX_REPOS_DIR", str(PROJECT_ROOT / "inside"))
    assert samples.main() == 1


def test_pinned_urls():
    assert [r.url for r in samples.REPOS] == [
        "https://github.com/pallets/flask.git",
        "https://github.com/gin-gonic/gin.git",
    ]
