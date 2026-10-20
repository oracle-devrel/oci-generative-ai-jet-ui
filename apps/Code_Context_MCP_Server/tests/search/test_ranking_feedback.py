"""The usage boost in ranking: explained, capped, bounded, never adding a hit, and without visible latency."""

import pytest

from search.feedback_helpers import CAP, hammer, search, symbols, use, write

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


def test_every_hit_explains_its_boost(conn, clean):
    write(conn, use(clean), use(clean, "turn_helper", how="opened"))
    hits = search(conn, clean, limit=50)
    assert hits and all(r.score == pytest.approx(r.relevance * (1 + r.feedback)) for r in hits)
    by_name = {r.name: r for r in hits}
    assert by_name["spin_widget"].feedback == pytest.approx(0.04, abs=1e-3)
    assert by_name["turn_helper"].feedback == pytest.approx(0.02, abs=1e-3)


@pytest.mark.parametrize("count", [1, 5, 1000])
def test_the_boost_never_passes_the_cap(conn, clean, count):
    hammer(conn, clean, "spin_widget", count=count)
    assert all(0 <= r.feedback <= CAP for r in search(conn, clean, limit=50))


def test_a_used_symbol_passes_only_what_is_within_twenty_percent(conn, clean):
    before = symbols(search(conn, clean, limit=50))
    target = before[-1]  # the weakest symbol found: everything else starts above it
    hammer(conn, clean, target.name, target.path, target.kind)
    after = symbols(search(conn, clean, limit=50))
    moved = {r.name: i for i, r in enumerate(after)}
    for r in before[:-1]:
        if r.relevance > target.relevance * (1 + CAP):
            assert moved[r.name] < moved[target.name], r.name
        elif r.relevance < target.relevance * (1 + CAP) and r.score > 0:  # not an unfound identifier definition
            assert moved[r.name] > moved[target.name], r.name
    assert [r.relevance for r in after if r.name == target.name] == [target.relevance]


def test_feedback_never_adds_a_hit(conn, clean):
    without = {r.name for r in search(conn, clean, limit=50)}
    hammer(conn, clean, "f3", "pkg/m3.py")
    assert {r.name for r in search(conn, clean, limit=50)} == without


def test_identifier_definitions_stay_first(conn, clean):
    hammer(conn, clean, "spin_widget")
    assert search(conn, clean, "turn_helper")[0].name == "turn_helper"


def test_a_used_page_is_placed_by_its_boosted_similarity(conn, clean):
    hammer(conn, clean, "pkg", "pkg", kind="page")
    hits = search(conn, clean, "what does the pkg package do with widgets", limit=50)
    [at] = [i for i, r in enumerate(hits) if r.kind == "page"]
    page = hits[at]
    assert page.feedback == pytest.approx(CAP) and page.score == pytest.approx(page.relevance * (1 + CAP))
    placed = min(1.0, page.similarity * (1 + CAP))
    assert all(h.similarity is not None and h.similarity >= placed for h in hits[:at] if h.kind != "page")
    assert all(r.feedback == 0 for r in hits if r.kind == "fact")


def test_switching_feedback_off_ranks_as_without_uses(conn, clean):
    baseline = search(conn, clean, limit=50)
    hammer(conn, clean, baseline[-1].name, baseline[-1].path, baseline[-1].kind)
    assert search(conn, clean, limit=50, feedback=False) == baseline
    assert search(conn, clean, limit=50, env={"CCCTX_FEEDBACK_CAP": "0"}) == baseline
    assert all(r.feedback == 0 and r.relevance == r.score for r in baseline)


def test_feedback_adds_no_visible_latency(conn, clean):
    """SC-007: the median of 5 searches with feedback is within 10% (plus 10 ms of timer noise) of the median without."""
    import statistics
    import time

    hammer(conn, clean, "spin_widget", count=20)

    def median(**kwargs):
        times = []
        for _ in range(5):
            started = time.perf_counter()
            search(conn, clean, **kwargs)
            times.append(time.perf_counter() - started)
        return statistics.median(times)

    median()  # warm up
    assert median() <= median(feedback=False) * 1.10 + 0.010
