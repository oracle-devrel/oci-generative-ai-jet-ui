"""Layer 1: the model. Supports three LLM providers.

Provider selection is controlled by the ``LLM_PROVIDER`` environment variable:

- ``oci_genai`` (default): Oracle Cloud Infrastructure Generative AI Service
  via the native ``oci`` Python SDK. Reads ``~/.oci/config`` for tenancy / user /
  region / key; set ``OCI_COMPARTMENT_ID`` and optionally ``OCI_MODEL_ID``.
- ``openai``: Standard OpenAI API. Same SDK, different base URL / key.
- ``oca``: Oracle Code Assist via LiteLLM-compatible gateway for internal demos.

Public interface
----------------
stream_chat(messages, *, model=None, temperature=0.7)
    Generator yielding token strings. Works for all configured providers.

stream_chat_with_tools(messages, tools, *, side, model=None, temperature=0.7)
    Generator yielding structured event dicts for the agent loop.
    Events: {type: tool_call, name, args}, {type: tool_result, name, result},
            {type: token, data}, {type: done}.
    Runs the tool-call loop internally, dispatching via TOOL_REGISTRY.

complete(prompt, *, system=None, model=None)
    Non-streaming convenience wrapper; joins streamed deltas.

get_model()
    Returns the OpenAI client for oca/openai providers.
    Raises ValueError for oci_genai (use stream_chat instead).
"""

import json
import os
from collections.abc import Generator
from functools import lru_cache

from openai import OpenAI

DEFAULT_OCA_HEADERS = {"client": "codex-cli", "client-version": "0"}


@lru_cache(maxsize=1)
def get_model() -> OpenAI:
    """Return the OpenAI-compatible client for oca or openai providers.

    Raises ValueError if LLM_PROVIDER=oci_genai — callers on that path should
    use stream_chat() instead, which handles client creation internally.
    """
    provider = os.environ.get("LLM_PROVIDER", "oci_genai").lower()
    if provider == "oci_genai":
        raise ValueError(
            "get_model() is not supported for LLM_PROVIDER=oci_genai. "
            "Use stream_chat() instead — it handles the OCI SDK client internally."
        )
    api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
    if provider == "openai":
        if not api_key:
            raise ValueError("API_KEY or OPENAI_API_KEY is required for LLM_PROVIDER=openai")
        return OpenAI(api_key=api_key)
    if provider == "oca":
        if not api_key:
            raise ValueError("API_KEY is required for LLM_PROVIDER=oca")
        base_url = os.environ.get("OCA_BASE_URL")
        if not base_url:
            raise ValueError("OCA_BASE_URL is required for LLM_PROVIDER=oca")
        headers_raw = os.environ.get("OCA_HEADERS")
        headers = json.loads(headers_raw) if headers_raw else DEFAULT_OCA_HEADERS
        return OpenAI(api_key=api_key, base_url=base_url, default_headers=headers)
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}. Supported: oca, openai, oci_genai")


def stream_chat(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.7,
) -> Generator[str, None, None]:
    """Yield token strings for a chat conversation, hiding provider details.

    Args:
        messages: List of dicts with 'role' and 'content' keys, following the
            OpenAI message format (roles: 'system', 'user', 'assistant').
        model: Model name override. Falls back to LLM_MODEL env var, then a
            sensible default per provider.
        temperature: Sampling temperature (0.0-2.0). Defaults to 0.7.

    Yields:
        Strings containing token deltas from the LLM. Caller can join them to
        reconstruct the full response.

    Raises:
        ValueError: If LLM_PROVIDER is unrecognised or required env vars are
            missing.

    Example:
        response = "".join(stream_chat([{"role": "user", "content": "Hello"}]))
    """
    provider = os.environ.get("LLM_PROVIDER", "oci_genai").lower()

    if provider in ("oca", "openai"):
        yield from _stream_chat_openai(messages, model=model, temperature=temperature)
    elif provider == "oci_genai":
        yield from _stream_chat_oci_genai(messages, model=model, temperature=temperature)
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: {provider!r}. Supported: oca, openai, oci_genai"
        )


