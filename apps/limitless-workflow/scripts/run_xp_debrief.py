from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from limitless.debrief.service import build_cli_summary, find_latest_transcript, run_debrief
from limitless.settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Limitless XP Debrief.")
    parser.add_argument("--topic", required=True, help="Topic slug, e.g. agent-memory")
    parser.add_argument("--transcript", default=None, help="Optional transcript path")
    parser.add_argument("--latest", action="store_true", help="Use the latest transcript for the topic")
    args = parser.parse_args(argv)

    settings = Settings()
    transcript_path = args.transcript
    if transcript_path is None and args.latest:
        transcript_path = find_latest_transcript(args.topic, settings=settings)
    if transcript_path is not None:
        print(f"Debriefing transcript: {transcript_path}")

    result = run_debrief(
        topic_slug=args.topic,
        transcript_path=transcript_path,
        latest=args.latest,
        settings=settings,
    )
    print(build_cli_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
