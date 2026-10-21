"""Shared OCI Generative AI model router for the notebook and the app.

Grok-4.3 limits are per tenancy *per region*, so every key of one region shares
one bucket: rotating keys on a 429 cannot help. Instead the router walks a chain
of *lanes* (model + endpoint + key pool), in order:

1. ``grok-phx``    LLM_MODEL on OCI_GENAI_ENDPOINT, keys OCI_GENAI_API_KEY.._6
2. ``grok-chi``    same model on OCI_GENAI_FALLBACK_ENDPOINT, keys OCI_GENAI_FALLBACK_API_KEY.._6
3. ``gptoss-chi``  OCI_GENAI_BACKUP_MODEL on the Chicago endpoint and keys

Lanes whose environment is missing are skipped. Error policy per call:

* rate limit -> no key sweep; the lane cools for OCI_GENAI_FALLBACK_COOLDOWN_S
  (default 120 s) and the next available lane is tried at once;
* auth (401/403) -> next key of the same lane (each key once per call), then the
  next lane; a key that failed auth is skipped for the rest of the process;
* transient (5xx, connection, timeout) -> one retry on the next key after ~1 s,
  then the next lane;
* anything else (400 ...) raises immediately.

When every lane is cooling or failing, the last lane is used anyway with
exponential backoff (at most 6 attempts, sleeps capped at 15 s), so attendees are
never locked out. Switches are silent: they are only appended as JSON lines to
OCI_GENAI_ROUTER_LOG (default ~/.cache/fraud-workshop/llm-router.log), never
containing key values, and optionally echoed to the console by the app.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

DEFAULT_COOLDOWN_S = 120.0
DEFAULT_LOG_PATH = "~/.cache/fraud-workshop/llm-router.log"
DEFAULT_PHOENIX_ENDPOINT = "https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com/openai/v1"
DEFAULT_MODEL = "xai.grok-4.3"
DEFAULT_BACKUP_MODEL = "openai.gpt-oss-120b"
TRANSIENT_RETRY_DELAY_S = 1.0
LAST_LANE_ATTEMPTS = 6
LAST_LANE_MAX_SLEEP_S = 15.0

# Per-model request adjustments, keyed by model id (see ModelRouter.chat).
MODEL_EXTRA_KWARGS: dict[str, dict[str, Any]] = {}


# --------------------------------------------------------------------------- keys


def load_keys(prefix: str, env: Mapping[str, str] = os.environ) -> list[str]:
    """Collect ``prefix``, ``prefix_1`` .. ``prefix_8`` in order, de-duplicated and sanitized."""
    found: list[str] = []
    for name in (prefix, f"{prefix}_1"):
        value = (env.get(name) or "").strip()
        if value and "REPLACE_ME" not in value and "NOT_SET" not in value:
            found.append(value)
            break
    for index in range(2, 9):
        value = (env.get(f"{prefix}_{index}") or "").strip()
        if value and "REPLACE_ME" not in value and "NOT_SET" not in value:
            found.append(value)
    return list(dict.fromkeys(found))


class KeyRotator:
    """Random starting key with sticky circular failover."""

    def __init__(self, keys: list[str], seed: Any | None = None):
        if not keys:
            raise RuntimeError("No OCI GenAI API keys found. Set OCI_GENAI_API_KEY and optionally _2.._8.")
        self.keys = keys
        self._idx = random.Random(seed).randrange(len(keys))

    def current(self) -> str:
        return self.keys[self._idx]

    def current_index(self) -> int:
        return self._idx

    def select(self, index: int) -> str:
        self._idx = index % len(self.keys)
        return self.current()

    def advance(self) -> str:
        return self.select(self._idx + 1)

    def __len__(self) -> int:
        return len(self.keys)


# --------------------------------------------------------------------------- errors

_RATE_TOKENS = ("429", "rate limit", "rate_limit", "too many requests", "quota", "throttl")
_AUTH_TOKENS = ("401", "403", "unauthorized", "forbidden", "invalid api key", "authentication")
_TRANSIENT_TOKENS = ("overloaded", "service unavailable", "temporarily", "connection", "timed out", "timeout")


def _status_of(exc: BaseException) -> int | None:
    for holder in (exc, getattr(exc, "response", None)):
        for attr in ("status_code", "status", "code"):
            value = getattr(holder, attr, None)
            try:
                if value is not None and 100 <= int(value) <= 599:
                    return int(value)
            except (TypeError, ValueError):
                continue
    return None


def classify_error(exc: BaseException) -> str:
    """Return ``'rate_limit' | 'auth' | 'transient' | 'fatal'``.

    Wrappers that hide the HTTP status (OAMP raises a bare RuntimeError around litellm's
    RateLimitError) are classified by the first cause in their chain that is not fatal.
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        kind = _classify_one(current)
        if kind != "fatal" or _status_of(current) is not None:
            return kind
        current = current.__cause__ or current.__context__
    return "fatal"


