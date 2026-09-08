"""Content normalization and hashing for the dedup primitive."""
from __future__ import annotations
import hashlib
import re

_WHITESPACE = re.compile(r"\s+")
_TRAILING_PUNCT = re.compile(r"[.!?]+$")


def normalize(text: str) -> str:
    """Normalize content for dedup hashing.

    Lowercase, collapse whitespace, strip trailing sentence punctuation.
    Trade-off: aggressive normalization → more dedup hits, more false
    positives.
    """
    text = _WHITESPACE.sub(" ", text).strip().lower()
    text = _TRAILING_PUNCT.sub("", text)
    return text


def content_hash(text: str) -> str:
    """SHA-256 of normalized content. Used as the dedup primitive
    in PromotionGate alongside the scope tuple."""
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()
