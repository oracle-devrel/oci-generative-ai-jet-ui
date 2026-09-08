# Blocker: Spring AI OCI GenAI Adapter Does Not Support Tool Calling

**Date:** 2026-03-09
**Status:** Resolved (workaround: migrated to Ollama)
**Severity:** Was Blocker — resolved by switching from OCI GenAI to Ollama for chat model

## Problem

The `@Tool`-annotated methods in `AgentTools.java` (listOrders, lookupOrderStatus, initiateReturn, escalateToSupport, listSupportTickets) are never invoked by the LLM. The model responds with generic text instead of calling tools, even when the user's request clearly matches a tool description (e.g., "What are my orders?").

## Root Cause

**Spring AI 1.1.2's OCI GenAI Cohere adapter (`OCICohereChatModel`) does not implement the tool/function calling protocol.**

From the [Spring AI Chat Models Comparison](https://docs.spring.io/spring-ai/reference/api/chat/comparison.html):

> Tools and function calling [...] However, some models such as HuggingFace and **OCI GenAI/Cohere do not support this feature**.

This is an **adapter-level limitation**, not a model-level one. The problem has two layers:

### Layer 1: Model Capability (not the blocker)

Both Cohere Command R+ and Meta Llama 3.3 70B Instruct (available on OCI GenAI) natively support tool/function calling. The models themselves can understand tool definitions, decide when to call them, and output structured tool call requests.

### Layer 2: Spring AI Adapter (the blocker)

For tool calling to work, the framework adapter must:

1. Serialize `@Tool` definitions into the API request format
2. Send them alongside the prompt to the model API
3. Parse tool call responses from the model
4. Execute the tool locally and send results back to the model
5. Handle the multi-turn tool calling loop

`OCICohereChatModel` in Spring AI 1.1.2 **does not implement steps 1-5**. The tool definitions registered via `.defaultTools(agentTools)` are silently ignored.

### Why switching to Llama on OCI GenAI won't help

The `spring-ai-starter-model-oci-genai` module only provides **one** chat model implementation: `OCICohereChatModel`. There is no generic `OCIChatModel` or `OCILlamaChatModel`. The only available config path is `spring.ai.oci.genai.cohere.chat` — no generic `spring.ai.oci.genai.chat` path exists.

Even though OCI's REST API supports tools for both Cohere (`CohereChatRequest.tools`) and Llama (`GenericChatRequest.tools`), Spring AI has no adapter to use them.

## Evidence

Server logs show only vector store queries (semantic memory working) but zero tool invocations (procedural memory silent):

```
DEBUG o.s.a.v.oracle.OracleVectorStore : SQL query: select id, content, metadata, embedding...
```

No log lines from `AgentTools` methods (which all log `"Procedural memory: ..."` on invocation).

## Impact

- Procedural memory (the 5 `@Tool` methods) is completely non-functional
- The agent cannot look up orders, initiate returns, escalate to support, or list tickets
- Episodic memory (chat history) and semantic memory (RAG/vector search) work correctly

## Possible Solutions

1. **Use Ollama** — Run a local model (e.g., Llama 3.1, Qwen 2.5) with `spring-ai-starter-model-ollama`. Full tool calling support, no API keys needed. Minimal code changes (swap dependency + chat config). Keep OCI GenAI for embeddings.

2. **Use OpenAI or Anthropic** — Add `spring-ai-starter-model-openai` or `spring-ai-starter-model-anthropic`. Full tool calling support. Requires an API key. Keep OCI GenAI for embeddings.

3. **Wait for Spring AI update** — Future versions of Spring AI may add tool calling support to the OCI GenAI adapter.

## Resolution

Migrated from OCI GenAI to Ollama for the chat model (commit `5279dc2`). The `spring-ai-starter-model-ollama` adapter fully supports tool calling. All 5 `@Tool` methods in `AgentTools` now work correctly. OCI GenAI was removed entirely — Ollama handles both chat (qwen2.5) and embeddings (nomic-embed-text).

## References

- [Spring AI Chat Models Comparison — Tool Calling Support](https://docs.spring.io/spring-ai/reference/api/chat/comparison.html)
- [Spring AI OCI GenAI Cohere Chat Documentation](https://docs.spring.io/spring-ai/reference/api/chat/oci-genai/cohere-chat.html)
- [Spring AI Tool Calling Documentation](https://docs.spring.io/spring-ai/reference/api/tools.html)
- [OCI GenAI Llama Tools Support Release Note](https://docs.oracle.com/en-us/iaas/releasenotes/generative-ai/llama-tools-support.htm)
