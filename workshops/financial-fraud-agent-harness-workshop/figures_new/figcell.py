"""Figure-cell rendering shared by .nbwork/sync_figures.py.

Expands the colour macros used in figures_new/*/manifest.json captions (\\inp \\out \\hl
\\third \\fourth \\negc) to portable ``{\\color{#hex}{...}}`` and builds the markdown source of
a figure cell (SVG as an inline data-URI <img>). Standard library only.
"""
from __future__ import annotations

import base64
import html
import re
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent

# jnb.tokens without running jnb/__init__.py (which imports matplotlib).
_pkg = types.ModuleType("jnb")
_pkg.__path__ = [str(HERE / "_jnb" / "jnb")]
sys.modules["jnb"] = _pkg
from jnb.tokens import color  # noqa: E402


def tex(role: str, s: str) -> str:
    """Same output as jnb.tex(): {\\color{#hex}{s}}."""
    return rf"{{\color{{{color(role)}}}{{{s}}}}}"


MACROS = {"inp": "input", "out": "output", "hl": "highlight",
          "third": "third", "fourth": "fourth", "negc": "negative"}
_MACRO_RE = re.compile(r"\\(" + "|".join(sorted(MACROS, key=len, reverse=True)) + r")(?![A-Za-z])")


def _arg(s: str, i: int) -> tuple[str, int]:
    """Parse a TeX macro argument starting at s[i]: {balanced} or one token."""
    while i < len(s) and s[i] in " \t":
        i += 1
    if i >= len(s):
        raise ValueError("macro without argument")
    if s[i] == "{":
        depth, j = 0, i
        while j < len(s):
            if s[j] == "\\":
                j += 2
                continue
            if s[j] == "{":
                depth += 1
            elif s[j] == "}":
                depth -= 1
                if depth == 0:
                    return s[i + 1:j], j + 1
            j += 1
        raise ValueError(f"unbalanced braces in {s[i:i+60]!r}")
    if s[i] == "\\":
        m = re.match(r"\\([A-Za-z]+|.)", s[i:])
        return m.group(0), i + len(m.group(0))
    return s[i], i + 1


def expand(s: str) -> str:
    out, pos = [], 0
    while True:
        m = _MACRO_RE.search(s, pos)
        if not m:
            out.append(s[pos:])
            return "".join(out)
        out.append(s[pos:m.start()])
        arg, pos = _arg(s, m.end())
        out.append(tex(MACROS[m.group(1)], expand(arg)))


def literal_dollars(s: str) -> str:
    """Manifest convention: ``\\$`` is a literal dollar. Inside math it stays ``\\$`` (valid in
    KaTeX and MathJax). In text, ``\\$`` is unsafe (markdown renderers eat the backslash and the
    bare ``$`` pairs with a later delimiter; ``&#36;`` decodes to ``$`` before KaTeX runs), so
    ``\\$1,234.5`` becomes the self-contained math span ``$\\$1{,}234.5$``."""
    out, i, n = [], 0, len(s)
    while i < n:
        if s.startswith("\\$", i):
            m = re.compile(r"\d[\d,]*(?:\.\d+)?").match(s, i + 2)
            if m:
                out.append("$\\$" + m.group(0).replace(",", "{,}") + "$")
                i = m.end()
            else:
                out.append("$\\$$")
                i += 2
        elif s[i] == "$":
            d = "$$" if s.startswith("$$", i) else "$"
            j = i + len(d)
            while j < n and not (s.startswith(d, j) and s[j - 1] != "\\"):
                j += 1
            if j >= n:
                raise ValueError(f"unterminated math span near {s[i:i+60]!r}")
            out.append(s[i:j + len(d)])
            i = j + len(d)
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def render(s: str) -> str:
    return literal_dollars(expand(s))



def _caption_html(caption: str) -> str:
    # escape unless it already carries markup/math
    return caption if re.search(r"[<$\\]", caption) else html.escape(caption)


def figure_cell(svg: str, name: str, alt: str, number: str, caption: str) -> dict:
    """jnb-figure markup with an inline data-URI <img>: JupyterLab's markdown attachment
    resolver rejects image/svg+xml ("Cannot render unknown image mime type")."""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    cap = f'<figcaption>{_caption_html(caption)}</figcaption>'
    img = (f'<img src="data:image/svg+xml;base64,{b64}" alt="{html.escape(alt, quote=True)}" '
           f'style="max-width:100%;height:auto">')
    return {"source": f'<figure class="jnb-figure" data-fig="{number}">\n\n{img}\n\n{cap}\n\n</figure>'}