def _classify_one(exc: BaseException) -> str:
    status = _status_of(exc)
    if status == 429:
        return "rate_limit"
    if status in (401, 403):
        return "auth"
    if status is not None:
        if status >= 500 or status == 408:
            return "transient"
        return "fatal"
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if "ratelimit" in name or any(t in message for t in _RATE_TOKENS):
        return "rate_limit"
    if "authentication" in name or "permissiondenied" in name or any(t in message for t in _AUTH_TOKENS):
        return "auth"
    if (isinstance(exc, (ConnectionError, TimeoutError)) or "connection" in name or "timeout" in name
            or any(t in message for t in _TRANSIENT_TOKENS)):
        return "transient"
    return "fatal"


# --------------------------------------------------------------------------- lanes


@dataclass
class Lane:
    name: str
    model: str
    endpoint: str
    rotator: KeyRotator
    extra_kwargs: dict = field(default_factory=dict)


def _normalize_endpoint(endpoint: str) -> str:
    endpoint = (endpoint or "").strip().rstrip("/")
    if endpoint and not endpoint.endswith("/openai/v1"):
        endpoint = f"{endpoint}/openai/v1"
    return endpoint


def load_lanes(env: Mapping[str, str] = os.environ) -> list[Lane]:
    """Build the lane chain from the environment, skipping lanes whose env is missing."""
    primary_keys = load_keys("OCI_GENAI_API_KEY", env)
    fallback_keys = load_keys("OCI_GENAI_FALLBACK_API_KEY", env)

    model = (env.get("LLM_MODEL") or DEFAULT_MODEL).strip()
    backup = (env.get("OCI_GENAI_BACKUP_MODEL") or DEFAULT_BACKUP_MODEL).strip()
    lanes: list[Lane] = []
    if primary_keys:
        endpoint = _normalize_endpoint(env.get("OCI_GENAI_ENDPOINT") or DEFAULT_PHOENIX_ENDPOINT)
        lanes.append(Lane("grok-phx", model, endpoint, KeyRotator(primary_keys),
                          dict(MODEL_EXTRA_KWARGS.get(model, {}))))
    fallback_endpoint = _normalize_endpoint(env.get("OCI_GENAI_FALLBACK_ENDPOINT") or "")
    if fallback_keys and fallback_endpoint:
        rotator = KeyRotator(fallback_keys)
        lanes.append(Lane("grok-chi", model, fallback_endpoint, rotator, dict(MODEL_EXTRA_KWARGS.get(model, {}))))
        if backup:
            lanes.append(Lane("gptoss-chi", backup, fallback_endpoint, rotator,
                              dict(MODEL_EXTRA_KWARGS.get(backup, {}))))
    return lanes


# --------------------------------------------------------------------------- router


@dataclass
class _Step:
    lane: Lane
    key_index: int
    delay: float


def _openai_client_factory(endpoint: str, key: str):
    from openai import OpenAI

    # max_retries=0: the router owns retry/backoff; SDK retries would only delay the lane switch.
    return OpenAI(base_url=endpoint, api_key=key, max_retries=0)


