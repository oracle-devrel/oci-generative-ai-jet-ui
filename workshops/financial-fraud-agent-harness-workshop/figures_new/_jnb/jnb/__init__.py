"""jnb -- SITP-style notebooks (dark, New Computer Modern, semantic colour roles).

Notebook preamble::

    import sys; sys.path.insert(0, "_jnb")
    import jnb; jnb.setup(chapter="1.2")

Names
-----
``jnb.tikz``      the *function* ``tikz(src, name=None, scale=1.0) -> svg`` (slice B).
``jnb.tikz_mod``  the module ``jnb/tikz.py`` (``register_magic``, ...).
``from jnb.tikz import x`` still works (sys.modules); only the attribute
``jnb.tikz`` is the function.
"""
from __future__ import annotations

import base64
import html as _html
import io
import re
from pathlib import Path

from .tokens import ASSETS, color, load_tokens
from . import style
from .figures import annotated_matrix, iso_bars, role_arrow

try:  # slice B module; package must work before it exists
    from . import tikz as tikz_mod
    tikz = tikz_mod.tikz
except ImportError:  # pragma: no cover
    tikz_mod = None

    def tikz(*_a, **_k):
        raise ImportError("jnb/tikz.py is not installed in this copy of jnb")

__all__ = ["setup", "figure", "macros", "tex", "color", "load_tokens", "ASSETS",
           "annotated_matrix", "iso_bars", "role_arrow", "tikz", "tikz_mod", "style"]

_state = {"chapter": None, "n": 0}

# role macro name -> token role
_MACROS = {"inp": "input", "out": "output", "hl": "highlight",
           "third": "third", "fourth": "fourth"}


def _rgb(role: str) -> str:
    h = color(role).lstrip("#")
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def _macro_tex() -> str:
    # `#` inside a \newcommand body is a parameter reference (`#7aaed6` -> arg 7), and
    # JupyterLab's MathJax 3.2 has no HTML color model ("Color model 'HTML' not defined"),
    # so use the RGB model with 0-255 channels.
    return "".join(rf"\newcommand{{\{m}}}[1]{{{{\color[RGB]{{{_rgb(r)}}}{{#1}}}}}}"
                   for m, r in _MACROS.items())


def macros(display_it: bool = True) -> str:
    """Role macros ``\\inp \\out \\hl \\third \\fourth`` for MathJax.

    Emits a hidden ``$$\\newcommand...$$`` block.  MathJax 3 keeps ``\\newcommand``
    definitions for the page session, so later cells can use ``$\\inp{x}$`` --
    but definitions are lost on page reload until this cell is re-rendered, and
    renderers without MathJax (VS Code uses KaTeX, GitHub its own) may ignore
    them.  Portable fallback: ``tex('input', 'x')`` -> ``{\\color{#..}{x}}``.
    """
    tex_src = _macro_tex()
    if display_it:
        try:
            from IPython.display import display
            display({"text/html": _macro_div(), "text/plain": ""}, raw=True)
        except ImportError:
            pass
    return tex_src


def _macro_div() -> str:
    return f'<div style="display:none" class="jnb-macros">$${_macro_tex()}$$</div>'


def tex(role: str, s: str) -> str:
    """Portable coloured math: ``tex('input', 'x')`` -> ``{\\color{#7aaed6}{x}}``."""
    return rf"{{\color{{{color(role)}}}{{{s}}}}}"


def setup(chapter: str | None = None, theme: str = "dark") -> None:
    """Apply the matplotlib theme, reset the figure counter, define math macros,
    register ``%%tikz`` (if available and IPython is running)."""
    if theme != "dark":
        raise ValueError("only theme='dark' is defined in tokens.json")
    style.apply()
    _state["chapter"], _state["n"] = chapter, 0
    ip = None
    try:
        from IPython import get_ipython
        ip = get_ipython()
    except ImportError:
        pass
    if ip is not None:
        macros(True)
        if tikz_mod is not None and hasattr(tikz_mod, "register_magic"):
            tikz_mod.register_magic()


_FIG_CSS = (
    ":where(.jnb-figure){margin:1.2em auto;text-align:center}"
    ":where(.jnb-figure) svg,:where(.jnb-figure) img{max-width:100%;height:auto}"
    ":where(.jnb-figure) figcaption{margin-top:.5em;font-family:'NewCM10','New Computer Modern',serif;"
    "font-size:.95em;color:@MUTED@}"
    ":where(.jnb-fignum){margin-right:.5em}"
)


def _strip_svg(svg: str) -> str:
    i = svg.find("<svg")
    return svg[i:] if i >= 0 else svg


def figure(obj, caption: str | None = None) -> str:
    """Display ``obj`` as an auto-numbered figure; returns e.g. ``'1.2.3'``.

    ``obj``: matplotlib Figure (closed afterwards), SVG string, or path to .svg/.png.
    Output carries ``text/html`` (``<figure class="jnb-figure">``) plus an
    ``image/svg+xml`` or ``image/png`` alternative.
    """
    _state["n"] += 1
    num = f"{_state['chapter']}.{_state['n']}" if _state["chapter"] else str(_state["n"])
    svg = png = None
    if hasattr(obj, "savefig"):
        import matplotlib.pyplot as plt
        buf = io.BytesIO()
        obj.savefig(buf, format="svg")
        svg = _strip_svg(buf.getvalue().decode("utf-8"))
        buf = io.BytesIO()
        obj.savefig(buf, format="png")
        png = buf.getvalue()
        plt.close(obj)
    elif isinstance(obj, (str, Path)) and not (isinstance(obj, str) and obj.lstrip().startswith("<")):
        p = Path(obj)
        if p.suffix.lower() == ".svg":
            svg = _strip_svg(p.read_text(encoding="utf-8"))
        elif p.suffix.lower() == ".png":
            png = p.read_bytes()
        else:
            raise ValueError(f"unsupported figure file: {p}")
    elif isinstance(obj, str):
        svg = _strip_svg(obj)
    else:
        raise TypeError(f"cannot make a figure from {type(obj).__name__}")

    if svg is not None:
        body = svg
    else:
        body = '<img alt="" src="data:image/png;base64,%s"/>' % base64.b64encode(png).decode()
    cap = (f'<figcaption><span class="jnb-fignum">Figure {num}</span>{caption or ""}</figcaption>')
    css = _FIG_CSS.replace("@MUTED@", color("text.muted"))
    # JupyterLab typesets outputs concurrently on load, so the setup cell's macro block may
    # not be defined yet when this caption renders; carry the definitions in-band.
    uses_roles = caption and re.search(r"\\(" + "|".join(_MACROS) + r")\b", caption)
    defs = _macro_div() if uses_roles else ""
    doc = f'<figure class="jnb-figure">{defs}<style>{css}</style>{body}{cap}</figure>'
    bundle = {"text/html": doc,
              "text/plain": f"Figure {num}" + (f" {re.sub('<[^>]+>', '', caption)}" if caption else "")}
    if svg is not None:
        bundle["image/svg+xml"] = svg
    if png is not None:
        bundle["image/png"] = base64.b64encode(png).decode()
    try:
        from IPython.display import display
        display(bundle, raw=True)
    except ImportError:
        pass
    return num
