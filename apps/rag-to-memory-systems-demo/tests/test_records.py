from memory.records import MemoryCandidate, PromotionResult, FactRecord


def test_candidate_fact_minimal():
    c = MemoryCandidate(
        memory_type="fact",
        tenant_id="t",
        content="x",
        confidence=0.9,
        source_run_id="run_1",
        subject="s",
        predicate="p",
    )
    assert c.subject == "s"


def test_promotion_result_factory_methods():
    assert PromotionResult.written("id1").outcome == "written"
    assert PromotionResult.deduplicated("id2").outcome == "deduplicated"
    assert PromotionResult.rejected("low_confidence").reason == "low_confidence"
    assert PromotionResult.superseded("new", "old").reason == "superseded:old"


def test_promotion_result_carries_status_and_confidence():
    """The envelope needs both the resulting status and the candidate's
    source confidence, so the factory methods accept and propagate them."""
    w = PromotionResult.written("fact_x", status="provisional", confidence=0.82)
    assert w.status == "provisional"
    assert w.confidence == 0.82

    # Supersession always lands as 'active' — the contradiction event
    # itself is a confirmation signal.
    s = PromotionResult.superseded("fact_new", "fact_old", confidence=0.95)
    assert s.status == "active"
    assert s.confidence == 0.95

    # Rejections carry confidence so replay can correlate threshold
    # rejections with the score that caused them; status stays None
    # because no record was written.
    r = PromotionResult.rejected("low_confidence", confidence=0.3)
    assert r.status is None
    assert r.confidence == 0.3
