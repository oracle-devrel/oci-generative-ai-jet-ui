#!/usr/bin/env python3
"""Split the workshop notebooks into editable per-part cell files, and assemble them back.

  python3 .nbwork/nbparts.py split      # notebook_*.ipynb -> .nbwork/parts/<part>/NNNN-<kind>.<ext>
  python3 .nbwork/nbparts.py assemble   # .nbwork/parts -> notebook_complete.ipynb + notebook_student.ipynb

Cell files (sorted by name inside a part; insert new cells with an in-between number, e.g. 0135):
  NNNN-md.md              markdown cell (same in both notebooks)
  NNNN-code.py            code cell (same in both notebooks)
  NNNN-*.student.<ext>    student-only variant of the cell with the same NNNN-<kind> (TODO stubs, banners)
  NNNN-figure.json        figure cell, full nbformat JSON (do not edit)
Assembled notebooks carry no outputs, unless `assemble EXECUTED.ipynb` is given: then each complete-notebook
code cell takes the outputs of the executed cell with the identical source (markdown edits never need a re-run).
"""
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / ".nbwork" / "parts"
COMPLETE = ROOT / "notebook_complete.ipynb"
STUDENT = ROOT / "notebook_student.ipynb"
# first cell index (in the notebooks at split time) of each part
BOUNDS = [("p01_setup", 0), ("p02_memory", 24), ("p03_retrieval", 49), ("p04_tools", 79),
          ("p05_loop", 107), ("p06_capstone", 140)]


def src(cell):
    s = cell["source"]
    return s if isinstance(s, str) else "".join(s)


def split():
    c = json.loads(COMPLETE.read_text())["cells"]
    s = json.loads(STUDENT.read_text())["cells"]
    assert len(c) == len(s)
    for k, (name, start) in enumerate(BOUNDS):
        end = BOUNDS[k + 1][1] if k + 1 < len(BOUNDS) else len(c)
        d = PARTS / name
        d.mkdir(parents=True, exist_ok=True)
        for n, i in enumerate(range(start, end)):
            stem = f"{(n + 1) * 10:04d}"
            cc, sc = c[i], s[i]
            if cc["metadata"].get("jnb_new") and "<figure" in src(cc):
                cell = {k2: v for k2, v in cc.items() if k2 != "id"}
                (d / f"{stem}-figure.json").write_text(json.dumps(cell, indent=1, ensure_ascii=False))
                continue
            kind, ext = ("code", "py") if cc["cell_type"] == "code" else ("md", "md")
            (d / f"{stem}-{kind}.{ext}").write_text(src(cc))
            if src(sc) != src(cc):
                (d / f"{stem}-{kind}.student.{ext}").write_text(src(sc))
    print("split into", PARTS)


def cell_from(path):
    text = path.read_text()
    if path.name.endswith("figure.json"):
        cell = json.loads(text)
    elif ".md" in path.suffixes:
        cell = {"cell_type": "markdown", "metadata": {}, "source": text}
    else:
        cell = {"cell_type": "code", "metadata": {}, "source": text, "outputs": [], "execution_count": None}
    cell["id"] = uuid.uuid5(uuid.NAMESPACE_URL, str(path.relative_to(PARTS))).hex[:12]
    return cell


def executed_outputs(path):
    """source -> list of (outputs, execution_count, metadata) from an executed notebook, in order."""
    table = {}
    for cell in json.loads(Path(path).read_text())["cells"]:
        if cell["cell_type"] == "code":
            table.setdefault(src(cell), []).append(
                (cell.get("outputs", []), cell.get("execution_count"), cell.get("metadata", {})))
    return table


def assemble(outputs_from=None):
    meta = json.loads(COMPLETE.read_text())["metadata"]
    executed = executed_outputs(outputs_from) if outputs_from else {}
    out = {"complete": [], "student": []}
    missing = 0
    for d in sorted(p for p in PARTS.iterdir() if p.is_dir()):
        files = sorted(f for f in d.iterdir() if f.is_file() and ".student." not in f.name)
        for f in files:
            base = cell_from(f)
            variants = list(d.glob(f.name.split(".")[0] + ".student.*"))
            out["student"].append(cell_from(variants[0]) if variants else base)
            if base["cell_type"] == "code" and outputs_from:
                base = dict(base)
                if executed.get(base["source"]):
                    base["outputs"], base["execution_count"], base["metadata"] = executed[base["source"]].pop(0)
                else:
                    missing += 1
            out["complete"].append(base)
    for path, cells in ((COMPLETE, out["complete"]), (STUDENT, out["student"])):
        nb = {"cells": cells, "metadata": meta, "nbformat": 4, "nbformat_minor": 5}
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
        print(path.name, len(cells), "cells")
    if outputs_from:
        print(f"outputs transplanted from {outputs_from}; code cells without a matching executed source: {missing}")


if __name__ == "__main__":
    if sys.argv[1] == "assemble":
        assemble(sys.argv[2] if len(sys.argv) > 2 else None)
    elif sys.argv[1] == "split":
        split()
