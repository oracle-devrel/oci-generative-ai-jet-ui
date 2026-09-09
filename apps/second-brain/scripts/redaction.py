"""Shared secret redaction for every chat/transcript loader.

One list, every loader: anything shaped like a credential is replaced with [REDACTED]
BEFORE it reaches the database — so a key once pasted into a chat can never become
searchable content, feed the wiki/memory layers, or ship to the cloud copy.

Usage:  from redaction import redact   (loaders run with scripts/ on sys.path)
"""
import re

SECRET_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9])sk-ant-[A-Za-z0-9_\-]{20,}"),
    # left boundary matters: without it this eats the tail of ordinary hyphenated
    # words ("desk-with-ocean-view" contains sk-with-ocean-view)
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{20,}"),  # OpenAI classic + sk-proj-... keys
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),                 # Google API key
    re.compile(r"ntn_[A-Za-z0-9]{20,}"),                   # Notion
    re.compile(r"secret_[A-Za-z0-9]{20,}"),                # Notion (legacy)
    re.compile(r"AKIA[0-9A-Z]{16}"),                       # AWS access key id
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),             # GitHub tokens
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),          # Slack
    re.compile(r"hf_[A-Za-z0-9]{20,}"),                    # Hugging Face
    re.compile(r"fo1_[A-Za-z0-9_\-]{20,}"),                # Fly.io deploy token
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{30,45}\b"),     # Telegram bot token
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
]


def redact(text):
    for pat in SECRET_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text
