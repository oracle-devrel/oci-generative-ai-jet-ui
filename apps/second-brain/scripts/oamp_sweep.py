"""Daily privacy sweep of the OAMP memory store (the default backend).

  ./.venv/bin/python scripts/oamp_sweep.py

Scans EVERY extracted memory against the structural deny patterns in oamp_memory.py
and deletes violators through the package's lifecycle API. The extraction-time prompt
guard filters; this ENFORCES — prompts get partial compliance (proven by
tests/eval_oamp.py probe 2), so the sweep is what makes "never memorize financials"
a guarantee instead of an instruction. sync.py runs this automatically whenever
the resolved backend is oamp (the default); harmless no-op otherwise.
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "oracle" / "agent"))
import db  # noqa: E402


def resolve_memory_backend(env):
    """Mirrors research_agent._resolve_backend: unset -> oamp, except ollama -> custom.
    Parity is enforced by tests/test_brain.py::test_backend_resolution_parity."""
    return (env.get("MEMORY_BACKEND") or (
        "custom" if env.get("LLM_PROVIDER", "anthropic").lower() == "ollama"
        else "oamp")).lower()


def main():
    if resolve_memory_backend(os.environ) != "oamp":
        print("oamp sweep: memory backend is not 'oamp' — nothing to sweep")
        return
    import oamp_memory
    conn = db.connect()
    try:
        removed = oamp_memory.enforce_privacy(conn)   # full scan
        print(f"oamp sweep: scanned all extracted memories, removed {len(removed)}")
        for r in removed:
            print(f"  - removed: {r!r}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
