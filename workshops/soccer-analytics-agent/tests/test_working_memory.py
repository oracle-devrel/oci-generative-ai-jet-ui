import uuid
import pytest
from soccer_agent.memory.working import WorkingMemory


@pytest.mark.integration
def test_set_get_delete(memory_schema_ready):
    s = f"test-{uuid.uuid4()}"
    wm = WorkingMemory(s)
    wm.set("k", {"x": 1})
    assert wm.get("k") == {"x": 1}
    wm.delete("k")
    assert wm.get("k") is None


@pytest.mark.integration
def test_clear_session(memory_schema_ready):
    s = f"test-{uuid.uuid4()}"
    wm = WorkingMemory(s)
    wm.set("a", {"x": 1})
    wm.set("b", {"y": 2})
    wm.clear_session()
    assert wm.get("a") is None and wm.get("b") is None
