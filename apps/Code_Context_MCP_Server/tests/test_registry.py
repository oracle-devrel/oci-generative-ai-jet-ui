"""Registry core (FR-005, FR-010 to FR-013). Database tests skip when it is unreachable."""

import uuid
from pathlib import Path

import pytest

from golestan_code_mcp import registry


def name():
    return f"t-{uuid.uuid4().hex[:8]}"


def repo_count(conn):
    with conn.cursor() as cur:
        return cur.execute("select count(*) from ccctx_repos").fetchone()[0]


@pytest.mark.parametrize("good", ["flask", "my-repo_2", "a", "x" * 64])
def test_valid_names(good):
    assert registry.validate_name(good) == good


@pytest.mark.parametrize("bad", ["Flask", "a b", "a/b", "", "x" * 65])
def test_invalid_names(bad):
    with pytest.raises(registry.RegistryError, match="invalid name"):
        registry.validate_name(bad)


def test_resolve_dir_expands_and_resolves(tmp_path, monkeypatch):
    (tmp_path / "repo").mkdir()
    monkeypatch.chdir(tmp_path)
    assert registry.resolve_dir("repo/../repo/") == (tmp_path / "repo").resolve()
    assert registry.resolve_dir("~") == Path.home().resolve()


def test_resolve_dir_refuses_missing_and_files(tmp_path):
    with pytest.raises(registry.RegistryError, match="does not exist"):
        registry.resolve_dir(tmp_path / "nope")
    (tmp_path / "f.txt").write_text("x")
    with pytest.raises(registry.RegistryError, match="is not a directory"):
        registry.resolve_dir(tmp_path / "f.txt")


def test_add_stores_absolute_path(conn, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "rel").mkdir()
    n = name()
    repo = registry.add_repo(conn, "rel", n)
    assert repo == registry.Repo(n, str((tmp_path / "rel").resolve()), 0, 0)
    assert any(r.name == n and r.path == repo.path for r in registry.list_repos(conn))


def test_refusals_record_nothing(conn, tmp_path):
    taken = name()
    registry.add_repo(conn, tmp_path, taken)
    (tmp_path / "other").mkdir()
    (tmp_path / "file.txt").write_text("x")
    before = repo_count(conn)
    cases = [
        (tmp_path / "missing", name(), "does not exist"),
        (tmp_path / "file.txt", name(), "is not a directory"),
        (tmp_path / "other", "Bad Name", "invalid name"),
        (tmp_path / "other", taken, f"name '{taken}' is already registered to"),
        (tmp_path / "other" / "..", name(), f"is already registered as '{taken}'"),
    ]
    for path, n, message in cases:
        with pytest.raises(registry.RegistryError, match=message):
            registry.add_repo(conn, path, n)
    assert repo_count(conn) == before


def test_list_sorted_with_counts(conn, tmp_path):
    a, b = sorted([name(), name()])
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    registry.add_repo(conn, tmp_path / "b", b)
    registry.add_repo(conn, tmp_path / "a", a)
    with conn.cursor() as cur:
        repo_id = cur.execute("select id from ccctx_repos where name = :n", n=a).fetchone()[0]
        for path, symbols in [("x.py", 2), ("y.py", 1), ("z.py", 0)]:
            file_id = cur.var(int)
            cur.execute(
                "insert into ccctx_files (repo_id, path, language, content_hash)"
                " values (:r, :p, 'python', :h) returning id into :i",
                r=repo_id, p=path, h="0" * 64, i=file_id,
            )
            for _ in range(symbols):
                cur.execute(
                    "insert into ccctx_symbols (file_id, name, kind, start_line, end_line, source, content_hash,"
                    " commit_sha) values (:f, 'f', 'function', 1, 1, 'x', :h, :c)",
                    f=file_id.getvalue()[0], h="0" * 64, c="a" * 40,
                )
    conn.commit()
    repos = registry.list_repos(conn)
    assert [r.name for r in repos] == sorted(r.name for r in repos)
    mine = {r.name: (r.files, r.symbols) for r in repos if r.name in (a, b)}
    assert mine == {a: (3, 3), b: (0, 0)}


def test_get_repo(conn, tmp_path):
    n = name()
    registry.add_repo(conn, tmp_path, n)
    repo_id, path = registry.get_repo(conn, n)
    assert isinstance(repo_id, int) and path == tmp_path.resolve()


def test_get_repo_unknown_name(conn):
    with pytest.raises(registry.RegistryError, match="no repository named 't-missing'"):
        registry.get_repo(conn, "t-missing")


def test_get_repo_deleted_directory(conn, tmp_path):
    n = name()
    (tmp_path / "gone").mkdir()
    registry.add_repo(conn, tmp_path / "gone", n)
    (tmp_path / "gone").rmdir()
    with pytest.raises(registry.RegistryError, match="does not exist"):
        registry.get_repo(conn, n)
