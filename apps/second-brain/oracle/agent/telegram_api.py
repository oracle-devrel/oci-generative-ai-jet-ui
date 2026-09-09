"""Minimal Telegram Bot API helper — push a message out, and (for a DEDICATED bot) read
messages in. Runs headlessly from a launchd job, where the interactive Telegram tool isn't
available.

PUSH (send): zero-setup — if a Claude Code Telegram channel is already configured on this
machine (`~/.claude/channels/telegram/{.env,access.json}`), reuse THAT bot + the allow-listed
chat. Override via env (keychain-aware): TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.

DRAIN (read via getUpdates): use a SEPARATE, dedicated bot token — never the channel bot.
getUpdates consumes each update for exactly one reader, so a drain on the channel bot would
steal messages from your live Claude sessions (and vice versa). A dedicated backlog bot has
no such conflict. Pass its token explicitly to get_updates()/send_message(token=...).

Absent everywhere -> `configured()` is False and callers skip gracefully.
"""
import json
import pathlib
import urllib.parse
import urllib.request

from keychain_secrets import getenv

_CHANNEL = pathlib.Path.home() / ".claude" / "channels" / "telegram"


def _token():
    t = getenv("TELEGRAM_BOT_TOKEN")
    if t:
        return t
    envp = _CHANNEL / ".env"
    if envp.exists():
        for line in envp.read_text().splitlines():
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


def _chat_id():
    c = getenv("TELEGRAM_CHAT_ID")
    if c:
        return str(c)
    aj = _CHANNEL / "access.json"
    if aj.exists():
        try:
            af = json.load(open(aj)).get("allowFrom") or []
            if af:
                return str(af[0])
        except Exception:
            pass
    return None


def configured() -> bool:
    return bool(_token() and _chat_id())


def send_message(text: str, token: str | None = None, chat_id: str | None = None) -> dict:
    """Send a message. Default (no token) uses the push/channel bot + allow-listed chat;
    pass token+chat_id explicitly to reply from a dedicated bot."""
    tok = token or _token()
    cid = chat_id or _chat_id()
    if not (tok and cid):
        raise RuntimeError("telegram not configured (no token / chat id)")
    data = urllib.parse.urlencode(
        {"chat_id": cid, "text": text, "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{tok}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read())
    if not out.get("ok"):
        raise RuntimeError(f"telegram sendMessage failed: {out.get('description', '?')}")
    return out


def get_updates(token: str, offset: int | None = None) -> list:
    """Poll a DEDICATED bot for new messages (getUpdates, non-blocking). `offset` is the
    next update_id to fetch (last seen + 1) — Telegram then also acks everything before it."""
    q = {"timeout": 0}
    if offset is not None:
        q["offset"] = offset
    url = f"https://api.telegram.org/bot{token}/getUpdates?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=35) as r:
        out = json.loads(r.read())
    if not out.get("ok"):
        raise RuntimeError(f"telegram getUpdates failed: {out.get('description', '?')}")
    return out.get("result", [])


def parse_updates(updates: list, allow_chat_id: str | None = None) -> list:
    """Pure: raw getUpdates result -> [{update_id, ts, text, chat_id}] for real text messages,
    chronological. When `allow_chat_id` is set, keep ONLY that chat (so a stray sender to the
    bot can't inject into the backlog — the same allowlist idea as the channel plugin)."""
    out = []
    for u in updates or []:
        if not isinstance(u, dict):
            continue
        msg = u.get("message") or u.get("edited_message") or {}
        text = (msg.get("text") or "").strip()
        uid = u.get("update_id")
        chat = str((msg.get("chat") or {}).get("id", ""))
        if not text or uid is None or not chat:
            continue
        if allow_chat_id and chat != str(allow_chat_id):
            continue
        out.append({"update_id": uid, "ts": msg.get("date"), "text": text, "chat_id": chat})
    out.sort(key=lambda x: x["update_id"])
    return out
