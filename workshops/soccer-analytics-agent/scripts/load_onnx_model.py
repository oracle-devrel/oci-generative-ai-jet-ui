#!/usr/bin/env python3
"""Load an Oracle-compatible ONNX embedding model into the soccer schema.

Uses the `onnx2oracle` PyPI package, which builds an augmented ONNX pipeline
with the tokenizer baked into the graph. Oracle AI Database's `VECTOR_EMBEDDING(...)`
expects this exact shape — a vanilla HuggingFace ONNX export fails with
ORA-54426 because its `input_ids` has two variable-size dimensions.

Default preset: `all-MiniLM-L6-v2` (384 dims, registered as `ALL_MINILM_L6_V2`).
Connection comes from `.env`. The `soccer` user needs `CREATE MINING MODEL`
(granted by SYSTEM during the workshop setup).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / ".env")

PRESET = os.environ.get("ORACLE_EMBED_PRESET", "all-MiniLM-L6-v2")


def main() -> int:
    user = os.environ["ORACLE_USER"]
    pw = os.environ["ORACLE_PASSWORD"]
    dsn = os.environ["ORACLE_DSN"]  # host:port/service
    full_dsn = f"{user}/{pw}@{dsn}"

    print(f"Loading {PRESET} into {user}@{dsn} ...")
    result = subprocess.run(
        ["uv", "run", "onnx2oracle", "load", PRESET,
         "--dsn", full_dsn, "--force"],
        cwd=REPO,
    )
    if result.returncode != 0:
        print("onnx2oracle load failed.", file=sys.stderr)
        return result.returncode

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
