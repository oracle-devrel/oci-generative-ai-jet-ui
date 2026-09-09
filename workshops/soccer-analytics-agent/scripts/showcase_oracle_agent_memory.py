#!/usr/bin/env python3
"""Optional oracleagentmemory PyPI package showcase.

This is intentionally separate from the core agent loop: the workshop keeps its
bespoke memory tables for transparency, and this script demonstrates how the new
Oracle Agent Memory SDK can live in the same database when installed.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent


def main() -> None:
    load_dotenv(REPO / ".env")
    from soccer_agent.memory.oracle_agent_memory import (
        OracleAgentMemoryUnavailable,
        run_demo,
    )

    try:
        result = run_demo()
    except OracleAgentMemoryUnavailable as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Thread: {result.thread_id}")
    print(f"Stored durable memory: {result.stored_memory}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    print("Retrieved memories/messages:")
    for item in result.retrieved:
        print(f"  - {item}")


if __name__ == "__main__":
    main()
