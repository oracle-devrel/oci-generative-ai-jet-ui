# Ollama — local inference for the beginner path

Ollama is the default inference for beginner; an option for intermediate / advanced. This file is the install + model-pick + gotchas reference.

## Install

- macOS: `brew install ollama`, then `brew services start ollama`.
- Linux: `curl -fsSL https://ollama.com/install.sh | sh`.
- Windows: download installer from https://ollama.com/download.

The Ollama server runs on `http://localhost:11434` by default. The skill checks this URL is reachable before doing anything else.

## Model picks

| Use | Default | Why |
| --- | --- | --- |
| Embedding (beginner + intermediate) | `nomic-embed-text` (768 dims) | Small, fast, good enough for retrieval. |
| Chat (beginner) | `llama3.1:8b` | Solid baseline; doesn't go off the rails. |
| Chat — adventurous beginner | `qwen2.5:7b` | Strong reasoning, smaller than llama3.1. **See thinking-mode trap below.** |
| Chat (intermediate, if not using OCI) | `llama3.1:8b` or `qwen2.5:14b` | Tradeoff: 14b smarter, slower. |

The skill's interview asks the user to pick from this short list, not from the full Ollama library. Keeps choice fatigue low.

Pull with: `ollama pull <model>`. The skill does this for the user.

## The Qwen thinking-mode trap

Qwen models support a `<think>` ... `</think>` reasoning prefix. With Ollama, this can:
- Hang the response on hardware with limited threads.
- Break LangChain prompt templates that don't strip the think block.
- OOM on 8GB machines because reasoning chains are long.

The skill applies all three of these mitigations when a Qwen model is selected:

1. Set `OLLAMA_NUM_THREAD=1` in the project's `.env`.
2. Add a system prompt instruction: `Do not use <think> tags. Answer directly.`
3. If the model output contains `<think>` ... `</think>`, the skill strips it before passing to LangChain.

Source: confirmed-broken behavior on the user's local hardware (CLAUDE.md note in `~/.claude/CLAUDE.md`).

## Embedding via LangChain

```python
from langchain_ollama import OllamaEmbeddings
emb = OllamaEmbeddings(model="nomic-embed-text")
v = emb.embed_query("hello")  # → list[float], length 768
```

Under the hood: HTTP POST to `http://localhost:11434/api/embed`. Source: `~/git/personal/cAST-efficient-ollama/src/cast_ollama/embedding/embedder.py:1-50`.

## Chat via LangChain

```python
from langchain_ollama import ChatOllama
llm = ChatOllama(model="llama3.1:8b", temperature=0.2)
print(llm.invoke("explain vector search in two sentences").content)
```

For the intermediate path's chatbot, wrap this in `RunnableWithMessageHistory` + `OracleChatMessageHistory` for persistent conversations.

## Remote Ollama

If the user has Ollama on another machine, the skill supports `OLLAMA_HOST=http://192.168.1.100:11434` in `.env`. Both `OllamaEmbeddings` and `ChatOllama` honor it via the `base_url` parameter.

## Gotchas

- **Cold start.** First request to a model after `ollama pull` is slow — the model loads into VRAM. The skill does one warm-up call before benchmarking anything.
- **Concurrent requests.** Ollama serializes per-model by default. For chatbot demos, that's fine; for parallel batch embedding, expect throughput to look like one stream.
- **Model switching.** Switching between two models repeatedly thrashes VRAM. If the user has both 8b chat + nomic embed loaded, fine; if they're swapping in/out a 14b, it'll feel slow.
- **`langchain-ollama` import.** It's `langchain_ollama`, not `langchain.llms.Ollama` (deprecated path). The skill only uses the new package.

## Don't do these

- Don't pin `OLLAMA_HOST` in committed code — it's per-machine; goes in `.env`.
- Don't use Qwen without the thinking-mode mitigations. Don't ask why we know.
- Don't expect Ollama to be as fast as OCI GenAI on a laptop. Set user expectations during the interview.
