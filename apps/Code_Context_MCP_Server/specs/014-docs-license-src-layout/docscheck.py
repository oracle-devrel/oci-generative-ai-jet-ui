"""Check that no line of master's README was lost when it was split into README.md, CLAUDE.md and docs/.

Every non-blank line of master's README outside its Layout section must appear, normalized, in the new documents,
unless EXPECTED names it with the reason it was reworded. Normalizing strips heading markers and outer whitespace,
and reduces Markdown links to their text. Run from the project root: python specs/014-docs-license-src-layout/docscheck.py
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# old line (normalized) -> why it reads differently now
EXPECTED: dict[str, str] = {
    "A code context MCP server backed by Oracle AI Database 26ai. It indexes codebases into the database, searches "
    "them by name and meaning, follows their calls, writes and maintains a wiki page about each module, and serves "
    "all of it to AI coding tools over MCP (`ccctx mcp`).":
        "rewritten as the README's longer purpose paragraph (FR-001)",
}


def normalize(line: str) -> str:
    line = re.sub(r"\[([^\]]*)\]\([^)\s]+\)", r"\1", line.strip())
    return re.sub(r"^#{1,6}\s+", "", line).strip()


def old_lines() -> list[tuple[int, str]]:
    text = subprocess.run(["git", "show", "master:README.md"], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout
    kept, in_layout = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            in_layout = line.strip() == "## Layout"
        if in_layout or not line.strip() or line.lstrip().startswith("```"):
            continue
        kept.append((number, normalize(line)))
    return kept


def main() -> int:
    new = set()
    for path in [ROOT / "README.md", ROOT / "CLAUDE.md", *(ROOT / "docs").glob("*.md")]:
        if path.exists():
            new.update(normalize(line) for line in path.read_text(encoding="utf-8").splitlines())
    missing = [(n, line) for n, line in old_lines() if line not in new and line not in EXPECTED]
    for number, line in missing:
        print(f"{number:4}: {line}")
    print(f"{len(missing)} lines missing")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