def complete(prompt: str, *, system: str | None = None, model: str | None = None) -> str:
    """Non-streaming completion; joins all streamed deltas into one string.

    Args:
        prompt: The user message to send to the model.
        system: Optional system prompt prepended to the conversation.
        model: Model name override. Falls back to LLM_MODEL env var.

    Returns:
        The full model response as a single string.
    """
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return "".join(stream_chat(messages, model=model))


# ── Private helpers ───────────────────────────────────────────────────────────


def _stream_chat_openai(
    messages: list[dict],
    *,
    model: str | None,
    temperature: float,
) -> Generator[str, None, None]:
    """Stream chat via the OpenAI-compatible SDK (used for oca and openai)."""
    client = get_model()
    resolved_model = model or os.environ.get("LLM_MODEL", "xai.grok-3-fast")
    # OCA's LiteLLM gateway returns streaming by default; request explicitly so
    # the OpenAI SDK gives us a proper Stream object rather than a raw SSE string.
    stream = client.chat.completions.create(
        model=resolved_model,
        messages=messages,
        stream=True,
        temperature=temperature,
    )
    for chunk in stream:
        if chunk.choices:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


def _stream_chat_oci_genai(
    messages: list[dict],
    *,
    model: str | None,
    temperature: float,
) -> Generator[str, None, None]:
    """Stream chat via the OCI Generative AI Service SDK.

    Reads ~/.oci/config for tenancy/user/region/fingerprint/key_file.
    Required env vars: OCI_COMPARTMENT_ID.
    Optional env vars: OCI_MODEL_ID, LLM_MODEL (default: xai.grok-3-fast),
    OCI_REGION, OCI_PROFILE (default: DEFAULT), OCI_MAX_TOKENS (default: 600).

    Streaming SSE events carry JSON payloads. For the GENERIC api_format the
    text delta lives at:
      choices[0].message.content[0].text  (streaming chunk shape)
    or the simpler single-message shape:
      message.content[0].text
    We try the choices path first, then fall back, then yield '' defensively.
    """
    import oci
    from oci.generative_ai_inference import GenerativeAiInferenceClient
    from oci.generative_ai_inference.models import (
        AssistantMessage,
        ChatDetails,
        GenericChatRequest,
        OnDemandServingMode,
        SystemMessage,
        TextContent,
        UserMessage,
    )

    compartment_id = os.environ.get("OCI_COMPARTMENT_ID")
    model_id = (
        model or os.environ.get("OCI_MODEL_ID") or os.environ.get("LLM_MODEL", "xai.grok-3-fast")
    )
    profile = os.environ.get("OCI_PROFILE", "DEFAULT")
    max_tokens = int(os.environ.get("OCI_MAX_TOKENS", "600"))

    if not compartment_id:
        raise ValueError(
            "OCI_COMPARTMENT_ID environment variable is required for LLM_PROVIDER=oci_genai"
        )
    # Build config: optional region override on top of the file-based config.
    config = oci.config.from_file(profile_name=profile)
    region_override = os.environ.get("OCI_REGION")
    if region_override:
        config["region"] = region_override

    client = GenerativeAiInferenceClient(config=config)

    # Convert OpenAI-style message dicts to OCI SDK Message objects.
    # Use the typed subclasses (UserMessage, SystemMessage, AssistantMessage)
    # so role is set correctly and the API accepts them.
    oci_messages = []
    for msg in messages:
        role = msg.get("role", "user").lower()
        text = msg.get("content", "")
        content = [TextContent(text=text)]
        if role == "system":
            oci_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            oci_messages.append(AssistantMessage(content=content))
        else:
            oci_messages.append(UserMessage(content=content))

    details = ChatDetails(
        compartment_id=compartment_id,
        serving_mode=OnDemandServingMode(model_id=model_id),
        chat_request=GenericChatRequest(
            api_format=GenericChatRequest.API_FORMAT_GENERIC,
            messages=oci_messages,
            is_stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
        ),
    )

    response = client.chat(details)

    # response.data is an oci._vendor.sseclient.SSEClient instance.
    # Each event.data is a JSON string.
    for event in response.data.events():
        if not event.data or event.data.strip() == "[DONE]":
            continue
        try:
            payload = json.loads(event.data)
        except (json.JSONDecodeError, ValueError):
            continue

        # Try the choices[0].message.content[0].text path first (standard
        # streaming chunk structure mirrors GenericChatResponse shape).
        try:
            text = payload["choices"][0]["message"]["content"][0]["text"]
            yield text
            continue
        except (KeyError, IndexError, TypeError):
            pass

        # Fallback: some streaming implementations omit the choices wrapper
        # and deliver message.content[0].text directly.
        try:
            text = payload["message"]["content"][0]["text"]
            yield text
            continue
        except (KeyError, IndexError, TypeError):
            pass

        # Yield empty string rather than crashing on unexpected payload shapes.
        yield ""


