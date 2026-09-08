from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from limitless.frameworks.builder import write_framework_note
from limitless.settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a grounded Limitless framework note.")
    parser.add_argument("--topic", required=True, help="Topic slug, e.g. agent-memory")
    args = parser.parse_args(argv)

    path = write_framework_note(args.topic, settings=Settings())
    print(f"Framework note written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
