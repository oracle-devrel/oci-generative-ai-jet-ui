"""Regenerates every figure of this slice: fig-<n>-<slug>.svg (page background baked in)."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_jnb")); sys.path.insert(0, str(HERE))
import jnb
from figgeom import build_tex as geometry_tex   # figure 2.1 is generated from the real distances
jnb.setup(chapter="0")


def compile_tex(stem):
    svg = jnb.tikz_mod.tikz_file(HERE / f"{stem}.tex", name=stem, bg=True)
    (HERE / f"{stem}.svg").write_text(svg)
    print("wrote", f"{stem}.svg")


def figure_2_1():
    (HERE / "fig-2.1-embedding-geometry.tex").write_text(geometry_tex())
    compile_tex("fig-2.1-embedding-geometry")


FIGS = [
    ("fig-0.1-harness-anatomy", lambda: compile_tex("fig-0.1-harness-anatomy")),
    ("fig-2.1-embedding-geometry", figure_2_1),
    ("fig-2.2-scan-pipeline", lambda: compile_tex("fig-2.2-scan-pipeline")),
]

if __name__ == "__main__":
    only = sys.argv[1:]
    for name, fn in FIGS:
        if not only or any(o in name for o in only):
            fn()
