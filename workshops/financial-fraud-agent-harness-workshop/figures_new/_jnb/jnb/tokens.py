"""Design tokens: single source of truth lives in ``assets/tokens.json``."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

# skill: <skill>/assets ; vendored: <project>/_jnb/assets
_HERE = Path(__file__).resolve().parent
ASSETS = _HERE.parent / "assets" if (_HERE.parent / "assets").is_dir() else _HERE.parent.parent / "assets"


@lru_cache(maxsize=1)
def load_tokens() -> dict:
    with open(ASSETS / "tokens.json", encoding="utf-8") as f:
        return json.load(f)


def color(name: str) -> str:
    """Resolve a colour: ``'input'`` (roles shorthand) or a dotted path such as
    ``'greys.cuboid_top'``, ``'surface.bg'``, ``'text.muted'``."""
    t = load_tokens()
    if "." not in name:
        for group in ("roles", "text", "surface", "greys"):
            if name in t.get(group, {}):
                return t[group][name]
        raise KeyError(f"unknown colour token: {name!r}")
    node = t
    for part in name.split("."):
        node = node[part]
    if not isinstance(node, str):
        raise KeyError(f"{name!r} is not a colour")
    return node
