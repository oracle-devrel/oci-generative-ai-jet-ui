"""Same selected provider, model, generation limits for both agent pipelines."""
import json
import time
from pathlib import Path

import anthropic
import httpx

from .config import MODELS, REASONING_EFFORT, env

TIMEOUT = httpx.Timeout(240, connect=8)


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise ValueError("Model did not return the requested JSON format") from None


def model_config(id):
    for m in MODELS:
        if m["id"] == id:
            return m
    raise ValueError("Unknown model")


def oci_url():
    # OCI's OpenAI-compatible surface lives under /openai/v1 on the regional inference host.
    url = env("OCI_GENAI_ENDPOINT").strip().rstrip("/")
    return url if url.endswith("/openai/v1") else url + "/openai/v1"


def available():
    models = []
    for m in MODELS:
        enabled = False
        reason = ""
        if m["provider"] in ["privateai", "ollama"]:
            try:
                url = (
                    env("PRIVATE_AI_URL", "https://127.0.0.1:8443")
                    if m["provider"] == "privateai"
                    else env("OLLAMA_URL", "http://127.0.0.1:11434")
                )
                verify = env("PRIVATE_AI_CA_FILE") or True
                headers = (
                    {"Authorization": "Bearer " + env("PRIVATE_AI_API_KEY")}
                    if m["provider"] == "privateai"
                    else {}
                )
                with httpx.Client(timeout=3, verify=verify) as client:
                    r = client.get(
                        url + ("/v1/models" if m["provider"] == "privateai" else "/api/tags"),
                        headers=headers,
                    )
                    r.raise_for_status()
                    names = [
                        x.get("id", x.get("name"))
                        for x in r.json().get("data", r.json().get("models", []))
                    ]
                    enabled = m["model"] in names
                    if not enabled:
                        reason = "Configured model is not loaded: " + m["model"]
            except Exception:
                reason = "Service not running or TLS/authentication is not configured"
        elif m["provider"] == "oci":
            api_key = bool(env("OCI_GENAI_API_KEY"))
            sdk = (
                bool(env("OCI_COMPARTMENT_ID"))
                and Path(env("OCI_CONFIG_FILE", "~/.oci/config")).expanduser().exists()
            )
            enabled = bool(env("OCI_GENAI_ENDPOINT")) and bool(m["model"]) and (api_key or sdk)
            reason = (
                ""
                if enabled
                else "Missing OCI_GENAI_API_KEY (or OCI SDK config + OCI_COMPARTMENT_ID) / OCI_GENAI_ENDPOINT"
            )
        else:
            enabled = bool(env(m["key"]))
            reason = "" if enabled else "Missing " + m["key"]
        models.append(dict(m, enabled=enabled, reason=reason))
    return models


def post(url, verify=True, **kw):
    # Connect/read failures (Wi-Fi roaming, VPN reconnects) get one retry; HTTP status errors never do.
    for attempt in range(2):
        try:
            with httpx.Client(timeout=TIMEOUT, verify=verify) as client:
                r = client.post(url, **kw)
                r.raise_for_status()
                return r.json()
        except httpx.TransportError:
            if attempt:
                raise


def complete(model_id, messages, max_tokens=600, schema=None):
    m = model_config(model_id)
    provider = m["provider"]
    t = time.perf_counter()
    if provider == "anthropic":
        return complete_anthropic(m, messages, schema, t)
    if provider == "oci" and not env("OCI_GENAI_API_KEY"):
        return complete_oci(m, messages, max_tokens, t)
    if provider == "ollama":
        d = post(
            env("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/chat",
            json={
                "model": m["model"],
                "messages": messages,
                "stream": False,
                "format": schema or "json",
                "options": {
                    "num_ctx": m["context"],
                    "num_predict": max_tokens,
                    "temperature": 0,
                    "seed": 131026,
                },
                "keep_alive": "30m",
            },
        )
        content = d["message"]["content"]
        usage = {
            "input_tokens": d.get("prompt_eval_count", 0),
            "output_tokens": d.get("eval_count", 0),
        }
    elif provider in ["privateai", "oci"]:
        url, key = (
            (env("PRIVATE_AI_URL", "https://127.0.0.1:8443") + "/v1", env("PRIVATE_AI_API_KEY"))
            if provider == "privateai"
            else (oci_url(), env("OCI_GENAI_API_KEY"))
        )
        body = {
            "model": m["model"],
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if provider == "privateai":
            body["temperature"] = 0
        if schema and provider == "oci":
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "answer", "schema": schema, "strict": True},
            }
        d = post(
            url + "/chat/completions",
            verify=(env("PRIVATE_AI_CA_FILE") or True) if provider == "privateai" else True,
            headers={"Authorization": "Bearer " + key},
            json=body,
        )
        content = d["choices"][0]["message"]["content"]
        u = d.get("usage", {})
        usage = {
            "input_tokens": u.get("prompt_tokens"),
            "output_tokens": u.get("completion_tokens"),
            "cached_input_tokens": (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
            or 0,
        }
    elif provider == "openai":
        if not env("OPENAI_API_KEY"):
            raise ValueError("Missing OPENAI_API_KEY")
        # GPT-6.x is a reasoning model: no temperature; output budget must cover reasoning tokens.
        fmt = (
            {"type": "json_schema", "name": "answer", "schema": schema, "strict": True}
            if schema
            else {"type": "json_object"}
        )
        d = post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": "Bearer " + env("OPENAI_API_KEY")},
            json={
                "model": m["model"],
                "input": messages,
                "max_output_tokens": max(4000, max_tokens),
                "reasoning": {"effort": REASONING_EFFORT},
                "text": {"format": fmt},
                "store": False,
            },
        )
        content = "".join(
            p.get("text", "")
            for x in d.get("output", [])
            for p in x.get("content", [])
            if p.get("type") == "output_text"
        )
        u = d["usage"]
        usage = {
            "input_tokens": u["input_tokens"],
            "output_tokens": u["output_tokens"],
            "cached_input_tokens": (u.get("input_tokens_details") or {}).get("cached_tokens", 0)
            or 0,
        }
    else:
        raise ValueError("Unsupported provider")
    if usage.get("input_tokens") is None or usage.get("output_tokens") is None:
        raise ValueError("Provider omitted token usage; measured tokenomics unavailable")
    return {
        "content": content,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "cached_input_tokens": usage.get("cached_input_tokens", 0),
        "cache_write_tokens": 0,
        "llm_ms": round((time.perf_counter() - t) * 1000, 2),
        "model": m["model"],
    }


