from abc import ABC, abstractmethod

from termcolor import colored

from agent_reasoning.client import OllamaClient


class BaseAgent(ABC):
    def __init__(self, model="gemma3:latest", base_url=None, **kwargs):
        self.client = OllamaClient(model=model, base_url=base_url)
        self.name = "BaseAgent"
        self.color = "white"
        self._debug_event = kwargs.get("_debug_event", None)
        self._debug_cancelled = False
        self.max_calls = kwargs.get("max_calls", None)
        self._call_count = 0

    def _debug_pause(self):
        """If in debug mode, pause until signaled."""
        if self._debug_event is not None and not self._debug_cancelled:
            self._debug_event.wait()
            self._debug_event.clear()

    def _validate_query(self, query):
        """Validate and normalize a query input.

        Raises ValueError if query is None. Converts non-string inputs to string.
        Returns the validated query string.
        """
        if query is None:
            raise ValueError("Query must not be None")
        if not isinstance(query, str):
            query = str(query)
        return query

    def _check_budget(self) -> bool:
        """Check if we're within call budget. Returns True if OK to proceed."""
        if not hasattr(self, "_call_count"):
            self._call_count = 0
        if not hasattr(self, "max_calls"):
            self.max_calls = None
        self._call_count += 1
        if self.max_calls is not None and self._call_count > self.max_calls:
            return False
        return True

    @property
    def _budget_exceeded_msg(self) -> str:
        return f"[Budget exceeded: {self._call_count}/{self.max_calls} LLM calls]"

    def log_thought(self, message):
        print(colored(f"[{self.name}]: {message}", self.color))

    @abstractmethod
    def run(self, query):
        pass

    def stream(self, query):
        """
        Default generator that yields chunks.
        Subclasses should implement this or run() to support streaming.
        If only run() is implemented, this wrapper yields the final result as one chunk.
        """
        result = self.run(query)
        if result:
            yield result
