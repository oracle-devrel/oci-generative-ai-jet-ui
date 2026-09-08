import pytest
from memory.stores.trace import TraceStore


@pytest.mark.asyncio
async def test_trace_write_and_replay(db):
    store = TraceStore(db)
    run_id = "run_test_001"

    await store.write(run_id, "acme", "u1", 0, "user_msg", {"text": "hi"})
    await store.write(run_id, "acme", "u1", 0, "model_msg", {"text": "hello"})
    await store.write(run_id, "acme", "u1", 1, "user_msg", {"text": "more"})

    events = await store.get_run(run_id)
    assert len(events) == 3
    assert events[0]["event_type"] == "user_msg"
    assert events[0]["payload"]["text"] == "hi"
    assert events[2]["turn_index"] == 1
