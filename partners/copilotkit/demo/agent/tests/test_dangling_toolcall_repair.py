"""A client-side HITL tool (book_flight) abandoned mid-confirm leaves an assistant
message with a tool_call and no following tool result. OpenAI 400s on the next turn
("tool_call_ids did not have response messages"). _repair_dangling_tool_calls
synthesizes a 'not completed' tool result so the history is valid and the model can
move on. Reproduces the crash a user hit on the live demo (conversational booking
then a new message before clicking Confirm/Cancel).
"""

from __future__ import annotations

from concierge.server import _repair_dangling_tool_calls


def _assistant_call(call_id: str, name: str = "book_flight") -> dict:
    return {
        "id": "a1",
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": call_id, "type": "function", "function": {"name": name, "arguments": "{}"}}
        ],
    }


def _dangling_ids(messages: list[dict]) -> set[str]:
    answered = {m.get("tool_call_id") for m in messages if m.get("role") == "tool"}
    calls = {
        tc["id"]
        for m in messages
        if m.get("role") == "assistant"
        for tc in (m.get("tool_calls") or [])
    }
    return calls - answered


def _every_assistant_call_followed_by_tool(messages: list[dict]) -> bool:
    """OpenAI's real rule is positional: an assistant tool_calls message must be
    immediately followed by tool result message(s). _dangling_ids is set-based and
    can't see this, so the position-sensitive bugs need this stricter oracle."""
    for i, m in enumerate(messages):
        if m.get("role") == "assistant" and m.get("tool_calls"):
            nxt = messages[i + 1] if i + 1 < len(messages) else None
            if not (nxt and nxt.get("role") == "tool"):
                return False
    return True


def test_synthesizes_result_for_dangling_call():
    msgs = [
        {"id": "u1", "role": "user", "content": "book it"},
        _assistant_call("call_X"),
        {"id": "u2", "role": "user", "content": "what do you remember about me?"},
    ]
    out = _repair_dangling_tool_calls(msgs)
    assert not _dangling_ids(out), "every tool_call must have a response after repair"
    synth = [m for m in out if m.get("role") == "tool" and m.get("tool_call_id") == "call_X"]
    assert len(synth) == 1
    # inserted directly after the assistant message that made the call
    assistant_idx = next(i for i, m in enumerate(out) if m.get("tool_calls"))
    assert out[assistant_idx + 1] is synth[0]


def test_leaves_answered_call_untouched():
    msgs = [
        _assistant_call("call_Y"),
        {"id": "t1", "role": "tool", "content": "Booked!", "tool_call_id": "call_Y"},
    ]
    assert _repair_dangling_tool_calls(msgs) == msgs


def test_mixed_answered_and_dangling():
    msgs = [
        {
            "id": "a1",
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "call_A", "type": "function", "function": {"name": "search_flights", "arguments": "{}"}},
                {"id": "call_B", "type": "function", "function": {"name": "book_flight", "arguments": "{}"}},
            ],
        },
        {"id": "t1", "role": "tool", "content": "results", "tool_call_id": "call_A"},
    ]
    out = _repair_dangling_tool_calls(msgs)
    assert not _dangling_ids(out)
    assert _every_assistant_call_followed_by_tool(out)  # positional, not just set-based
    synth = [m for m in out if m.get("role") == "tool" and m.get("tool_call_id") == "call_B"]
    assert len(synth) == 1 and "book_flight" in synth[0]["content"]


def test_dangling_call_as_trailing_message():
    # The abandoned book_flight call can be the LAST message (history re-sent before
    # the next user delta is appended) — the synth must still be inserted after it.
    msgs = [
        {"id": "u1", "role": "user", "content": "book it"},
        _assistant_call("call_Z"),
    ]
    out = _repair_dangling_tool_calls(msgs)
    assert _every_assistant_call_followed_by_tool(out)
    assert out[-1]["role"] == "tool" and out[-1]["tool_call_id"] == "call_Z"


def test_same_unanswered_id_on_two_assistant_messages():
    # The bad `answered.add` guard left the SECOND occurrence dangling. Both
    # assistant messages must end up followed by a tool result.
    msgs = [
        _assistant_call("dup"),
        {"id": "u1", "role": "user", "content": "wait"},
        _assistant_call("dup"),
        {"id": "u2", "role": "user", "content": "what do you remember?"},
    ]
    out = _repair_dangling_tool_calls(msgs)
    assert _every_assistant_call_followed_by_tool(out), "both occurrences must be repaired"


def test_no_tool_calls_unchanged():
    msgs = [
        {"id": "u1", "role": "user", "content": "hi"},
        {"id": "a1", "role": "assistant", "content": "hello"},
    ]
    assert _repair_dangling_tool_calls(msgs) == msgs
