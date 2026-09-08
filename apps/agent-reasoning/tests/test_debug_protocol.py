import threading


def test_debug_event_pauses():
    """_debug_pause blocks until event is set."""
    event = threading.Event()

    class MockAgent:
        def __init__(self):
            self._debug_event = event
            self._debug_cancelled = False

        def _debug_pause(self):
            if self._debug_event is not None and not self._debug_cancelled:
                self._debug_event.wait()
                self._debug_event.clear()

    agent = MockAgent()
    paused = threading.Event()
    resumed = threading.Event()

    def worker():
        paused.set()
        agent._debug_pause()
        resumed.set()

    t = threading.Thread(target=worker)
    t.start()

    paused.wait(timeout=1)
    assert not resumed.is_set(), "Should be paused"

    event.set()
    resumed.wait(timeout=1)
    assert resumed.is_set(), "Should have resumed"
    t.join(timeout=1)


def test_debug_cancel_unblocks():
    """Setting _debug_cancelled should let pause return immediately."""
    event = threading.Event()

    class MockAgent:
        def __init__(self):
            self._debug_event = event
            self._debug_cancelled = False

        def _debug_pause(self):
            if self._debug_event is not None and not self._debug_cancelled:
                self._debug_event.wait()
                self._debug_event.clear()

    agent = MockAgent()
    agent._debug_cancelled = True
    # Should not block since cancelled
    agent._debug_pause()  # no assertion needed, just shouldn't hang


def test_no_debug_event_is_noop():
    """Without _debug_event, _debug_pause is a no-op."""

    class MockAgent:
        def __init__(self):
            self._debug_event = None
            self._debug_cancelled = False

        def _debug_pause(self):
            if self._debug_event is not None and not self._debug_cancelled:
                self._debug_event.wait()
                self._debug_event.clear()

    agent = MockAgent()
    agent._debug_pause()  # Should not block


def test_base_agent_has_debug_hook():
    """BaseAgent accepts _debug_event kwarg and stores it."""
    from agent_reasoning.agents.base import BaseAgent

    class ConcreteAgent(BaseAgent):
        def run(self, query):
            return "result"

    event = threading.Event()
    agent = ConcreteAgent(model="gemma3:latest", _debug_event=event)
    assert agent._debug_event is event
    assert agent._debug_cancelled is False


def test_base_agent_debug_pause_noop_without_event():
    """BaseAgent._debug_pause does nothing when _debug_event is None."""
    from agent_reasoning.agents.base import BaseAgent

    class ConcreteAgent(BaseAgent):
        def run(self, query):
            return "result"

    agent = ConcreteAgent(model="gemma3:latest")
    assert agent._debug_event is None
    agent._debug_pause()  # should not block


def test_base_agent_debug_pause_blocks_and_resumes():
    """BaseAgent._debug_pause blocks until the event is set."""
    from agent_reasoning.agents.base import BaseAgent

    class ConcreteAgent(BaseAgent):
        def run(self, query):
            return "result"

    event = threading.Event()
    agent = ConcreteAgent(model="gemma3:latest", _debug_event=event)

    paused = threading.Event()
    resumed = threading.Event()

    def worker():
        paused.set()
        agent._debug_pause()
        resumed.set()

    t = threading.Thread(target=worker)
    t.start()

    paused.wait(timeout=1)
    assert not resumed.is_set(), "Agent should be paused"

    event.set()
    resumed.wait(timeout=1)
    assert resumed.is_set(), "Agent should have resumed after event.set()"
    t.join(timeout=1)
