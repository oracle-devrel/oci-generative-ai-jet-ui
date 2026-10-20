"""Usage feedback: uses and sessions, weights and decay, resolving names, listing, adding and resetting."""

import uuid

import pytest

from golestan_code_mcp.search import feedback as search_feedback

from search.feedback_helpers import make_repo, search, stored, use, write

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


# --- the boost (T007) ---


def test_boost_grows_linearly_to_the_cap():
    assert search_feedback.boost(0, 0.2) == 0
    assert search_feedback.boost(1, 0.2) == pytest.approx(0.04)
    assert search_feedback.boost(2.5, 0.2) == pytest.approx(0.1)
    assert search_feedback.boost(search_feedback.SATURATION, 0.2) == search_feedback.boost(1000, 0.2) == 0.2
    assert search_feedback.boost(1000, 0) == 0


# --- writing uses: one per result per session ---


def test_a_cited_use_replaces_an_opened_one_in_the_same_session(conn, clean):
    s = uuid.uuid4().hex
    write(conn, use(clean, how="opened", session=s), use(clean, how="cited", session=s))
    assert stored(conn, clean) == [("cited", s)]
    write(conn, use(clean, how="cited", session=s), use(clean, how="opened", session=s))
    assert stored(conn, clean) == [("cited", s)]


def test_two_opened_uses_in_one_session_are_one(conn, clean):
    s = uuid.uuid4().hex
    write(conn, use(clean, how="opened", session=s), use(clean, how="opened", session=s))
    assert stored(conn, clean) == [("opened", s)]


def test_another_session_adds_a_use(conn, clean):
    write(conn, use(clean), use(clean))
    assert [how for how, _ in stored(conn, clean)] == ["cited", "cited"]


# --- weights and decay ---


def test_weights_halve_every_half_life(conn, clean):
    write(conn, use(clean), use(clean, "turn_helper", how="opened"), use(clean, "Widget", days_ago=30, kind="class"),
          use(clean, "Widget.run", days_ago=60, kind="method"))
    with conn.cursor() as cur:
        w = search_feedback.weights(cur, [clean.id], 30)
    weight = {name: v[1] for (_, _, name), v in w.items()}
    assert weight["spin_widget"] == pytest.approx(1.0, abs=0.01)
    assert weight["turn_helper"] == pytest.approx(0.5, abs=0.01)
    assert weight["Widget"] == pytest.approx(0.5, abs=0.01)
    assert weight["Widget.run"] == pytest.approx(0.25, abs=0.01)
    assert {v[0] for v in w.values()} == {1}
    assert set(w) == {(clean.id, "pkg/widgets.py", n) for n in weight}


def test_weights_add_up_and_skip_other_repositories(conn, clean):
    write(conn, *(use(clean) for _ in range(3)))
    with conn.cursor() as cur:
        uses, weight, last = search_feedback.weights(cur, [clean.id], 30)[(clean.id, "pkg/widgets.py", "spin_widget")]
        assert uses == 3 and weight == pytest.approx(3.0, abs=0.01) and last is not None
        assert search_feedback.weights(cur, [], 30) == {}
        assert search_feedback.weights(cur, [-1], 30) == {}


# --- resolving a result's identity ---


def test_resolve_finds_symbols_and_pages(conn, fb):
    with conn.cursor() as cur:
        assert search_feedback.resolve(cur, fb.id, "pkg/widgets.py", "spin_widget") == "function"
        assert search_feedback.resolve(cur, fb.id, "pkg/widgets.py", "Widget.run") == "method"
        assert search_feedback.resolve(cur, fb.id, "pkg", "pkg") == "page"
        assert search_feedback.resolve(cur, fb.id, "pkg/other.py", "spin_widget") is None
        assert search_feedback.resolve(cur, fb.id, "pkg/widgets.py", "no_such_name") is None


# --- listing, adding and resetting (US3, research R9) ---


