"""Deterministic tests for the model fallback router (fake clients, injected clock and sleep)."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import oci_key_rotation as kr  # noqa: E402


class FakeAPIError(Exception):
    """Shaped like an openai.APIStatusError: carries `status_code`."""

    def __init__(self, status_code, message="boom"):
        super().__init__(message)
        self.status_code = status_code


class Clock:
    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds

    async def asleep(self, seconds):
        self.sleep(seconds)


def make_lanes(phx_keys=3, chi_keys=3):
    chi = kr.KeyRotator([f"chi-{i}" for i in range(chi_keys)], seed=0)
    return [
        kr.Lane("grok-phx", "xai.grok-4.3", "https://phx/openai/v1",
                kr.KeyRotator([f"phx-{i}" for i in range(phx_keys)], seed=0)),
        kr.Lane("grok-chi", "xai.grok-4.3", "https://chi/openai/v1", chi),
        kr.Lane("gptoss-chi", "openai.gpt-oss-120b", "https://chi/openai/v1", chi,
                {"reasoning_effort": "low"}),
    ]


def make_router(tmp_path, lanes=None, **kw):
    clock = Clock()
    router = kr.ModelRouter(lanes or make_lanes(), cooldown_s=120, log_path=tmp_path / "router.log",
                            clock=clock, sleep=clock.sleep, async_sleep=clock.asleep, **kw)
    return router, clock


class Script:
    """do_call that raises per (lane name) from a script and records every attempt."""

    def __init__(self, behaviour):
        self.behaviour = behaviour   # lane name -> callable(attempt_no, key) -> result or raises
        self.calls = []

    def __call__(self, client, lane):
        key = client
        self.calls.append((lane.name, key))
        count = sum(1 for n, _ in self.calls if n == lane.name)
        return self.behaviour[lane.name](count, key)


def fake_factory(endpoint, key):
    return key


def run(router, script):
    return router.call(script, fake_factory)


def events(router):
    return [json.loads(line) for line in router.log_path.read_text().splitlines()]


def ok(value):
    return lambda n, key: value


def raises(status, message="boom"):
    def fn(n, key):
        raise FakeAPIError(status, message)
    return fn


def test_classify_error():
    assert kr.classify_error(FakeAPIError(429)) == "rate_limit"
    assert kr.classify_error(Exception("Too Many Requests")) == "rate_limit"
    assert kr.classify_error(Exception("quota exceeded")) == "rate_limit"
    assert kr.classify_error(FakeAPIError(401)) == "auth"
    assert kr.classify_error(FakeAPIError(403)) == "auth"
    assert kr.classify_error(FakeAPIError(503)) == "transient"
    assert kr.classify_error(ConnectionError("reset")) == "transient"
    assert kr.classify_error(Exception("model overloaded")) == "transient"
    assert kr.classify_error(FakeAPIError(400, "bad request")) == "fatal"
    assert kr.classify_error(ValueError("nope")) == "fatal"


def wrapped(inner):
    """What OAMP raises: a bare RuntimeError whose cause carries the provider error."""
    try:
        try:
            raise inner
        except BaseException as e:
            raise RuntimeError("Chat Completions provider request failed.") from e
    except RuntimeError as outer:
        return outer


def test_classify_error_follows_wrapped_cause():
    assert kr.classify_error(wrapped(FakeAPIError(429))) == "rate_limit"
    assert kr.classify_error(wrapped(FakeAPIError(401))) == "auth"
    assert kr.classify_error(wrapped(FakeAPIError(400, "bad request"))) == "fatal"
    assert kr.classify_error(wrapped(ValueError("nope"))) == "fatal"


def test_rate_limit_goes_to_next_lane_without_key_sweep(tmp_path):
    router, _ = make_router(tmp_path)
    script = Script({"grok-phx": raises(429), "grok-chi": ok("chi"), "gptoss-chi": ok("oss")})
    assert run(router, script) == "chi"
    assert [n for n, _ in script.calls] == ["grok-phx", "grok-chi"]   # exactly one phx attempt
    first = events(router)[0]
    assert first["event"] == "cooldown" and first["from_lane"] == "grok-phx" and first["to_lane"] == "grok-chi"
    assert first["reason"] == "rate_limit" and first["status"] == 429
    assert router.active_lane().name == "grok-chi"


def test_cooling_lane_is_skipped_then_primary_returns_after_cooldown(tmp_path):
    router, clock = make_router(tmp_path)
    phx_fails = {"on": True}

    def phx(n, key):
        if phx_fails["on"]:
            raise FakeAPIError(429)
        return "phx"

    script = Script({"grok-phx": phx, "grok-chi": ok("chi"), "gptoss-chi": ok("oss")})
    assert run(router, script) == "chi"
    clock.now += 60
    assert run(router, script) == "chi"
    assert [n for n, _ in script.calls].count("grok-phx") == 1      # still cooling: not retried
    phx_fails["on"] = False
    clock.now += 61                                                   # 121 s since the 429
    assert run(router, script) == "phx"
    assert router.active_lane().name == "grok-phx"
    assert "return_to_primary" in [e["event"] for e in events(router)]


def test_auth_rotates_keys_in_lane_then_next_lane(tmp_path):
    router, _ = make_router(tmp_path)
    script = Script({"grok-phx": raises(401), "grok-chi": ok("chi"), "gptoss-chi": ok("oss")})
    assert run(router, script) == "chi"
    phx_keys = [k for n, k in script.calls if n == "grok-phx"]
    assert sorted(phx_keys) == ["phx-0", "phx-1", "phx-2"]            # each key exactly once
    assert "cooldown" not in [e["event"] for e in events(router)]     # auth does not cool the lane
    # bad keys are remembered: the next call does not retry them, goes straight to Chicago
    script.calls.clear()
    assert run(router, script) == "chi"
    assert [n for n, _ in script.calls] == ["grok-chi"]


def test_auth_single_bad_key_is_skipped_and_sticky(tmp_path):
    router, _ = make_router(tmp_path)
    bad = router.lanes[0].rotator.current()
    script = Script({"grok-phx": lambda n, key: (_ for _ in ()).throw(FakeAPIError(401)) if key == bad else "phx",
                     "grok-chi": ok("chi"), "gptoss-chi": ok("oss")})
    assert run(router, script) == "phx"
    script.calls.clear()
    assert run(router, script) == "phx"
    assert bad not in [k for _, k in script.calls]


def test_transient_retries_next_key_once_then_next_lane(tmp_path):
    router, clock = make_router(tmp_path)
    script = Script({"grok-phx": raises(503), "grok-chi": ok("chi"), "gptoss-chi": ok("oss")})
    assert run(router, script) == "chi"
    phx = [k for n, k in script.calls if n == "grok-phx"]
    assert len(phx) == 2 and phx[0] != phx[1]
    assert clock.slept == [kr.TRANSIENT_RETRY_DELAY_S]


def test_transient_recovers_on_retry(tmp_path):
    router, _ = make_router(tmp_path)
    script = Script({"grok-phx": lambda n, key: "phx" if n == 2 else (_ for _ in ()).throw(ConnectionError("x")),
                     "grok-chi": ok("chi"), "gptoss-chi": ok("oss")})
    assert run(router, script) == "phx"


def test_fatal_error_raises_immediately(tmp_path):
    router, _ = make_router(tmp_path)
    script = Script({"grok-phx": raises(400, "bad request"), "grok-chi": ok("chi"), "gptoss-chi": ok("oss")})
    with pytest.raises(FakeAPIError):
        run(router, script)
    assert len(script.calls) == 1


def test_all_lanes_limited_uses_last_lane_with_backoff_never_locks_out(tmp_path):
    router, clock = make_router(tmp_path)
    # all lanes 429 at first; the last lane recovers on its 3rd overall attempt
    script = Script({"grok-phx": raises(429), "grok-chi": raises(429),
                     "gptoss-chi": lambda n, key: "oss" if n >= 3 else (_ for _ in ()).throw(FakeAPIError(429))})
    assert run(router, script) == "oss"
    assert [n for n, _ in script.calls] == ["grok-phx", "grok-chi", "gptoss-chi", "gptoss-chi", "gptoss-chi"]
    assert clock.slept and max(clock.slept) <= kr.LAST_LANE_MAX_SLEEP_S
    assert "all_lanes_unavailable" in [e["event"] for e in events(router)]
    # served by the last lane: it is no longer cooling
    assert router.active_lane().name == "gptoss-chi"


def test_all_lanes_cooling_still_calls_last_lane_immediately(tmp_path):
    router, clock = make_router(tmp_path)
    for lane in router.lanes:
        router._cooling_until[lane.name] = clock.now + 100
    script = Script({"grok-phx": ok("phx"), "grok-chi": ok("chi"), "gptoss-chi": ok("oss")})
    assert run(router, script) == "oss"
    assert clock.slept == []


def test_last_lane_gives_up_after_cap_with_bounded_sleeps(tmp_path):
    router, clock = make_router(tmp_path)
    script = Script({"grok-phx": raises(429), "grok-chi": raises(429), "gptoss-chi": raises(429)})
    with pytest.raises(FakeAPIError):
        run(router, script)
    assert [n for n, _ in script.calls].count("gptoss-chi") == 1 + kr.LAST_LANE_ATTEMPTS
    assert max(clock.slept) <= kr.LAST_LANE_MAX_SLEEP_S


def test_missing_fallback_env_gives_phx_only():
    env = {"OCI_GENAI_API_KEY": "k1", "OCI_GENAI_API_KEY_2": "k2", "OCI_GENAI_ENDPOINT": "https://phx.example"}
    lanes = kr.load_lanes(env)
    assert [l.name for l in lanes] == ["grok-phx"]
    assert lanes[0].endpoint == "https://phx.example/openai/v1" and len(lanes[0].rotator) == 2


def test_full_env_builds_three_lanes():
    env = {"OCI_GENAI_API_KEY": "p", "LLM_MODEL": "xai.grok-4.3",
           "OCI_GENAI_FALLBACK_ENDPOINT": "https://chi.example/openai/v1",
           "OCI_GENAI_FALLBACK_API_KEY": "c1", "OCI_GENAI_FALLBACK_API_KEY_2": "c2"}
    lanes = kr.load_lanes(env)
    assert [l.name for l in lanes] == ["grok-phx", "grok-chi", "gptoss-chi"]
    assert lanes[2].model == "openai.gpt-oss-120b" and lanes[1].rotator is lanes[2].rotator
    assert lanes[1].rotator.keys == ["c1", "c2"]


def test_single_lane_behaves_like_before(tmp_path):
    router, clock = make_router(tmp_path, lanes=make_lanes()[:1])
    script = Script({"grok-phx": lambda n, key: "phx" if n == 3 else (_ for _ in ()).throw(FakeAPIError(429))})
    assert run(router, script) == "phx"
    assert router.primary_model == "xai.grok-4.3"


def test_chat_overrides_model_and_merges_extra_kwargs(tmp_path):
    seen = []

    class Completions:
        def __init__(self, key):
            self.key = key

        def create(self, **kwargs):
            seen.append((self.key, kwargs))
            if self.key.startswith("phx"):
                raise FakeAPIError(429)
            return "response-object"

    class Client:
        def __init__(self, key):
            self.chat = type("C", (), {"completions": Completions(key)})()

    router, _ = make_router(tmp_path)
    router._clients.clear()
    original = kr._openai_client_factory
    kr._openai_client_factory = lambda endpoint, key: Client(key)
    try:
        # call() resolves the factory at call time via the module global
        assert router.chat(model="ignored", messages=[{"role": "user", "content": "hi"}]) == "response-object"
    finally:
        kr._openai_client_factory = original
    assert seen[0][1]["model"] == "xai.grok-4.3" and "reasoning_effort" not in seen[0][1]
    assert seen[1][1]["model"] == "xai.grok-4.3"
    # force the gpt-oss lane
    router._cooling_until["grok-phx"] = router._cooling_until["grok-chi"] = router._clock() + 100
    kr._openai_client_factory = lambda endpoint, key: Client(key)
    try:
        router.chat(model="ignored", messages=[])
    finally:
        kr._openai_client_factory = original
    assert seen[-1][1]["model"] == "openai.gpt-oss-120b" and seen[-1][1]["reasoning_effort"] == "low"


def test_async_call_follows_same_policy(tmp_path):
    router, clock = make_router(tmp_path)

    async def do_call(client, lane):
        if lane.name == "grok-phx":
            raise FakeAPIError(429)
        return lane.name

    assert asyncio.run(router.acall(do_call, fake_factory)) == "grok-chi"
    assert events(router)[0]["event"] == "cooldown"


def test_log_never_contains_key_values(tmp_path):
    router, _ = make_router(tmp_path)
    script = Script({"grok-phx": raises(401), "grok-chi": raises(429), "gptoss-chi": ok("oss")})
    run(router, script)
    text = router.log_path.read_text()
    assert "phx-" not in text and "chi-" not in text
    assert all(e.get("pid") for e in events(router))
