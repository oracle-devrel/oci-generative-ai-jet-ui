"""The documents: every relative link resolves, and the README and LICENSE say what they must.

- Every relative link in README.md, CLAUDE.md and docs/*.md names an existing file, and its `#fragment`, if any, a
  heading of that file, slugged as GitHub does. Links inside fenced code blocks don't count.
- The README is short, and its first screen names the article the idea came from, Spec Kit and the license.
- LICENSE holds the MIT License.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = sorted([ROOT / "README.md", ROOT / "CLAUDE.md", *(ROOT / "docs").glob("*.md")])
ARTICLE = "https://codingchallenges.substack.com/p/coding-challenge-139-code-context"
SPEC_KIT = "https://github.github.com/spec-kit/"
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def prose(path: Path) -> list[str]:
    """The file's lines outside fenced code blocks."""
    lines, fenced = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            lines.append(line)
    return lines


def slugs(path: Path) -> set[str]:
    """The anchors GitHub gives the file's headings."""
    seen: dict[str, int] = {}
    for line in prose(path):
        heading = re.match(r"#{1,6}\s+(.*)", line)
        if not heading:
            continue
        slug = re.sub(r"[^\w\- ]", "", heading.group(1).strip().lower()).replace(" ", "-")
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        if count:
            seen[f"{slug}-{count}"] = 1
    return set(seen)


@pytest.mark.parametrize("doc", DOCS, ids=[p.relative_to(ROOT).as_posix() for p in DOCS])
def test_relative_links_resolve(doc):
    assert doc.exists(), "missing"
    broken = []
    for line in prose(doc):
        for target in LINK.findall(line):
            if re.match(r"(https?|mailto):", target):
                continue
            name, _, fragment = target.partition("#")
            linked = (doc.parent / name).resolve() if name else doc
            if not linked.exists() or (fragment and fragment not in slugs(linked)):
                broken.append(target)
    assert broken == []


def test_readme_is_short():
    lines = len((ROOT / "README.md").read_text(encoding="utf-8").splitlines())
    assert lines <= 150, f"{lines} lines"


def test_readme_first_screen_names_the_article_spec_kit_and_license():
    first = "\n".join((ROOT / "README.md").read_text(encoding="utf-8").splitlines()[:30])
    assert ARTICLE in first
    assert SPEC_KIT in first
    assert "(LICENSE)" in first
    assert "MIT" in first


def test_license_is_mit():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.splitlines()[0] == "MIT License"
    assert "Copyright (c) 2026 Mohammad Hossein Golestan" in text
    assert "Permission is hereby granted, free of charge" in text
