"""Helpers for the ccctx tests: run the command in-process, sample summaries, repositories and runs, and table
readers.
"""

import re
import subprocess
from collections import Counter

from golestan_code_mcp.cli import entry
from golestan_code_mcp.indexing import ingest as indexing_ingest

FAKE_PW = "Not-A-Real-Pw-42"


def run(capsys, *argv):
    code = entry.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def summary(skipped=(), no_grammar=0, parse_errors=0, files=176, symbols=1847):
    return indexing_ingest.Summary("flask", "a" * 40, False, Counter(dict(skipped)), files, no_grammar, parse_errors, symbols, 9.2)


def make_repo(root):
    root.mkdir()
    (root / "app.py").write_text("def a():\n    pass\n\n\nclass B:\n    def c(self):\n        pass\n")
    (root / "broken.py").write_text("def oops(:\n")
    (root / "notes.md").write_text("# notes\n")
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root, check=True,
                       capture_output=True)
    return root


HEADER = ["RANK", "SCORE", "FEEDBACK", "KEYWORD", "SEMANTIC", "REPO", "KIND", "NAME", "PATH", "LINES"]


def table(out):
    header, *rows = out.splitlines()
    assert header.split() == HEADER
    return [r.split() for r in rows]


def untimed(out):
    return re.sub(r"in [0-9.]+s", "", out)


# --- wiki (009 contracts/cli.md) ------------------------------------------------------------------------------


WIKI_PKG = '"""Ledger accounting for the demo."""\n' + "".join(
    f'\n\ndef post{i}():\n    """Post entry {i}."""\n    return {i}\n' for i in range(10))

WIKI_USER = "from pkg.core import post0\n\n\ndef use():\n    return post0()\n"


def make_wiki_repo(root):
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "app").mkdir()
    (root / "src" / "pkg" / "__init__.py").write_text('"""The demo ledger package."""\n')
    (root / "src" / "pkg" / "core.py").write_text(WIKI_PKG)
    (root / "app" / "main.py").write_text(WIKI_USER)
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root, check=True,
                       capture_output=True)
    return root


def a_run(tool, question, repo, results=(), status="ok", reason=None, client="test-client 9.9"):
    arguments = {"query": question, "repo": repo} if question else {}
    return {"tool": tool, "arguments": arguments, "question": question, "client": client, "status": status,
            "reason": reason, "ms": 3, "result_count": len(results), "results": list(results), "repos": [repo]}


def symbol_run(n, question, symbol, path, kind):
    return a_run("search_code", question, n, [{"kind": kind, "repo": n, "name": symbol, "path": path,
                                               "start_line": 1, "end_line": 9}])
