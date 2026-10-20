"""repo add and list, ingest, symbols, stats, model load and db migrate, with their refusals and exit codes."""

import re
import subprocess
import time
import uuid
from dataclasses import replace

import pytest

from golestan_code_mcp import registry
from golestan_code_mcp.indexing import ingest as indexing_ingest

from cli.helpers import FAKE_PW, WIKI_PKG, run, summary, untimed


def test_add_then_list(live, capsys, tmp_path):
    n = f"t-{uuid.uuid4().hex[:8]}"
    code, out, _ = run(capsys, "repo", "add", str(tmp_path), "--name", n)
    assert code == 0
    assert out.strip() == f"registered {n} {tmp_path.resolve()}"

    code, out, _ = run(capsys, "repo", "list")
    assert code == 0
    header, *rows = out.splitlines()
    assert header.split() == ["NAME", "PATH", "FILES", "SYMBOLS"]
    mine = [r for r in rows if r.split()[0] == n]
    assert len(mine) == 1 and mine[0].split()[-2:] == ["0", "0"]
    assert len({len(line.rstrip()) for line in [header, *rows]}) == 1  # right-aligned counts end in one column


@pytest.mark.parametrize(("path", "name", "message"), [
    ("{tmp}/missing", "t-ok", "does not exist"),
    ("{tmp}/file.txt", "t-ok", "is not a directory"),
    ("{tmp}", "Bad", "invalid name"),
])
def test_refusals_without_database(capsys, tmp_path, monkeypatch, path, name, message):
    monkeypatch.setenv("DB_PORT", "1")  # proves these never reach the database
    (tmp_path / "file.txt").write_text("x")
    code, out, err = run(capsys, "repo", "add", path.format(tmp=tmp_path), "--name", name)
    assert code == 1 and out == ""
    assert err.startswith("error: ") and message in err


def test_duplicate_name_exits_1(live, capsys, tmp_path):
    n = f"t-{uuid.uuid4().hex[:8]}"
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    assert run(capsys, "repo", "add", str(tmp_path / "a"), "--name", n)[0] == 0
    code, _, err = run(capsys, "repo", "add", str(tmp_path / "b"), "--name", n)
    assert code == 1 and "already registered" in err


def test_empty_registry(capsys, monkeypatch, live):
    monkeypatch.setattr(registry, "list_repos", lambda conn: [])
    code, out, _ = run(capsys, "repo", "list")
    assert code == 0 and out.strip() == "no repositories registered"


def test_migrate(live, capsys):
    code, out, _ = run(capsys, "db", "migrate")
    assert code == 0
    assert out.startswith(("applied ", "schema up to date (version "))


@pytest.mark.parametrize("argv", [
    ["repo", "list"], ["db", "migrate"], ["repo", "add", ".", "--name", "t-x"],
    ["ingest", "flask"], ["symbols", "--repo", "flask"], ["stats", "--by-language"],
])
def test_unreachable_exits_2_fast_without_secret(capsys, monkeypatch, argv):
    monkeypatch.setenv("DB_PORT", "1")
    monkeypatch.setenv("DB_PASSWORD", FAKE_PW)
    started = time.monotonic()
    code, out, err = run(capsys, *argv)
    assert time.monotonic() - started < 5
    assert code == 2 and err.startswith("error: ")
    assert FAKE_PW not in out + err


def test_missing_setting_exits_1(capsys, monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "")
    code, _, err = run(capsys, "repo", "list")
    assert code == 1 and "DB_PASSWORD" in err


def test_ingest_prints_summary(ingested):
    _, out = ingested
    lines = out.splitlines()
    assert [line.split()[0] for line in lines] == ["Scanned", "Skipped", "Indexed", "Fallback"]
    assert lines[0].split()[1] == "3" and lines[2].endswith("s")
    assert "(1 no grammar, 1 parse errors)" in lines[3]


