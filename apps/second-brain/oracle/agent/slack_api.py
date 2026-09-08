"""Minimal Slack Web API helper — post a message, read a channel, react. Generic and
personal-data-free: channel IDs and message content live in the caller, never here.

Token from SLACK_BOT_TOKEN (may be `keychain:slack-bot-token`, resolved per call). When
it's absent, `configured()` is False and callers skip gracefully — the repo's
token-absent-is-fine pattern (same as IG_ACCESS_TOKEN / APIFY_TOKEN).

Bot scopes needed: chat:write, channels:history, channels:read, reactions:write (use the
groups:* variants for private channels). Everything speaks x-www-form-urlencoded, which
every Slack Web API method accepts — no per-method content-type surprises.
"""
import urllib.parse
import urllib.request
import json

from keychain_secrets import getenv

API = "https://slack.com/api/"


def configured() -> bool:
    return bool(getenv("SLACK_BOT_TOKEN"))


def _call(method: str, params: dict) -> dict:
    token = getenv("SLACK_BOT_TOKEN")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN not configured")
    data = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}).encode()
    req = urllib.request.Request(
        API + method, data=data,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read())
    if not out.get("ok"):
        raise RuntimeError(f"slack {method} failed: {out.get('error', 'unknown')}")
    return out


def post_message(channel: str, text: str) -> dict:
    """Post plain text to a channel or a DM (channel may be a channel ID or a user ID)."""
    return _call("chat.postMessage",
                 {"channel": channel, "text": text, "unfurl_links": "false",
                  "unfurl_media": "false"})


def history(channel: str, oldest: str | None = None, limit: int = 200) -> list:
    """Raw messages in a channel, newest-first, after the `oldest` ts (exclusive-ish)."""
    return _call("conversations.history",
                 {"channel": channel, "oldest": oldest, "limit": limit,
                  "inclusive": "false"}).get("messages", [])


def add_reaction(channel: str, ts: str, name: str = "white_check_mark"):
    """React to a message; a duplicate reaction is not an error."""
    try:
        return _call("reactions.add", {"channel": channel, "timestamp": ts, "name": name})
    except RuntimeError as e:
        if "already_reacted" in str(e):
            return None
        raise


def human_messages(messages: list) -> list:
    """Pure: keep only real user messages (drop bot posts, joins, edits, thread noise),
    return them CHRONOLOGICAL (oldest first) with just {ts, text}. So a brain-dump channel
    drains in the order things were typed, and the bot never re-ingests its own posts."""
    out = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        if m.get("type") != "message" or m.get("subtype") or m.get("bot_id"):
            continue
        text = (m.get("text") or "").strip()
        ts = m.get("ts")
        if not text or not ts:
            continue
        out.append({"ts": ts, "text": text})
    out.sort(key=lambda x: float(x["ts"]))
    return out
