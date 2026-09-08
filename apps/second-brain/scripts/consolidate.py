"""Standalone entrypoint: re-consolidate the agent's episodic memory into semantic facts.

Used by the scheduled (daily) LaunchAgent so the learned facts stay fresh even between agent
sessions. Loads oracle/.env explicitly so it works from any cwd (e.g. launchd).

  python scripts/consolidate.py
"""
import datetime
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "oracle" / "agent"))

from dotenv import load_dotenv
load_dotenv(ROOT / "oracle" / ".env")   # cloud creds + ANTHROPIC_API_KEY + wallet, abs path

import anthropic   # noqa: E402
import db          # noqa: E402
from semantic_memory import consolidate   # noqa: E402


def main():
    facts = consolidate(anthropic.Anthropic(), db.connect())
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] consolidated {len(facts)} semantic facts")


if __name__ == "__main__":
    main()
