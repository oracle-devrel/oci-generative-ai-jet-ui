"""FastAPI server for Agent Reasoning Gateway."""

import argparse
import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_reasoning.agents import (
    ConsistencyAgent,
    CoTAgent,
    DecomposedAgent,
    LeastToMostAgent,
    ReActAgent,
    RecursiveAgent,
    SelfReflectionAgent,
    StandardAgent,
    ToTAgent,
)

app = FastAPI(title="Agent Reasoning Gateway")

AGENT_MAP = {
    "standard": StandardAgent,
    "cot": CoTAgent,
    "reflection": SelfReflectionAgent,
    "react": ReActAgent,
    "tot": ToTAgent,
    "consistency": ConsistencyAgent,
    "decomposed": DecomposedAgent,
    "least_to_most": LeastToMostAgent,
    "recursive": RecursiveAgent,
}


class GenerateRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = True


@app.post("/api/generate")
async def generate(request: GenerateRequest):
    """Generate response using reasoning agent."""
    # Parse model string: "model_name+strategy"
    if "+" in request.model:
        base_model, strategy = request.model.split("+", 1)
    else:
        base_model = request.model
        strategy = "standard"

    strategy = strategy.lower().strip()

    if strategy not in AGENT_MAP:
        strategy = "standard"

    print(f"Request: Model={base_model}, Strategy={strategy}")

    agent_class = AGENT_MAP[strategy]
    agent = agent_class(model=base_model)

    async def response_generator():
        try:
            for chunk in agent.stream(request.prompt):
                data = {
                    "model": request.model,
                    "created_at": "2023-01-01T00:00:00.000000Z",
                    "response": chunk,
                    "done": False,
                }
                yield json.dumps(data) + "\n"
                await asyncio.sleep(0)

            data = {
                "model": request.model,
                "created_at": "2023-01-01T00:00:00.000000Z",
                "response": "",
                "done": True,
                "total_duration": 0,
                "load_duration": 0,
                "prompt_eval_count": 0,
                "eval_count": 0,
            }
            yield json.dumps(data) + "\n"
        except Exception as e:
            err_data = {"response": f"\n\n[Error in Reasoning Agent: {str(e)}]", "done": True}
            yield json.dumps(err_data) + "\n"

    return StreamingResponse(response_generator(), media_type="application/x-ndjson")


@app.get("/api/tags")
async def tags():
    """Return list of available virtual models."""
    return {"models": [{"name": f"gemma3:270m+{strategy}"} for strategy in AGENT_MAP.keys()]}


def main():
    """Server entry point."""
    from agent_reasoning.config import get_ollama_host, set_ollama_host

    parser = argparse.ArgumentParser(description="Agent Reasoning Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument(
        "--ollama-host", default=None, help="Ollama API endpoint (overrides config file)"
    )
    args = parser.parse_args()

    # Set Ollama endpoint from CLI arg or use config
    if args.ollama_host:
        set_ollama_host(args.ollama_host)
        print(f"Using Ollama endpoint: {args.ollama_host} (saved to config)")
    else:
        ollama_host = get_ollama_host()
        print(f"Using Ollama endpoint: {ollama_host}")

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
