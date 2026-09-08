from __future__ import annotations

import subprocess
import sys

COMMANDS = [
    [sys.executable, "scripts/check_oracle_connection.py"],
    [sys.executable, "scripts/load_topics.py"],
    [sys.executable, "scripts/demo_smoke.py"],
]


def main() -> int:
    for command in COMMANDS:
        print(f"RUNNING: {' '.join(command)}")
        completed = subprocess.run(command)
        if completed.returncode != 0:
            print(f"FAILED: {' '.join(command)}")
            return completed.returncode
    print("Workshop bootstrap complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
