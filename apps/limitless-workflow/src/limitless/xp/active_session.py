from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from limitless.settings import Settings
from limitless.xp.turn_engine import answer_session, finish_session, hint_session, start_session, status_session


ACTIVE_SESSION_PATH = Path("content/session_state/active_session.json")


def _ensure_parent() -> None:
    ACTIVE_SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)


def set_active_session(session_key: str, topic_slug: str) -> Path:
    _ensure_parent()
    ACTIVE_SESSION_PATH.write_text(
        json.dumps({"session_key": session_key, "topic_slug": topic_slug}, indent=2),
        encoding="utf-8",
    )
    return ACTIVE_SESSION_PATH


def get_active_session() -> dict[str, str]:
    if not ACTIVE_SESSION_PATH.exists():
        raise FileNotFoundError("No active XP session found.")
    data = json.loads(ACTIVE_SESSION_PATH.read_text(encoding="utf-8"))
    return {"session_key": data["session_key"], "topic_slug": data["topic_slug"]}


def clear_active_session() -> None:
    if ACTIVE_SESSION_PATH.exists():
        ACTIVE_SESSION_PATH.unlink()


def start_active_session(topic_slug: str, focus_concept_id: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    payload = start_session(topic_slug, focus_concept_id, settings)
    set_active_session(payload["session_key"], topic_slug)
    payload["active_session_path"] = str(ACTIVE_SESSION_PATH)
    return payload


def answer_active_session(answer: str, settings: Settings | None = None) -> dict[str, Any]:
    active = get_active_session()
    payload = answer_session(active["session_key"], answer, settings)
    payload["active_session_path"] = str(ACTIVE_SESSION_PATH)
    return payload


def hint_active_session(settings: Settings | None = None) -> dict[str, Any]:
    active = get_active_session()
    payload = hint_session(active["session_key"], settings)
    payload["active_session_path"] = str(ACTIVE_SESSION_PATH)
    return payload


def status_active_session() -> dict[str, Any]:
    active = get_active_session()
    payload = status_session(active["session_key"])
    payload["active_session_path"] = str(ACTIVE_SESSION_PATH)
    return payload


def finish_active_session(settings: Settings | None = None) -> dict[str, Any]:
    active = get_active_session()
    payload = finish_session(active["session_key"], settings)
    clear_active_session()
    payload["active_session_path"] = str(ACTIVE_SESSION_PATH)
    return payload