class ModelRouter:
    def __init__(self, lanes: list[Lane], cooldown_s: float | None = None, log_path: str | os.PathLike | None = None,
                 console: bool = False, *, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], Any] = time.sleep,
                 async_sleep: Callable[[float], Any] = asyncio.sleep):
        if not lanes:
            raise RuntimeError("No LLM lanes configured: set OCI_GENAI_API_KEY (and optionally the fallback keys).")
        self.lanes = list(lanes)
        if cooldown_s is None:
            try:
                cooldown_s = float(os.environ.get("OCI_GENAI_FALLBACK_COOLDOWN_S", DEFAULT_COOLDOWN_S))
            except ValueError:
                cooldown_s = DEFAULT_COOLDOWN_S
        self.cooldown_s = float(cooldown_s)
        self.log_path = Path(log_path or os.environ.get("OCI_GENAI_ROUTER_LOG") or DEFAULT_LOG_PATH).expanduser()
        self.console = console
        self._clock, self._sleep, self._async_sleep = clock, sleep, async_sleep
        self._cooling_until: dict[str, float] = {}
        self._bad_keys: dict[int, set[int]] = {}      # id(rotator) -> key indexes that failed auth
        self._clients: dict[tuple[Any, str, str], Any] = {}
        self._served_rank = 0                          # lane index that served the last call
        self._lock = threading.Lock()

    # ---- public API

    @property
    def primary_model(self) -> str:
        return self.lanes[0].model

    def active_lane(self) -> Lane:
        """First lane that is not cooling (the last lane when all are)."""
        available = self._available()
        return available[0] if available else self.lanes[-1]

    def call(self, do_call: Callable[[Any, Lane], Any], make_client: Callable[[str, str], Any] | None = None):
        """Run ``do_call(client, lane)`` through the lane chain. ``make_client(endpoint, key)`` overrides the OpenAI client."""
        factory = make_client or _openai_client_factory
        steps = self._steps()
        step = next(steps)
        while True:
            if step.delay:
                self._sleep(step.delay)
            try:
                result = do_call(self._client(step, factory), step.lane)
            except Exception as exc:  # noqa: BLE001 - classified by the step generator
                step = steps.send(exc)
            else:
                try:
                    steps.send(None)
                except StopIteration:
                    pass
                return result

    async def acall(self, do_call: Callable[[Any, Lane], Any], make_client: Callable[[str, str], Any] | None = None):
        """Async counterpart of :meth:`call`; ``do_call`` returns an awaitable."""
        factory = make_client or _openai_client_factory
        steps = self._steps()
        step = next(steps)
        while True:
            if step.delay:
                await self._async_sleep(step.delay)
            try:
                result = await do_call(self._client(step, factory), step.lane)
            except Exception as exc:  # noqa: BLE001
                step = steps.send(exc)
            else:
                try:
                    steps.send(None)
                except StopIteration:
                    pass
                return result

    def chat(self, **kwargs):
        """``chat.completions.create(**kwargs)`` on the active lane's model; returns the response unchanged."""
        def do_call(client, lane):
            params = {**kwargs, **lane.extra_kwargs, "model": lane.model}
            return client.chat.completions.create(**params)
        return self.call(do_call)

    # ---- state

    def _available(self) -> list[Lane]:
        now = self._clock()
        return [lane for lane in self.lanes if self._cooling_until.get(lane.name, 0.0) <= now]

    def _client(self, step: _Step, factory):
        key = step.lane.rotator.keys[step.key_index]
        cache_key = (factory, step.lane.endpoint, key)
        with self._lock:
            client = self._clients.get(cache_key)
            if client is None:
                client = self._clients[cache_key] = factory(step.lane.endpoint, key)
        return client

    def _bad(self, lane: Lane) -> set[int]:
        return self._bad_keys.setdefault(id(lane.rotator), set())

    def _log(self, event: str, **fields):
        record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "pid": os.getpid(), "event": event, **fields}
        line = json.dumps({k: v for k, v in record.items() if v is not None}, sort_keys=False)
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock, self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass
        if self.console:
            detail = " ".join(f"{k}={v}" for k, v in record.items() if k not in ("ts", "pid", "event") and v is not None)
            print(f"[llm-router] {event} {detail}".rstrip(), flush=True)

    # ---- the retry state machine (shared by sync and async drivers)
    # Protocol: yields a _Step; the driver sends back the exception raised by the call, or None
    # on success. The generator raises the final error itself.

    def _steps(self):
        lanes = self._available()
        last_lane = self.lanes[-1]
        tried_last = False
        for lane in lanes:
            tried_last = tried_last or lane is last_lane
            failure = yield from self._lane_steps(lane)
            if failure is None:
                self._note_served(lane)
                return
            reason, exc = failure
            following = next((l for l in lanes if self.lanes.index(l) > self.lanes.index(lane)), None)
            status = _status_of(exc)
            if reason == "rate_limit":
                self._cooling_until[lane.name] = self._clock() + self.cooldown_s
                self._log("cooldown", from_lane=lane.name, to_lane=following.name if following else None,
                          reason=reason, status=status, cooldown_s=self.cooldown_s)
            else:
                self._log("lane_failed", from_lane=lane.name, to_lane=following.name if following else None,
                          reason=reason, status=status)
        # Every lane is cooling or failed: never lock out, hammer the last lane with backoff.
        yield from self._last_resort(last_lane, tried_last)

    def _lane_steps(self, lane: Lane):
        rotator, bad = lane.rotator, self._bad(lane)
        count = len(rotator)
        start = rotator.current_index()
        queue = [i for i in ((start + n) % count for n in range(count)) if i not in bad]
        transient_retried = False
        delay = 0.0
        failure: tuple[str, BaseException] | None = ("auth", RuntimeError("all keys failed authentication"))
        while queue:
            index = queue.pop(0)
            rotator.select(index)
            exc = yield _Step(lane, index, delay)
            delay = 0.0
            if exc is None:
                return None
            kind = classify_error(exc)
            failure = (kind, exc)
            if kind == "fatal":
                raise exc
            if kind == "rate_limit":
                return failure
            if kind == "auth":
                bad.add(index)
                self._log("bad_key", from_lane=lane.name, key_index=index, reason="auth", status=_status_of(exc))
                continue
            # transient
            if transient_retried:
                return failure
            transient_retried = True
            delay = TRANSIENT_RETRY_DELAY_S
            if not queue:
                queue.append(index if index not in bad else (index + 1) % count)
        return failure

    def _last_resort(self, lane: Lane, already_tried: bool):
        self._log("all_lanes_unavailable", to_lane=lane.name)
        rotator = lane.rotator
        last_exc: BaseException | None = None
        for attempt in range(LAST_LANE_ATTEMPTS):
            if attempt == 0:
                delay = TRANSIENT_RETRY_DELAY_S if already_tried else 0.0
            else:
                delay = min(LAST_LANE_MAX_SLEEP_S, 2.0 ** attempt)
            index = rotator.current_index()
            exc = yield _Step(lane, index, delay)
            if exc is None:
                self._cooling_until.pop(lane.name, None)
                self._note_served(lane)
                return
            last_exc = exc
            kind = classify_error(exc)
            if kind == "fatal":
                raise exc
            if kind in ("auth", "transient"):
                rotator.advance()
        assert last_exc is not None
        raise last_exc

    def _note_served(self, lane: Lane):
        self._cooling_until.pop(lane.name, None)
        rank = self.lanes.index(lane)
        if rank < self._served_rank:
            self._log("return_to_primary" if rank == 0 else "return_to_lane", to_lane=lane.name,
                      from_lane=self.lanes[self._served_rank].name)
        elif rank > self._served_rank:
            self._log("switch", from_lane=self.lanes[self._served_rank].name, to_lane=lane.name)
        self._served_rank = rank


