import pytest
from soccer_agent.inference.bulk import lookup


@pytest.mark.integration
def test_lookup_existing_match(predictions_loaded):
    p = lookup("Spain", "Brazil")
    assert p is not None
    assert p.prob_home_win == pytest.approx(0.45)
    assert p.source == "bulk"


@pytest.mark.integration
def test_lookup_missing_match_returns_none(predictions_loaded):
    assert lookup("Atlantis", "Mars") is None
