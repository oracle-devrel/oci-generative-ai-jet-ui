"""Wiki text helpers: split documentation into safe sentences, and join names into readable lists."""

import re

from golestan_code_mcp.parsing import tables

MAX_SENTENCE = 300

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
SPHINX_ROLE = re.compile(r":(?:[\w-]+:)+`[~!]?(?:[^`<]*<)?([^`>]+)>?`")  # :class:`~a.B` and :ref:`text <a.B>`
DIRECTIVE = re.compile(r"(?<!\S)\.\. [\w:-]+::")
UNDERLINE = re.compile(r"(?<!\S)([=\-~^\"'#*+])\1{2,}(?!\S)")
_EXTENSIONS = "|".join(sorted((re.escape(e[1:]) for e in tables.EXTENSIONS), key=len, reverse=True))
# A file name with an indexed extension (not a dotted name going on, like flask.json.dumps), or a line number.
UNSAFE = re.compile(rf"[\w-]\.(?:{_EXTENSIONS})(?!\w|\.\w)|\b(?i:line)\s+\d+")


def _sentences(doc: str | None) -> list[str]:
    """The doc's sentences that are safe to quote: Sphinx roles reduced to their last name, directives, RST
    underlines and backticks removed, and no sentence that names a file or a line."""
    text = SPHINX_ROLE.sub(lambda m: m.group(1).rsplit(".", 1)[-1], doc or "")
    text = UNDERLINE.sub("", text).replace("`", "")  # a backticked name in the page is always a cited one
    found = []
    # simplified: docs are stored as one collapsed paragraph, so a directive drops its whole sentence
    for sentence in SENTENCE_END.split(text):
        sentence = " ".join(sentence.split())
        if sentence and not DIRECTIVE.search(sentence) and not UNSAFE.search(sentence):
            found.append(sentence if len(sentence) <= MAX_SENTENCE else sentence[:MAX_SENTENCE - 3].rstrip() + "...")
    return found


def _plural(n: int, word: str) -> str:
    return f"{n} {word if n == 1 else word + ('es' if word.endswith('s') else 's')}"


def _and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _ticked(names) -> str:
    return ", ".join(f"`{n}`" for n in names)
