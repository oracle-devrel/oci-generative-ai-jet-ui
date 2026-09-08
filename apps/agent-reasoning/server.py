import asyncio
import json
import queue
import threading
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from agent_reasoning.agent_metadata import get_agent_list

# Import unified AGENT_MAP from interceptor (single source of truth)
from agent_reasoning.interceptor import AGENT_MAP

# Store active debug sessions
debug_sessions = {}
debug_sessions_lock = threading.Lock()

app = FastAPI(title="Agent Reasoning Gateway")


class GenerateRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = True
    parameters: dict = {}
    # Other ollama fields ignored for this demo


@app.post("/api/generate")
async def generate(request: GenerateRequest):
    # 1. Parse Model String to find Strategy
    # Format: "model_name+strategy" e.g. "gemma3+cot"
    if "+" in request.model:
        base_model, strategy = request.model.split("+", 1)
    else:
        base_model = request.model
        strategy = "standard"  # Default

    strategy = strategy.lower().strip()

    if strategy not in AGENT_MAP:
        # Fallback to standard if unknown strategy
        strategy = "standard"

    print(f"Rx Request: Model={base_model}, Strategy={strategy}")

    # 2. Instantiate Agent, forwarding any optional hyperparameters
    agent_class = AGENT_MAP[strategy]
    params = request.parameters
    try:
        agent = agent_class(model=base_model, **params)
    except TypeError:
        agent = agent_class(model=base_model)

    # 3. Stream Response with timing
    async def response_generator():
        start_time = time.time()
        first_token_time = None
        chunk_count = 0
        try:
            for chunk in agent.stream(request.prompt):
                if first_token_time is None:
                    first_token_time = time.time()
                chunk_count += 1
                data = {
                    "model": request.model,
                    "created_at": "2023-01-01T00:00:00.000000Z",
                    "response": chunk,
                    "done": False,
                }
                yield json.dumps(data) + "\n"
                if chunk_count % 10 == 0:
                    await asyncio.sleep(0)

            end_time = time.time()
            total_duration = int((end_time - start_time) * 1e9)
            ttft_ns = int((first_token_time - start_time) * 1e9) if first_token_time else 0

            data = {
                "model": request.model,
                "created_at": "2023-01-01T00:00:00.000000Z",
                "response": "",
                "done": True,
                "total_duration": total_duration,
                "load_duration": ttft_ns,
                "prompt_eval_count": 0,
                "eval_count": chunk_count,
            }
            yield json.dumps(data) + "\n"
        except Exception as e:
            err_data = {"response": f"\n\n[Error in Reasoning Agent: {str(e)}]", "done": True}
            yield json.dumps(err_data) + "\n"

    return StreamingResponse(response_generator(), media_type="application/x-ndjson")


@app.post("/api/generate_structured")
async def generate_structured(request: Request):
    """Structured streaming: yields StreamEvent objects as NDJSON."""
    body = await request.json()

    model_name = body.get("model", "gemma3:latest")
    prompt = body.get("prompt", "")
    params = body.get("parameters", {})

    parts = model_name.split("+", 1)
    base_model = parts[0]
    strategy = parts[1] if len(parts) > 1 else "standard"

    agent_class = AGENT_MAP.get(strategy)
    if not agent_class:
        return JSONResponse({"error": f"Unknown strategy: {strategy}"}, status_code=400)

    try:
        agent = agent_class(model=base_model, **params)
    except TypeError:
        agent = agent_class(model=base_model)

    async def event_stream():
        try:
            if hasattr(agent, "stream_structured"):
                for event in agent.stream_structured(prompt):
                    yield json.dumps(event.to_dict()) + "\n"
            else:
                # Fallback: wrap plain text chunks as text events
                for chunk in agent.stream(prompt):
                    event_data = {
                        "event_type": "text",
                        "data": {"content": chunk},
                        "is_update": False,
                    }
                    yield json.dumps(event_data) + "\n"
            # Final done marker
            yield json.dumps({"event_type": "done", "data": {}, "is_update": False}) + "\n"
        except Exception as e:
            yield (
                json.dumps({"event_type": "error", "data": {"message": str(e)}, "is_update": False})
                + "\n"
            )

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.get("/api/tags")
async def tags():
    """Return available model+strategy combinations (Ollama-compatible)."""
    from agent_reasoning.agent_metadata import PRIMARY_AGENT_IDS

    strategies = sorted(s for s in PRIMARY_AGENT_IDS if s in AGENT_MAP)
    return {"models": [{"name": f"gemma3:270m+{s}"} for s in strategies]}