ANTHROPIC = None


def complete_anthropic(m, messages, schema, t):
    global ANTHROPIC
    if not env("ANTHROPIC_API_KEY"):
        raise ValueError("Missing ANTHROPIC_API_KEY")
    ANTHROPIC = ANTHROPIC or anthropic.Anthropic(
        api_key=env("ANTHROPIC_API_KEY"), timeout=240.0, max_retries=2
    )
    # Prompt cache: the stable system prefix (instructions, catalog or schema) carries the breakpoint; Opus 5.5 caches prefixes from 512 tokens.
    system = [
        {
            "type": "text",
            "text": "\n".join(x["content"] for x in messages if x["role"] == "system"),
            "cache_control": {"type": "ephemeral"},
        }
    ]
    msgs = [x for x in messages if x["role"] != "system"]
    # Opus 5.5: thinking is always on, sampling parameters are rejected; effort sets depth.
    output_config = {"effort": REASONING_EFFORT}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    response = ANTHROPIC.beta.messages.create(
        model=m["model"],
        max_tokens=16000,
        system=system,
        messages=msgs,
        output_config=output_config,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        raise ValueError("Model declined the request (refusal)")
    content = "".join(b.text for b in response.content if b.type == "text")
    u = response.usage
    read = u.cache_read_input_tokens or 0
    write = u.cache_creation_input_tokens or 0
    return {
        "content": content,
        "input_tokens": u.input_tokens + read + write,
        "output_tokens": u.output_tokens,
        "cached_input_tokens": read,
        "cache_write_tokens": write,
        "llm_ms": round((time.perf_counter() - t) * 1000, 2),
        "model": response.model,
    }


def complete_oci(m, messages, max_tokens, t):
    import oci

    config = oci.config.from_file(
        env("OCI_CONFIG_FILE", "~/.oci/config"), env("OCI_PROFILE", "DEFAULT")
    )
    client = oci.generative_ai_inference.GenerativeAiInferenceClient(
        config, service_endpoint=env("OCI_GENAI_ENDPOINT"), timeout=(8, 240)
    )
    models = oci.generative_ai_inference.models
    converted = []
    for message in messages:
        cls = {
            "system": models.SystemMessage,
            "user": models.UserMessage,
            "assistant": models.AssistantMessage,
        }[message["role"]]
        converted.append(cls(content=[models.TextContent(text=message["content"])]))
    request = models.GenericChatRequest(messages=converted, max_tokens=max_tokens, temperature=0)
    mode = (
        models.DedicatedServingMode(endpoint_id=m["model"])
        if m["model"].startswith("ocid1.generativeaiendpoint")
        else models.OnDemandServingMode(model_id=m["model"])
    )
    d = oci.util.to_dict(
        client.chat(
            models.ChatDetails(
                compartment_id=env("OCI_COMPARTMENT_ID"), serving_mode=mode, chat_request=request
            )
        ).data
    )
    cr = d["chat_response"]
    content = "".join(x.get("text", "") for x in cr["choices"][0]["message"]["content"])
    usage = cr.get("usage", {})
    if not usage:
        raise ValueError("OCI endpoint omitted usage; configure a model with usage reporting")
    return {
        "content": content,
        "input_tokens": usage.get("prompt_tokens", usage.get("input_tokens")),
        "output_tokens": usage.get("completion_tokens", usage.get("output_tokens")),
        "cached_input_tokens": 0,
        "cache_write_tokens": 0,
        "llm_ms": round((time.perf_counter() - t) * 1000, 2),
        "model": m["model"],
    }


def call_cost(m, c):
    # Cached prompt tokens are billed at the provider's cached-input rate; cache writes (Anthropic) at the write rate.
    read = c.get("cached_input_tokens", 0)
    write = c.get("cache_write_tokens", 0)
    plain = c["input_tokens"] - read - write
    return (
        plain * m["input_price"]
        + read * m.get("cached_input_price", m["input_price"])
        + write * m.get("cache_write_price", m["input_price"])
        + c["output_tokens"] * m["output_price"]
    ) / 1e6
