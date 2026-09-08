"""Build the multi-agent supervisor + 2 specialists.

Compiles once on first request and is cached for the lifetime of the
process. Same wiring as the workshop notebook (Part 10).
"""

from __future__ import annotations

from app.backend.agent.tools import (
    get_planner_policy,
    get_user_memory,
    search_demand_reports,
)
from app.backend.config import LLM_MODEL, chat_model_kwargs
from app.backend.db.connections import saver_connection
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph_oracledb.checkpoint.oracle import AsyncOracleSaver
from langgraph_supervisor import create_supervisor

_supervisor = None
_saver: AsyncOracleSaver | None = None


async def _get_saver() -> AsyncOracleSaver:
    global _saver
    if _saver is None:
        conn = await saver_connection()
        _saver = AsyncOracleSaver(conn)
        await _saver.setup()
    return _saver


async def get_supervisor():
    """Return the compiled multi-agent supervisor.

    The compiled graph is keyed by a global module-level cache. Re-invoke
    with the same `thread_id` to resume; pass a fresh `thread_id` to
    start clean.
    """
    global _supervisor
    if _supervisor is not None:
        return _supervisor

    agent_model = ChatOpenAI(model=LLM_MODEL, **chat_model_kwargs())

    demand_analyst = create_agent(
        agent_model,
        tools=[search_demand_reports],
        system_prompt=(
            "You are a demand analyst. Given a category or product line, use "
            "`search_demand_reports` and return a concise 3-5 sentence summary "
            "covering volume direction, peak hours/days, and unique-visitor coverage."
        ),
        name="demand_analyst",
    )

    policy_agent = create_agent(
        agent_model,
        tools=[get_planner_policy, get_user_memory],
        system_prompt=(
            "You are the policy and preference agent. Use `get_planner_policy` for the "
            "standing buy-volume policy, and `get_user_memory(user_id=...)` for the active "
            "planner's saved preferences (the user_id is mentioned in the supervisor's request). "
            "Return both verbatim — do not editorialise."
        ),
        name="policy_agent",
    )

    supervisor_graph = create_supervisor(
        [demand_analyst, policy_agent],
        model=agent_model,
        prompt=(
            "You are the supply-chain planning supervisor. For any planner request:\n"
            "1. Delegate to `policy_agent` for the standing policy + the active planner's "
            "user_id memories.\n"
            "2. Delegate to `demand_analyst` for historical demand data on the relevant categories.\n"
            "3. Synthesise a concise buy recommendation that respects BOTH the policy and the "
            "user's saved preferences. Cite the data inline."
        ),
    )

    saver = await _get_saver()
    # We compile without `store=` here because the policy_agent's
    # get_user_memory tool reaches into AsyncOracleStore directly via the
    # module-level singleton — see tools.py. This keeps the app's
    # streaming events clean.
    _supervisor = supervisor_graph.compile(checkpointer=saver)
    return _supervisor