@app.get("/api/agents")
async def list_agents():
    """List available reasoning agents with full metadata."""
    agents = get_agent_list()
    return {"agents": agents, "count": len(agents)}


@app.post("/api/debug/start")
async def debug_start(request: Request):
    body = await request.json()
    model_name = body.get("model", "gemma3:latest")
    prompt = body.get("prompt", "")
    params = body.get("parameters", {})

    parts = model_name.split("+", 1)
    base_model = parts[0]
    strategy = parts[1] if len(parts) > 1 else "standard"

    agent_class = AGENT_MAP.get(strategy)
    if not agent_class:
        return JSONResponse({"error": f"Unknown strategy: {strategy}"}, status_code=400)

    session_id = str(uuid.uuid4())[:8]
    step_event = threading.Event()
    event_queue = queue.Queue(maxsize=100)

    try:
        agent = agent_class(model=base_model, _debug_event=step_event, **params)
    except TypeError:
        agent = agent_class(model=base_model, _debug_event=step_event)

    def run_agent():
        try:
            if hasattr(agent, "stream_structured"):
                for event in agent.stream_structured(prompt):
                    if agent._debug_cancelled:
                        break
                    event_queue.put(event.to_dict())
                    agent._debug_pause()
            else:
                for chunk in agent.stream(prompt):
                    if agent._debug_cancelled:
                        break
                    event_queue.put(
                        {"event_type": "text", "data": {"content": chunk}, "is_update": False}
                    )
                    agent._debug_pause()
        except Exception as e:
            event_queue.put(
                {"event_type": "error", "data": {"message": str(e)}, "is_update": False}
            )
        finally:
            event_queue.put(None)  # sentinel

    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()

    with debug_sessions_lock:
        debug_sessions[session_id] = {
            "agent": agent,
            "event": step_event,
            "queue": event_queue,
            "thread": thread,
        }

    # Signal the first step so the agent starts
    step_event.set()

    return {"session_id": session_id}


@app.post("/api/debug/step")
async def debug_step(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "")

    with debug_sessions_lock:
        if session_id not in debug_sessions:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        session = debug_sessions[session_id]

    # Get the event from the queue without blocking the event loop
    loop = asyncio.get_event_loop()
    try:
        event = await loop.run_in_executor(None, lambda: session["queue"].get(timeout=30))
    except queue.Empty:
        return JSONResponse({"error": "Timeout waiting for event"}, status_code=408)

    if event is None:
        return {"event": None, "done": True}

    # Signal agent to continue to next step
    session["event"].set()

    return {"event": event, "done": False}


@app.post("/api/debug/run")
async def debug_run(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "")

    with debug_sessions_lock:
        if session_id not in debug_sessions:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        session = debug_sessions[session_id]

    # Disable pausing
    session["agent"]._debug_event = None
    session["event"].set()

    # Drain remaining events without blocking the event loop
    loop = asyncio.get_event_loop()

    def drain_queue():
        events = []
        while True:
            try:
                event = session["queue"].get(timeout=10)
                if event is None:
                    break
                events.append(event)
            except queue.Empty:
                break
        return events

    events = await loop.run_in_executor(None, drain_queue)

    with debug_sessions_lock:
        debug_sessions.pop(session_id, None)
    return {"events": events}


@app.delete("/api/debug/{session_id}")
async def debug_cancel(session_id: str):
    with debug_sessions_lock:
        if session_id not in debug_sessions:
            return {"status": "not_found"}
        session = debug_sessions[session_id]

    session["agent"]._debug_cancelled = True
    session["event"].set()  # unblock if waiting

    with debug_sessions_lock:
        debug_sessions.pop(session_id, None)
    return {"status": "cancelled"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