# ── Agent loop: tool-calling ──────────────────────────────────────────────────

_MAX_TOOL_ITERATIONS = 5


def stream_chat_with_tools(
    messages: list[dict],
    tools: list[dict],
    *,
    side: str,
    model: str | None = None,
    temperature: float = 0.7,
) -> Generator[dict, None, None]:
    """Run the multi-turn agent loop, yielding structured event dicts.

    The function sends the conversation to the LLM with the four tool schemas.
    When the LLM decides to call a tool, it:

    1. Yields ``{"type": "tool_call", "name": ..., "args": {...}}``.
    2. Executes the tool via TOOL_REGISTRY (injecting ``side`` as the first arg).
    3. Yields ``{"type": "tool_result", "name": ..., "result": ...}``.
    4. Appends the assistant + tool messages and loops.

    When the LLM produces text content instead of tool calls it yields
    ``{"type": "token", "data": token_string}`` events and finally
    ``{"type": "done"}``.

    The loop is capped at ``_MAX_TOOL_ITERATIONS`` turns to prevent runaway.

    Implementation note on OCI GenAI tool-calling:
    The OCI SDK uses non-streaming for the tool-decision turns (the
    is_stream=False path) because assembling partial-JSON tool-call deltas
    from an SSE stream is fragile and not needed for latency here -- the user
    sees the tool_status events immediately after the call returns. Only the
    final text-generation turn uses streaming so the audience sees tokens
    appearing. This hybrid approach is deliberately chosen for reliability.

    Args:
        messages: OpenAI-style message list with role/content dicts.
        tools: List of TOOL_SCHEMAS dicts (the JSON Schema the LLM sees).
        side: 'mongo' or 'oracle' -- injected as the first arg to every tool.
        model: Model override. Falls back to LLM_MODEL env var.
        temperature: Sampling temperature.

    Yields:
        Dicts with a 'type' key; see module docstring for shapes.
    """
    from data_migration_harness.tools.agent_tools import TOOL_REGISTRY

    provider = os.environ.get("LLM_PROVIDER", "oci_genai").lower()

    if provider in ("oca", "openai"):
        yield from _agent_loop_openai(
            messages=messages,
            tools=tools,
            side=side,
            model=model,
            temperature=temperature,
            registry=TOOL_REGISTRY,
        )
    elif provider == "oci_genai":
        yield from _agent_loop_oci_genai(
            messages=messages,
            tools=tools,
            side=side,
            model=model,
            temperature=temperature,
            registry=TOOL_REGISTRY,
        )
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: {provider!r}. Supported: oca, openai, oci_genai"
        )


# ── OpenAI-compatible agent loop (oca / openai) ───────────────────────────────


