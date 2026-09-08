"""Tests for the shared agent metadata module."""

from agent_reasoning.agent_metadata import AGENT_METADATA, PRIMARY_AGENT_IDS, get_agent_list

REQUIRED_FIELDS = {"name", "description", "reference", "best_for", "tradeoffs", "parameters"}
REQUIRED_PARAM_FIELDS = {"type", "default", "description"}


def test_all_agents_have_required_fields():
    for agent_id, meta in AGENT_METADATA.items():
        missing = REQUIRED_FIELDS - meta.keys()
        assert not missing, f"Agent '{agent_id}' missing fields: {missing}"


def test_parameter_schemas_valid():
    for agent_id, meta in AGENT_METADATA.items():
        for param_name, param_schema in meta["parameters"].items():
            missing = REQUIRED_PARAM_FIELDS - param_schema.keys()
            assert not missing, (
                f"Agent '{agent_id}', param '{param_name}' missing fields: {missing}"
            )


def test_get_agent_list_returns_all_primary_agents():
    agents = get_agent_list()
    ids = {a["id"] for a in agents}
    expected = set(PRIMARY_AGENT_IDS)
    assert ids == expected, f"Missing agents: {expected - ids}, extra: {ids - expected}"


def test_get_agent_list_includes_parameters():
    agents = get_agent_list()
    tot = next((a for a in agents if a["id"] == "tot"), None)
    assert tot is not None, "tot agent not found in list"
    params = tot["parameters"]
    assert "width" in params, "tot missing 'width' parameter"
    assert "depth" in params, "tot missing 'depth' parameter"
    assert params["width"]["default"] == 2
    assert params["depth"]["default"] == 3


def test_get_agent_list_has_visualizer_flags():
    agents = get_agent_list()
    by_id = {a["id"]: a for a in agents}
    # These agents have real visualizers
    for agent_id in (
        "cot",
        "tot",
        "react",
        "consistency",
        "decomposed",
        "least_to_most",
        "reflection",
        "refinement",
    ):
        assert by_id[agent_id]["has_visualizer"] is True, f"{agent_id} should have visualizer"
    # standard has no visualizer
    assert by_id["standard"]["has_visualizer"] is False


def test_get_agent_list_entry_shape():
    agents = get_agent_list()
    expected_keys = {
        "id",
        "name",
        "description",
        "reference",
        "best_for",
        "tradeoffs",
        "has_visualizer",
        "parameters",
    }
    for agent in agents:
        missing = expected_keys - agent.keys()
        assert not missing, f"Agent '{agent['id']}' entry missing keys: {missing}"