# --------------------------------------------------------------------------- OAMP


def make_router_oamp_llm(router: ModelRouter):
    """OAMP-compatible LLM that serves every call through the router's active lane."""
    from oracleagentmemory.core.llms import Llm

    def make_llm(endpoint: str, key: str):
        return _LaneLlm(endpoint, key)

    class _LaneLlm:
        """Late-bound per lane: the OAMP Llm needs the lane model, known only at call time."""
        def __init__(self, endpoint, key):
            self.endpoint, self.key, self._by_model = endpoint, key, {}

        def get(self, lane: Lane):
            if lane.model not in self._by_model:
                self._by_model[lane.model] = Llm(f"openai/{lane.model}", api_base=lane.endpoint, api_key=self.key)
            return self._by_model[lane.model]

    class RouterOAMPLlm:
        def generate(self, *args, **kwargs):
            return router.call(lambda holder, lane: holder.get(lane).generate(*args, **kwargs), make_llm)

        async def generate_async(self, *args, **kwargs):
            return await router.acall(lambda holder, lane: holder.get(lane).generate_async(*args, **kwargs), make_llm)

        def __getattr__(self, name):
            lane = router.active_lane()
            return getattr(Llm(f"openai/{lane.model}", api_base=lane.endpoint, api_key=lane.rotator.current()), name)

    return RouterOAMPLlm()
