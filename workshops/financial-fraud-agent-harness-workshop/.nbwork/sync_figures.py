#!/usr/bin/env python3
"""Regenerate every .nbwork/parts/**/NNNN-figure.json from figures_new/*/manifest.json + the SVGs.

The manifest (caption) and the slice's SVG are the source of truth; the figure number in each
cell picks its manifest entry. `--check` only reports cells whose content would change.
Run: python3 .nbwork/sync_figures.py [--check]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "figures_new"))
import figcell as b  # noqa: E402

PARTS = ROOT / ".nbwork" / "parts"


def entries():
    out = {}
    for mf in sorted((ROOT / "figures_new").glob("*/manifest.json")):
        if mf.parent.name.startswith("_"):
            continue
        for e in json.loads(mf.read_text(encoding="utf-8")):
            svg = (mf.parent / e["svg"]).read_text(encoding="utf-8")
            out[e["number"]] = {**e, "svg_text": svg[svg.find("<svg"):]}
    return out


def alt_text(caption):
    alt = re.sub(r"<[^>]+>", "", caption)
    alt = re.sub(r"\\(?:mathrm|mathbf|text|operatorname)\b", "", alt)
    alt = re.sub(r"\\\$", "USD ", alt)
    alt = re.sub(r"\\[A-Za-z]+", "", alt)
    alt = re.sub(r"[\[\]${}\\\n]", " ", alt)
    return re.sub(r"\s+", " ", alt).strip()


def main(check):
    es, changed = entries(), 0
    for path in sorted(PARTS.glob("*/*-figure.json")):
        cell = json.loads(path.read_text())
        src = cell["source"] if isinstance(cell["source"], str) else "".join(cell["source"])
        number = re.search(r'data-fig="([\d.]+)"', src).group(1)
        e = es[number]
        new = b.figure_cell(e["svg_text"], "", alt_text(e["caption"]), number, b.render(e["caption"]))
        new_src = new["source"]
        if new_src != src:
            changed += 1
            old_cap = re.search(r"<figcaption>(.*)</figcaption>", src, re.S).group(1)
            new_cap = re.search(r"<figcaption>(.*)</figcaption>", new_src, re.S).group(1)
            what = "caption" if old_cap != new_cap else "svg"
            print(f"{path.relative_to(PARTS)}  Figure {number}: {what} differs")
            if check and what == "caption":
                print("   old:", old_cap[:160], "\n   new:", new_cap[:160])
            if not check:
                cell["source"] = new_src
                path.write_text(json.dumps(cell, indent=1, ensure_ascii=False))
    print(f"{changed} figure cell(s) {'would change' if check else 'updated'}")


if __name__ == "__main__":
    main("--check" in sys.argv)