def test_ingest_refusals_exit_1(model, capsys, tmp_path):
    assert run(capsys, "ingest", "t-missing")[0] == 1
    n = f"t-{uuid.uuid4().hex[:8]}"
    run(capsys, "repo", "add", str(tmp_path), "--name", n)
    code, _, err = run(capsys, "ingest", n)
    assert code == 1 and "not a git repository" in err


def test_symbols_lists_parsed_first(ingested, capsys):
    n, _ = ingested
    code, out, _ = run(capsys, "symbols", "--repo", n, "--limit", "3")
    header, *rows = out.splitlines()
    assert code == 0 and header.split() == ["NAME", "KIND", "LANGUAGE", "PATH", "LINES"]
    assert [r.split()[:2] for r in rows] == [["a", "function"], ["B", "class"], ["B.c", "method"]]
    assert rows[0].split()[2:] == ["python", "app.py", "1-2"]
    code, out, _ = run(capsys, "symbols", "--repo", n, "--kind", "chunk")
    assert {r.split()[1] for r in out.splitlines()[1:]} == {"chunk"}


def test_stats_by_language(ingested, capsys):
    n, _ = ingested
    code, out, _ = run(capsys, "stats", "--by-language", "--repo", n)
    header, *rows = out.splitlines()
    assert code == 0 and header.split() == ["REPO", "LANGUAGE", "FILES", "SYMBOLS", "CHUNKS"]
    assert [r.split() for r in rows] == [[n, "markdown", "1", "0", "1"], [n, "python", "2", "3", "1"]]


# --- model load and search (004) ----------------------------------------------------------------------------


def test_model_load_when_present(model, capsys):
    code, out, _ = run(capsys, "model", "load")
    assert code == 0 and out.strip() == "model ALL_MINILM_L12_V2 already present (384 dimensions)"


def test_ingest_again_then_full(ingested, capsys):
    n, first = ingested
    code, out, _ = run(capsys, "ingest", n)
    assert code == 0 and out.startswith(f"{n} is already up to date at ") and "--full" in out
    code, out, _ = run(capsys, "ingest", n, "--full")
    assert code == 0 and untimed(out) == untimed(first)  # same counts as the first ingest (SC-004)
    assert [line.split()[0] for line in out.splitlines()] == ["Scanned", "Skipped", "Indexed", "Fallback"]


def test_note_goes_to_stderr(live, capsys, monkeypatch):
    monkeypatch.setattr(indexing_ingest, "ingest", lambda conn, name, full=False: replace(
        summary(), note="no recorded revision for 'flask'; indexing in full"))
    code, out, err = run(capsys, "ingest", "flask")
    assert code == 0 and out.startswith("Scanned")
    assert "note: no recorded revision for 'flask'; indexing in full" in err


def test_ingest_prints_the_pages_it_recompiled(wikirepo, capsys):
    n, root, _, _ = wikirepo
    core = root / "src" / "pkg" / "core.py"
    core.write_text(WIKI_PKG.replace("return 0\n", "return -1\n"))
    for args in (["add", "-A"], ["commit", "-q", "-m", "tweak"]):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root, check=True,
                       capture_output=True)
    code, out, _ = run(capsys, "ingest", n)
    lines = out.splitlines()
    assert code == 0
    assert re.fullmatch(r"Wiki      pkg stale: \S+ (changed \([0-9a-f]{12} -> [0-9a-f]{12}\)|is gone), recompiled",
                        lines[-2])
    assert lines[-1] == "Wiki      1 stale, 1 recompiled, 0 added, 0 removed"
    assert "fresh" in run(capsys, "wiki", "list", "--repo", n)[1]


def test_ingest_warns_when_the_wiki_was_not_recompiled(model, capsys, monkeypatch):
    from golestan_code_mcp.wiki.build import Refresh

    s = replace(summary(), mode="incremental", added=0, changed=1, removed=0, unchanged=3,
                wiki=Refresh([("pkg", "post0 is gone")], error="boom"))
    monkeypatch.setattr(indexing_ingest, "ingest", lambda conn, name, full=False: s)
    code, _, err = run(capsys, "ingest", "flask")
    assert code == 0 and "warning: wiki not recompiled: boom" in err
