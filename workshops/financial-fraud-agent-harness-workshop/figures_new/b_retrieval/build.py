"""Part 3 (Retrieval) figures -> figures_new/b_retrieval/fig-3.<n>-<slug>.svg

Run:  cd figures_new && uv run -q --with matplotlib --with numpy --with ipython python b_retrieval/build.py

Figure 3.2 is computed from the hybrid_search_knowledge constants (rrf_k = 60, 30 rows per leg);
Figure 3.1 is static TikZ.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_jnb"))
import jnb  # noqa: E402

jnb.setup(chapter="3")
T = jnb.tikz_mod

RRF_K = 60            # rrf_k default of hybrid_search_knowledge
PER_LIST = 30         # rows fetched from each leg


def build(name, **kw):
    svg = T.tikz_file(HERE / f"{name}.tex", name=name, bg=True, **kw)
    (HERE / f"{name}.svg").write_text(svg, encoding="utf-8")
    print("wrote", name)


def fig_3_1():
    build("fig-3.1-bi-vs-cross")


def fig_3_2():
    ys = 171.0  # cm per unit score -> 0.035 fills ~6 cm
    y = lambda v: v * ys
    one = lambda r: 1.0 / (RRF_K + r)
    both_lo, both_hi = 2.0 / (RRF_K + PER_LIST), 2.0 / (RRF_K + 1)
    curve = " ".join(f"({0.4 * r:.3f},{y(one(r)):.4f})" for r in range(1, PER_LIST + 1))
    subs = {
        "YS": f"{ys}",
        "BLO": f"{y(both_lo):.4f}", "BHI": f"{y(both_hi):.4f}",
        "LO2": f"{both_lo:.4f}", "HI2": f"{both_hi:.4f}",
        "TOP": f"{y(0.035):.3f}", "MID": f"{y(0.0175):.3f}",
        "YTICKS": "0.01/0.01, 0.02/0.02, 0.03/0.03",
        "CURVE": curve,
        "CLBL": f"{y(one(20)) - 0.45:.3f}",
        "P1": f"{y(one(1)):.4f}", "P30": f"{y(one(PER_LIST)):.4f}",
        "V1": f"{one(1):.4f}", "V30": f"{one(PER_LIST):.4f}",
        "GAPMID": f"{(y(one(1)) + y(both_lo)) / 2:.4f}",
    }
    build("fig-3.2-rrf-curve", subs=subs)


FIGS = [fig_3_1, fig_3_2]

if __name__ == "__main__":
    only = sys.argv[1:]
    for fn in FIGS:
        if not only or any(o in fn.__name__ for o in only):
            fn()
