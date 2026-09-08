"""AgentSession envelope: who is asking (tenant/user/agent), in which
run + turn, plus ephemeral scratch state that lives only for the run."""
from __future__ import annotations
import secrets
from dataclasses import dataclass, field
from typing import Any


def _make_run_id() -> str:
    return f"run_{secrets.token_hex(4)}"


@dataclass
class AgentSession:
    """Scope columns (tenant_id, user_id, agent_id), the run/turn
    identifiers that bind trace entries together, and scratch/turn_buffer
    for in-run working state that does not survive the run.
    """
    tenant_id: str
    user_id: str
    agent_id: str
    run_id: str = field(default_factory=_make_run_id)
    turn_index: int = 0
    scratch: dict[str, Any] = field(default_factory=dict)
    turn_buffer: list[Any] = field(default_factory=list)

    def advance_turn(self) -> None:
        self.turn_index += 1

    def new_run(self) -> None:
        self.run_id = _make_run_id()
        self.turn_index = 0
        self.scratch.clear()
        self.turn_buffer.clear()