def _agent_loop_openai(
    messages: list[dict],
    tools: list[dict],
    side: str,
    model: str | None,
    temperature: float,
    registry: dict,
) -> Generator[dict, None, None]:
    """Agent loop for oca/openai providers using the OpenAI tools API."""
    client = get_model()
    resolved_model = model or os.environ.get("LLM_MODEL", "xai.grok-3-fast")
    # Convert our TOOL_SCHEMAS format (which uses "FUNCTION" type capitalized
    # for OCI compatibility) to the lowercase "function" format OpenAI expects.
    openai_tools = []
    for t in tools:
        openai_tools.append(
            {
                "type": "function",
                "function": t["function"],
            }
        )

    conversation = list(messages)

    for _ in range(_MAX_TOOL_ITERATIONS):
        response = client.chat.completions.create(
            model=resolved_model,
            messages=conversation,
            tools=openai_tools,
            tool_choice="auto",
            temperature=temperature,
            stream=False,
        )
        choice = response.choices[0]
        msg = choice.message

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            # Append the assistant's tool-call message to the conversation
            conversation.append(
                {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    fn_args = {}
                yield {"type": "tool_call", "name": fn_name, "args": fn_args}
                result = _execute_tool(registry, fn_name, side, fn_args)
                yield {"type": "tool_result", "name": fn_name, "result": result}
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    }
                )
        else:
            # Final text response -- stream it
            stream = client.chat.completions.create(
                model=resolved_model,
                messages=conversation,
                temperature=temperature,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield {"type": "token", "data": delta}
            yield {"type": "done"}
            return

    # Loop limit hit
    yield {"type": "token", "data": "(tool loop limit reached)"}
    yield {"type": "done"}


# ── OCI GenAI agent loop ──────────────────────────────────────────────────────


def _agent_loop_oci_genai(
    messages: list[dict],
    tools: list[dict],
    side: str,
    model: str | None,
    temperature: float,
    registry: dict,
) -> Generator[dict, None, None]:
    """Agent loop for OCI GenAI using the native SDK.

    Tool-decision turns are non-streaming (single round-trip) for reliability.
    Only the final text-generation turn streams tokens so the audience sees
    them appear in real time.
    """
    import oci
    from oci.generative_ai_inference import GenerativeAiInferenceClient
    from oci.generative_ai_inference.models import (
        AssistantMessage,
        ChatDetails,
        FunctionCall,
        FunctionDefinition,
        GenericChatRequest,
        OnDemandServingMode,
        SystemMessage,
        TextContent,
        ToolChoiceAuto,
        ToolMessage,
        UserMessage,
    )

    compartment_id = os.environ.get("OCI_COMPARTMENT_ID")
    model_id = (
        model or os.environ.get("OCI_MODEL_ID") or os.environ.get("LLM_MODEL", "xai.grok-3-fast")
    )
    profile = os.environ.get("OCI_PROFILE", "DEFAULT")
    max_tokens = int(os.environ.get("OCI_MAX_TOKENS", "1200"))

    if not compartment_id:
        raise ValueError("OCI_COMPARTMENT_ID required for LLM_PROVIDER=oci_genai")

    config = oci.config.from_file(profile_name=profile)
    region_override = os.environ.get("OCI_REGION")
    if region_override:
        config["region"] = region_override

    client = GenerativeAiInferenceClient(config=config)

    # Build the OCI FunctionDefinition tool objects from our TOOL_SCHEMAS.
    # FunctionDefinition(name, description, parameters) -- parameters is an
    # opaque object (dict) in the SDK.
    oci_tools = []
    for t in tools:
        fn = t["function"]
        oci_tools.append(
            FunctionDefinition(
                name=fn["name"],
                description=fn["description"],
                parameters=fn.get("parameters"),
            )
        )

    def _build_oci_messages(msg_list: list[dict]) -> list:
        """Convert OpenAI-style message dicts to OCI Message objects."""
        result = []
        for msg in msg_list:
            role = msg.get("role", "user").lower()
            content_raw = msg.get("content")
            # content can be None (e.g. assistant tool-call message with no text)
            if role == "system":
                text = content_raw or ""
                result.append(SystemMessage(content=[TextContent(text=text)]))
            elif role == "assistant":
                tool_calls_raw = msg.get("tool_calls")
                if tool_calls_raw:
                    # Build FunctionCall objects for each tool call
                    oci_calls = []
                    for tc in tool_calls_raw:
                        oci_calls.append(
                            FunctionCall(
                                id=tc.get("id"),
                                name=tc["function"]["name"],
                                arguments=tc["function"]["arguments"],
                            )
                        )
                    result.append(AssistantMessage(content=None, tool_calls=oci_calls))
                else:
                    text = content_raw or ""
                    result.append(AssistantMessage(content=[TextContent(text=text)]))
            elif role == "tool":
                tool_content = content_raw or ""
                result.append(
                    ToolMessage(
                        content=[TextContent(text=tool_content)],
                        tool_call_id=msg.get("tool_call_id"),
                    )
                )
            else:
                text = content_raw or ""
                result.append(UserMessage(content=[TextContent(text=text)]))
        return result

    conversation = list(messages)

    for _ in range(_MAX_TOOL_ITERATIONS):
        oci_messages = _build_oci_messages(conversation)

        # Non-streaming call for the tool-decision turn
        details = ChatDetails(
            compartment_id=compartment_id,
            serving_mode=OnDemandServingMode(model_id=model_id),
            chat_request=GenericChatRequest(
                api_format=GenericChatRequest.API_FORMAT_GENERIC,
                messages=oci_messages,
                tools=oci_tools,
                tool_choice=ToolChoiceAuto(),
                is_stream=False,
                temperature=temperature,
                max_tokens=max_tokens,
            ),
        )

        response = client.chat(details)
        chat_resp = response.data.chat_response
        choice = chat_resp.choices[0]
        finish_reason = choice.finish_reason
        resp_msg = choice.message

        if finish_reason in ("tool_calls", "TOOL_CALLS") or (
            hasattr(resp_msg, "tool_calls") and resp_msg.tool_calls
        ):
            # Collect the tool calls from the assistant message
            tool_calls_out = resp_msg.tool_calls or []

            # Persist the assistant's tool-call message in conversation
            tc_dicts = []
            for tc in tool_calls_out:
                tc_dicts.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments or "{}",
                        },
                    }
                )
            conversation.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tc_dicts,
                }
            )

            for tc in tool_calls_out:
                fn_name = tc.name
                try:
                    fn_args = json.loads(tc.arguments or "{}")
                except json.JSONDecodeError:
                    fn_args = {}
                yield {"type": "tool_call", "name": fn_name, "args": fn_args}
                result = _execute_tool(registry, fn_name, side, fn_args)
                yield {"type": "tool_result", "name": fn_name, "result": result}
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    }
                )
        else:
            # Final text response -- stream it with a second call
            oci_messages_final = _build_oci_messages(conversation)
            stream_details = ChatDetails(
                compartment_id=compartment_id,
                serving_mode=OnDemandServingMode(model_id=model_id),
                chat_request=GenericChatRequest(
                    api_format=GenericChatRequest.API_FORMAT_GENERIC,
                    messages=oci_messages_final,
                    is_stream=True,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
            )
            stream_resp = client.chat(stream_details)
            for event in stream_resp.data.events():
                if not event.data or event.data.strip() == "[DONE]":
                    continue
                try:
                    payload = json.loads(event.data)
                except (json.JSONDecodeError, ValueError):
                    continue
                try:
                    text = payload["choices"][0]["message"]["content"][0]["text"]
                    if text:
                        yield {"type": "token", "data": text}
                    continue
                except (KeyError, IndexError, TypeError):
                    pass
                try:
                    text = payload["message"]["content"][0]["text"]
                    if text:
                        yield {"type": "token", "data": text}
                    continue
                except (KeyError, IndexError, TypeError):
                    pass
            yield {"type": "done"}
            return

    # Loop limit hit
    yield {"type": "token", "data": "(tool loop limit reached)"}
    yield {"type": "done"}


# ── Shared tool executor ──────────────────────────────────────────────────────


def _execute_tool(registry: dict, name: str, side: str, args: dict) -> object:
    """Call a registered tool, injecting side as the first positional arg.

    Args:
        registry: TOOL_REGISTRY dict mapping name to callable.
        name: The tool name the LLM requested.
        side: 'mongo' or 'oracle'.
        args: Dict of kwargs as parsed from the LLM's JSON arguments string.

    Returns:
        The tool's return value (list or dict).

    Raises:
        ValueError: If the tool name is not in the registry.
    """
    fn = registry.get(name)
    if fn is None:
        available = ", ".join(sorted(registry))
        raise ValueError(f"Unknown tool {name!r}. Available tools: {available}")
    try:
        return fn(side, **args)
    except Exception as exc:
        # Return the error as a dict so the LLM can narrate it rather than
        # crashing the whole agent loop.
        return {"error": f"{type(exc).__name__}: {str(exc)[:300]}"}
