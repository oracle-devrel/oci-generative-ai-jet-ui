"""Regenerate every figure of the c_tools_loop slice (parts 4 and 5).

    cd figures_new && uv run -q --with matplotlib --with numpy --with ipython python c_tools_loop/build.py
"""
import re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_jnb"))
import jnb  # noqa: E402

jnb.setup(chapter="6")
COMMON = (HERE / "common.tex").read_text()


def build(slug_file, number, slug, subs=None, scale=1.0):
    src = (HERE / slug_file).read_text()
    for k, v in (subs or {}).items():
        src = src.replace(f"<<{k}>>", str(v))
    # NCM's ff/ffi ligature glyphs are missing from the dvisvgm output ("different" -> "dierent")
    src = re.sub(r"(\\begin\{tikzpicture\}(\[[^\]]*\])?)", r"\1\\addfontfeature{Ligatures=NoCommon}", src, count=1)
    # pad the bounding box so outer strokes (box borders, arrowheads) are not clipped at the SVG edge
    src = src.replace("\\end{tikzpicture}", "\\useasboundingbox ([shift={(-6pt,-6pt)}]current bounding box.south west) rectangle ([shift={(6pt,6pt)}]current bounding box.north east);\n\\end{tikzpicture}")
    svg = jnb.tikz(COMMON + src, name=f"fig-{number}-{slug}", scale=scale, bg=True)
    out = HERE / f"fig-{number}-{slug}.svg"
    out.write_text(svg)
    print("wrote", out.name, len(svg) // 1024, "KiB")


if __name__ == "__main__":
    only = sys.argv[1:]
    for f, n, s in [("fig-4-1-toolbox-flow.tex", "4.1", "toolbox-flow"), ("fig-4-2-register.tex", "4.2", "register"), ("fig-5-1-hierarchy.tex", "5.1", "hierarchy"), ("fig-5-2-summarize.tex", "5.2", "summarize"), ("fig-5-3-agent-loop.tex", "5.3", "agent-loop"), ("fig-5-4-offload.tex", "5.4", "offload")]:
        if not only or n in only:
            build(f, n, s)
