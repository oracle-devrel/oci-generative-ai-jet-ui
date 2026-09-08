"""Provider-agnostic LLM adapter — pick your model with config, not code edits.

In oracle/.env:
  LLM_PROVIDER=anthropic   (default)  needs ANTHROPIC_API_KEY
  LLM_PROVIDER=openai                 needs OPENAI_API_KEY  (pip install openai)
  LLM_PROVIDER=ollama                 needs a local Ollama  (OLLAMA_HOST, default localhost:11434)
  LLM_MODEL=<override>                optional; sensible default per provider

All three providers verified live: anthropic, openai (json_schema strict), and ollama
(llama3.2, schema-constrained output). This covers every *structured* LLM step (wiki compiler, memory consolidation, the
classifiers, the idea agent): one `structured(system, prompt, schema)` call that returns
validated JSON on any provider. The research agent's TOOL LOOP (client tools + server-side
web search) is Anthropic-shaped and stays Claude-first — run it with Claude, or point the
Anthropic SDK at an Anthropic-compatible gateway via ANTHROPIC_BASE_URL.
"""
import json
import os
import pathlib
import urllib.request

from dotenv import load_dotenv

# self-sufficient: load oracle/.env relative to this file (same pattern as db.py), so the
# adapter works no matter which module imports it first, from any cwd.
load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

import keychain_secrets  # noqa: E402 -- resolve keychain:<item> secrets (same as db.py)
keychain_secrets.resolve_env()  # so ANTHROPIC/OPENAI keys work whether or not db was imported

PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").lower()
DEFAULTS = {"anthropic": "claude-opus-4-8", "openai": "gpt-5.6-sol", "ollama": "llama3.2"}
MODEL = os.environ.get("LLM_MODEL") or DEFAULTS.get(PROVIDER, DEFAULTS["anthropic"])

# --- the loop ledger: every LLM call records its tokens, tagged by which loop spent them.
# Loops should report their cost ("every loop earns its keep" needs a denominator).
# One JSONL line per call; LOOP_LABEL names the loop (sync exports it per step), else the
# running script's name. Local file, gitignored; report scripts aggregate it.
LEDGER = os.environ.get("LOOP_LEDGER") or str(
    pathlib.Path(__file__).resolve().parent.parent.parent / "exports" / "loop_ledger.jsonl")


def loop_label():
    import sys
    stem = pathlib.Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else ""
    return os.environ.get("LOOP_LABEL") or stem or "interactive"


def record_usage(model, tokens_in, tokens_out, label=None):
    """Append one ledger line. Never raises — cost visibility must not break a loop."""
    try:
        import datetime
        line = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
                "label": label or loop_label(), "provider": PROVIDER, "model": model,
                "tokens_in": int(tokens_in or 0), "tokens_out": int(tokens_out or 0)}
        p = pathlib.Path(LEDGER)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a") as f:
            f.write(json.dumps(line) + "\n")
    except Exception:
        pass


def structured(system, prompt, schema, max_tokens=4096, model=None):
    """One prompt in, schema-validated JSON out — on whichever provider is configured.
    `model` overrides per call on anthropic (e.g. a cheap classifier model); other
    providers use the configured LLM_MODEL."""
    if PROVIDER == "anthropic":
        import anthropic
        r = anthropic.Anthropic().messages.create(
            model=model or MODEL, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": schema}})
        record_usage(model or MODEL, r.usage.input_tokens, r.usage.output_tokens)
        return json.loads(next(b.text for b in r.content if b.type == "text"))

    if PROVIDER == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            raise SystemExit("LLM_PROVIDER=openai needs the sdk: ./.venv/bin/pip install openai")
        r = OpenAI().chat.completions.create(
            model=MODEL, max_completion_tokens=max_tokens,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_schema",
                             "json_schema": {"name": "out", "strict": True, "schema": schema}})
        if getattr(r, "usage", None):
            record_usage(MODEL, r.usage.prompt_tokens, r.usage.completion_tokens)
        return json.loads(r.choices[0].message.content)

    if PROVIDER == "ollama":
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        body = json.dumps({"model": MODEL, "stream": False, "format": schema,
                           "messages": [{"role": "system", "content": system},
                                        {"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(f"{host}/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read())
        record_usage(MODEL, data.get("prompt_eval_count"), data.get("eval_count"))
        return json.loads(data["message"]["content"])

    raise SystemExit(f"unknown LLM_PROVIDER={PROVIDER!r} (anthropic | openai | ollama)")
