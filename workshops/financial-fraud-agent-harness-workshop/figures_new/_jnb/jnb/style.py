"""Matplotlib theme: New Computer Modern, dark surface, semantic colours."""
from __future__ import annotations

import logging

import matplotlib as mpl
from matplotlib import font_manager as fm

from .tokens import ASSETS, color, load_tokens

class _QuietSansBold(logging.Filter):
    # mathtext's custom fontset probes sans-bold-italic, which NCM Sans lacks;
    # matplotlib falls back to regular and warns on every kernel start.
    def filter(self, record):
        return not (record.name.endswith("font_manager") and "NewComputerModern Sans" in record.getMessage())


_families: dict[str, str] = {}


def register_fonts() -> dict[str, str]:
    """Register every font file in ASSETS/fonts with matplotlib (idempotent).

    Returns ``{'serif'|'sans'|'mono'|'math': internal family name}``.  The names in
    tokens.json are file stems; the font's own family name (what matplotlib needs,
    e.g. 'NewComputerModern 10') is read from the first file of each group.
    """
    if not _families:
        for p in sorted((ASSETS / "fonts").glob("*.otf")):
            fm.fontManager.addfont(str(p))
        files = load_tokens()["fonts"]["files"]
        for key, names in files.items():
            _families[key] = fm.FontProperties(
                fname=str(ASSETS / "fonts" / names[0])).get_name()
    return _families


def family(key: str) -> str:
    """Matplotlib family name for 'serif' | 'sans' | 'mono' | 'math'."""
    return register_fonts()[key]


def apply() -> None:
    """Install the theme into ``mpl.rcParams``."""
    fam = register_fonts()
    lg = logging.getLogger("matplotlib.font_manager")
    if not any(isinstance(f, _QuietSansBold) for f in lg.filters):
        lg.addFilter(_QuietSansBold())
    serif, sans, mono, math = fam["serif"], fam["sans"], fam["mono"], fam["math"]
    bg, fg = color("surface.bg"), color("text.body")
    muted = color("text.muted")
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": [serif],
        "font.sans-serif": [sans],
        "font.monospace": [mono],
        "font.size": 11,
        # math matches body text; big operators / symbols come from NewCMMath
        "mathtext.fontset": "custom",
        "mathtext.rm": serif,
        "mathtext.it": f"{serif}:italic",
        "mathtext.bf": f"{serif}:bold",
        "mathtext.sf": sans,
        "mathtext.tt": mono,
        "mathtext.cal": math,
        "mathtext.fallback": "stix",
        "axes.unicode_minus": True,
        "figure.facecolor": bg, "axes.facecolor": bg, "savefig.facecolor": bg,
        "savefig.edgecolor": "none", "figure.edgecolor": "none",
        "text.color": fg, "axes.labelcolor": fg, "axes.edgecolor": muted,
        "xtick.color": muted, "ytick.color": muted,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": False, "grid.color": color("surface.grid"),
        "axes.prop_cycle": mpl.cycler(color=[
            color("input"), color("output"), color("third"), color("fourth"),
            color("greys.cuboid_top")]),
        "legend.frameon": False,
        "svg.fonttype": "path",
        "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight",
        "savefig.pad_inches": 0.1,
    })
