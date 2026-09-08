"""Tests for DecomposedAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent():
    """Create a DecomposedAgent with mocked internals."""
    with patch("agent_reasoning.agents.decomposed.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.decomposed import DecomposedAgent

        agent = DecomposedAgent.__new__(DecomposedAgent)
        agent.name = "DecomposedAgent"
        agent.color = "red"
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.client = MagicMock()
        return agent


def _setup_mock_generate(
    agent,
    decomposition="1. First task\n2. Second task",
    solution="Solution text",
    synthesis="Final synthesis",
):
    """Configure mock generate for the decomposition -> solve -> synthesize pattern."""
    call_count = [0]

    def mock_generate(prompt, **kwargs):
        call_count[0] += 1
        # Order matters: synthesis prompt contains "Original Query" AND "Completed Sub-tasks"
        # while decomposition prompt contains "Break down" and "sub-tasks"
        if "Original Query" in prompt and "Completed Sub-tasks" in prompt:
            return iter([synthesis])
        elif "Break down" in prompt:
            return iter([decomposition])
        else:
            return iter([solution])

    agent.client.generate = MagicMock(side_effect=mock_generate)
    return call_count


def test_decomposed_emits_task_events():
    """DecomposedAgent should emit task events for each sub-task."""
    agent = _make_agent()
    _setup_mock_generate(agent)

    events = list(agent.stream_structured("Explain quantum computing"))
    task_events = [e for e in events if e.event_type == "task"]
    assert len(task_events) > 0

    # Should have tasks for each line in the decomposition
    non_update_tasks = [e for e in task_events if not e.is_update]
    assert len(non_update_tasks) >= 2  # At least 2 tasks from "1. First task\n2. Second task"


def test_decomposed_tasks_go_through_lifecycle():
    """Each sub-task should transition through PENDING -> RUNNING -> COMPLETED.

    Note: SubTask objects are mutated in place, so we can't check historical
    statuses from event snapshots. Instead we verify the sequence of event
    emissions (initial non-update = PENDING, then update events during RUNNING,
    final update = COMPLETED) and check the final state.
    """
    agent = _make_agent()
    _setup_mock_generate(agent)

    from agent_reasoning.visualization.models import TaskStatus

    events = list(agent.stream_structured("test"))
    task_events = [e for e in events if e.event_type == "task"]

    # Group events by task id
    tasks_by_id = {}
    for e in task_events:
        tid = e.data.id
        if tid not in tasks_by_id:
            tasks_by_id[tid] = []
        tasks_by_id[tid].append(e)

    assert len(tasks_by_id) >= 2, "Should have at least 2 sub-tasks"

    for tid, task_evts in tasks_by_id.items():
        # First event for each task should be non-update (initial PENDING emission)
        assert not task_evts[0].is_update, f"Task {tid} first event should be non-update (initial)"

        # Should have update events (RUNNING + COMPLETED phases)
        updates = [e for e in task_evts if e.is_update]
        assert len(updates) >= 2, f"Task {tid} should have update events for RUNNING and COMPLETED"

        # Final state should be COMPLETED (object is mutated to final state)
        assert task_evts[-1].data.status == TaskStatus.COMPLETED, f"Task {tid} should end COMPLETED"
        assert task_evts[-1].data.progress == 1.0, f"Task {tid} should have 100% progress"


def test_decomposed_emits_final_event():
    """DecomposedAgent should emit a final event with the synthesis."""
    agent = _make_agent()
    _setup_mock_generate(agent, synthesis="The comprehensive answer")

    events = list(agent.stream_structured("test"))
    final_events = [e for e in events if e.event_type == "final"]
    assert len(final_events) == 1
    assert isinstance(final_events[0].data, str)
    assert "comprehensive answer" in final_events[0].data.lower()


def test_decomposed_stream_yields_text():
    """DecomposedAgent.stream() should yield text strings."""
    agent = _make_agent()
    _setup_mock_generate(agent)

    chunks = list(agent.stream("test"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_decomposed_run_returns_string():
    """DecomposedAgent.run() should return a non-empty string."""
    agent = _make_agent()
    _setup_mock_generate(agent)

    result = agent.run("test query")
    assert isinstance(result, str)
    assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
