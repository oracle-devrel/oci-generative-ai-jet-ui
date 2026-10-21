"""Part 6 (capstone: autonomous AML triage) figure -> figures_new/d_capstone/*.svg + manifest.json.

Run:  cd figures_new && uv run -q --with matplotlib --with numpy --with ipython python d_capstone/build.py

A schematic: it carries no sample-run data. Static TikZ -> SVG with the page background baked in (bg=True).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "_jnb"))
import jnb  # noqa: E402

jnb.setup(chapter="6")

from figs import FIGURES  # noqa: E402

manifest = []
for fig in FIGURES:
    svg = jnb.tikz(fig["tikz"](), name=f"capstone-{fig['number']}-{fig['slug']}", bg=True)
    fname = f"fig-{fig['number']}-{fig['slug']}.svg"
    (HERE / fname).write_text(svg, encoding="utf-8")
    manifest.append({"number": fig["number"], "anchor": fig["anchor"], "svg": fname,
                     "prose": fig["prose"], "caption": fig["caption"]})
    print("wrote", fname, len(svg), "bytes")

(HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
print("wrote manifest.json with", len(manifest), "entries")