def test_listing_shows_decay_by_weight(conn, clean):
    search_feedback.add(conn, clean.name, "spin_widget")
    search_feedback.add(conn, clean.name, "turn_helper", days_ago=30)
    search_feedback.add(conn, clean.name, "Widget.run", days_ago=60)
    rows = search_feedback.listing(conn, clean.name)
    assert [(r.name, r.kind, r.path, r.uses, round(r.weight, 2), round(r.boost, 2), r.indexed) for r in rows] == [
        ("spin_widget", "function", "pkg/widgets.py", 1, 1.0, 0.04, True),
        ("turn_helper", "function", "pkg/widgets.py", 1, 0.5, 0.02, True),
        ("Widget.run", "method", "pkg/widgets.py", 1, 0.25, 0.01, True)]
    assert all(r.last_used is not None for r in rows)


def test_add_gives_each_use_its_own_cli_session(conn, clean):
    assert search_feedback.add(conn, clean.name, "spin_widget", count=3) == ("pkg/widgets.py", "function")
    with conn.cursor() as cur:
        cur.execute("select client, session_id from ccctx_feedback where repo_id = :r", r=clean.id)
        rows = cur.fetchall()
    assert len({s for _, s in rows}) == 3 and all(c == "cli" and s.startswith("cli:") for c, s in rows)


def test_add_finds_pages_and_refuses_what_it_cannot_place(conn, clean, tmp_path):
    assert search_feedback.add(conn, clean.name, "pkg") == ("pkg", "page")
    with pytest.raises(ValueError, match="must not be negative"):
        search_feedback.add(conn, clean.name, "spin_widget", days_ago=-1)
    with pytest.raises(ValueError, match="not found: no indexed symbol or page named 'nothing_here'"):
        search_feedback.add(conn, clean.name, "nothing_here")
    with pytest.raises(ValueError, match="not found"):
        search_feedback.add(conn, clean.name, "spin_widget", path="pkg/m1.py")
    with pytest.raises(ValueError, match="no repository named 't-nowhere'"):
        search_feedback.add(conn, "t-nowhere", "spin_widget")


def test_a_name_at_several_paths_needs_a_path(conn, tmp_path):
    repo = make_repo(conn, tmp_path / "twice", {"a/x.py": "def same():\n    return 1\n",
                                                "b/x.py": "def same():\n    return 2\n"})
    try:
        with pytest.raises(ValueError, match="'same' is at several paths; pass --path:\na/x.py\nb/x.py"):
            search_feedback.add(conn, repo.name, "same")
        assert search_feedback.add(conn, repo.name, "same", path="b/x.py") == ("b/x.py", "function")
    finally:
        with conn.cursor() as cur:
            cur.execute("delete from ccctx_repos where id = :i", i=repo.id)
        conn.commit()


def test_a_use_of_removed_code_lists_unindexed_and_boosts_nothing(conn, clean):
    write(conn, use(clean, "gone_widget"))
    [row] = search_feedback.listing(conn, clean.name)
    assert (row.name, row.indexed) == ("gone_widget", False)
    assert "gone_widget" not in {r.name for r in search(conn, clean, "gone widget", limit=50)}


def test_reset_one_repository(conn, clean, tmp_path):
    other = make_repo(conn, tmp_path / "other", {"pkg/o.py": "def other_fn():\n    return 1\n"})
    try:
        search_feedback.add(conn, clean.name, "spin_widget", count=2)
        search_feedback.add(conn, other.name, "other_fn")
        assert search_feedback.reset(conn, clean.name) == 2
        assert search_feedback.listing(conn, clean.name) == [] and len(search_feedback.listing(conn, other.name)) == 1
        # reset(conn, None) empties every repository's uses: not run here, it would wipe the real ones too
    finally:
        with conn.cursor() as cur:
            cur.execute("delete from ccctx_repos where id = :i", i=other.id)
        conn.commit()
