from agent_reasoning.visualization.models import StreamEvent, TaskStatus, TreeNode


def test_stream_event_to_dict_text():
    event = StreamEvent(event_type="text", data="hello world")
    d = event.to_dict()
    assert d == {"event_type": "text", "data": "hello world", "is_update": False}


def test_stream_event_to_dict_dataclass():
    node = TreeNode(id="root", content="test", score=0.85, depth=0)
    event = StreamEvent(event_type="node", data=node)
    d = event.to_dict()
    assert d["event_type"] == "node"
    assert d["data"]["id"] == "root"
    assert d["data"]["score"] == 0.85


def test_stream_event_to_dict_with_enum():
    """TaskStatus enum values should serialize to strings."""
    from agent_reasoning.visualization.models import SubTask

    task = SubTask(id=1, description="test", status=TaskStatus.RUNNING, result="")
    event = StreamEvent(event_type="task", data=task)
    d = event.to_dict()
    assert d["data"]["status"] == "running" or d["data"]["status"] == TaskStatus.RUNNING.value


def test_stream_event_to_dict_is_update():
    event = StreamEvent(event_type="text", data="update", is_update=True)
    d = event.to_dict()
    assert d["is_update"] is True
