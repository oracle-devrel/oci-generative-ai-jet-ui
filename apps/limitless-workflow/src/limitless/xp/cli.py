from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Iterable

from limitless.settings import Settings
from limitless.xp.active_session import (
    answer_active_session,
    clear_active_session,
    finish_active_session,
    hint_active_session,
    start_active_session,
    status_active_session,
)


class XPSessionRunner:
    def __init__(
        self,
        *,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
        settings: Settings | None = None,
    ) -> None:
        self.input_func = input_func
        self.output_func = output_func
        self.settings = settings or Settings()

    def _print_payload(self, payload: dict) -> None:
        if payload.get("hud"):
            self.output_func(payload["hud"])
        if payload.get("tutor_message"):
            self.output_func(payload["tutor_message"])
        if payload.get("prompt"):
            self.output_func(payload["prompt"])

    def run(self, topic_slug: str, focus_concept_id: str | None = None) -> tuple[str, str]:
        start = start_active_session(topic_slug, focus_concept_id, self.settings)
        self.output_func(f"Session key: {start['session_key']}")
        self.output_func(f"Transcript path: {start['transcript_path']}")
        self._print_payload(start)

        while True:
            user_input = self.input_func("> ").strip()
            if not user_input:
                continue

            command = user_input.lower()
            if command == "/status":
                payload = status_active_session()
                self._print_payload(payload)
                continue
            if command == "/hint":
                payload = hint_active_session(self.settings)
                self._print_payload(payload)
                continue
            if command == "/finish":
                payload = finish_active_session(self.settings)
                self.output_func("Session finished.")
                return payload["session_key"], payload.get("transcript_path", "")
            if command == "/quit":
                payload = finish_active_session(self.settings)
                self.output_func("Session stopped.")
                return payload["session_key"], payload.get("transcript_path", "")

            payload = answer_active_session(user_input, self.settings)
            self._print_payload(payload)
            if payload.get("finished"):
                return payload["session_key"], payload.get("transcript_path", "")


def parse_command(raw: str) -> str | None:
    normalized = raw.strip().lower()
    return normalized if normalized in {"/status", "/hint", "/finish", "/quit"} else None


def run_scripted_session(
    topic_slug: str,
    inputs: Iterable[str],
    *,
    focus_concept_id: str | None = None,
    output_dir: str | Path = "content/transcripts",
) -> tuple[object, Path, list[str]]:
    iterator = iter(inputs)
    outputs: list[str] = []

    runner = XPSessionRunner(
        input_func=lambda prompt='': next(iterator),
        output_func=outputs.append,
        settings=Settings(
            _env_file=None,
            ORACLE_DSN="dummy",
            ORACLE_USER="dummy",
            ORACLE_PASSWORD="dummy",
            OBSIDIAN_VAULT_PATH="Limitless",
        ),
    )
    # Backward-compatible helper for tests that expect transcript output
    import limitless.xp.active_session as active
    import limitless.xp.turn_engine as te

    original_active_path = active.ACTIVE_SESSION_PATH
    original_state_dir = te.SESSION_STATE_DIR
    original_save_transcript = te.save_transcript_json
    original_create = te.create_db_session
    original_persist = te.persist_turn
    original_finalize = te.finalize_session

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    active.ACTIVE_SESSION_PATH = output_dir / "active_session.json"
    te.SESSION_STATE_DIR = output_dir / "state"

    def _save_transcript(state, out='content/transcripts'):
        path = output_dir / f"{state.session_key}.json"
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return path

    te.save_transcript_json = _save_transcript
    te.create_db_session = lambda state, settings=None: None
    te.persist_turn = lambda state, turn, settings=None: None
    te.finalize_session = lambda state, status, settings=None: None

    try:
        session_key, transcript_path = runner.run(topic_slug, focus_concept_id)
        from limitless.xp.turn_engine import load_session_state
        state = load_session_state(session_key)
        return state, Path(transcript_path), outputs
    finally:
        active.ACTIVE_SESSION_PATH = original_active_path
        te.SESSION_STATE_DIR = original_state_dir
        te.save_transcript_json = original_save_transcript
        te.create_db_session = original_create
        te.persist_turn = original_persist
        te.finalize_session = original_finalize
        clear_active_session()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the interactive Limitless XP Builder session.")
    parser.add_argument("--topic", required=True, help="Topic slug, e.g. agent-memory")
    parser.add_argument("--focus", default=None, help="Optional concept slug to prioritize")
    args = parser.parse_args(argv)

    clear_active_session()
    runner = XPSessionRunner(settings=Settings())
    session_key, transcript_path = runner.run(args.topic, focus_concept_id=args.focus)
    print(f"Transcript saved: {transcript_path}")
    print(f"Session key: {session_key}")
    return 0
