from memory.agent_session import AgentSession


def test_agent_session_with_defaults():
    session = AgentSession(
        tenant_id="acme-support",
        user_id="customer:jane@example.com",
        agent_id="agent:support_v1",
    )
    assert session.run_id is not None
    assert session.run_id.startswith("run_")
    assert session.turn_index == 0
    assert session.scratch == {}
    assert session.turn_buffer == []


def test_agent_session_advance_turn():
    session = AgentSession(tenant_id="t", user_id="u", agent_id="a")
    session.advance_turn()
    assert session.turn_index == 1
    session.advance_turn()
    assert session.turn_index == 2


def test_agent_session_new_run():
    session = AgentSession(tenant_id="t", user_id="u", agent_id="a")
    session.advance_turn()
    session.scratch["k"] = "v"
    session.turn_buffer.append("x")
    old_run = session.run_id
    session.new_run()
    assert session.run_id != old_run
    assert session.turn_index == 0
    assert session.scratch == {}
    assert session.turn_buffer == []
