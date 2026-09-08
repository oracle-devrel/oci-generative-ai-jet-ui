from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from limitless.obsidian.generator import refresh_obsidian_projection
from limitless.settings import Settings


def main() -> int:
    written = refresh_obsidian_projection(Settings())
    print("Refreshed Obsidian projection:")
    for path in written:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
