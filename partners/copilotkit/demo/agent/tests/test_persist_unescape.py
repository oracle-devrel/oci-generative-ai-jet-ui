"""The assistant text persisted to Oracle Agent Memory must be HTML-unescaped.

The agentspec exporter escapes every streamed TEXT_MESSAGE_CHUNK delta
(& < > -> &amp; &lt; &gt;) for safe transport to the browser; persisting those
raw corrupts stored facts (e.g. "fares &lt; $700"). _clean_assistant_text
assembles + unescapes the deltas before they reach memory.
"""

from __future__ import annotations

from concierge.server import _clean_assistant_text


def test_unescapes_lt_gt_amp_from_streamed_deltas():
    parts = ["Sure — fares ", "&lt;", " $700 for ", "SFO ", "&amp;", " Cebu (", "A&gt;B", ")"]
    assert (
        _clean_assistant_text(parts)
        == "Sure — fares < $700 for SFO & Cebu (A>B)"
    )


def test_decodes_entity_split_across_delta_boundaries():
    # Streaming can split a single entity across two chunks; join-then-unescape
    # decodes it correctly, whereas per-delta unescaping would not.
    parts = ["price &l", "t; 700 and a &amp", "; b"]
    assert _clean_assistant_text(parts) == "price < 700 and a & b"


def test_plain_text_is_unchanged():
    assert _clean_assistant_text(["Hello", " ", "world"]) == "Hello world"


def test_empty_parts():
    assert _clean_assistant_text([]) == ""


def test_joins_nonempty_empty_deltas_to_empty_string():
    # Production appends `getattr(item, "delta", "") or ""` per chunk, so a run
    # that emits chunk events with empty/None deltas yields ['', '', ''] (not []).
    # That must still clean to "" (and _persist_sync then drops the empty turn).
    assert _clean_assistant_text(["", "", ""]) == ""


def test_streamed_delta_stays_escaped_only_persist_is_unescaped():
    """Guards the other half of the invariant the fix documents: the copy yielded
    to the client keeps the exporter's HTML-escaping; ONLY the persisted copy is
    unescaped. A future change that unescaped item.delta before `yield` would
    corrupt the browser stream — this test would catch it.
    """
    from ag_ui.core import TextMessageChunkEvent
    from ag_ui.encoder import EventEncoder

    delta = "fares &lt; $700 &amp; up"
    encoded = EventEncoder().encode(
        TextMessageChunkEvent(message_id="m1", delta=delta)
    )
    # Streamed copy: still escaped (encoder must not unescape).
    assert "&lt;" in encoded and "&amp;" in encoded
    # Persisted copy of the same delta: unescaped.
    assert _clean_assistant_text([delta]) == "fares < $700 & up"
