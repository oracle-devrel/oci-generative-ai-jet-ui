"""Flask + Socket.IO entry point.
Mirrors finance-ai-agent-demo's app.py shape: connect → init memory → init tools →
register API blueprint and socket events → run."""

import eventlet  # noqa: E402

eventlet.monkey_patch()


from flask import Flask  # noqa: E402
from flask_cors import CORS  # noqa: E402
from flask_socketio import SocketIO  # noqa: E402

from config import FLASK_DEBUG, FLASK_PORT, FLASK_SECRET_KEY  # noqa: E402


app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


def init_app():
    print("\n=== Enterprise Data Agent — Backend Startup ===\n")

    print("[1/4] Connecting to Oracle...")
    from db.connection import connect_agent
    agent_conn = connect_agent()
    print("  AGENT connection ready.")

    print("\n[2/4] Initializing OAMP memory client...")
    from memory.manager import build_memory_client
    memory_client = build_memory_client(agent_conn)
    print("  Memory client ready.")

    print("\n[3/4] Initializing tools + skillbox + scratchpad + reranker...")
    from agent.skills import ensure_skillbox
    from agent.tools import init_tools
    from db.dbfs import DBFS
    from db.reranker_setup import ensure_reranker
    from db.scheduler_setup import (
        drain_queued_scans, ensure_scan_history, ensure_scheduler,
    )
    from retrieval.rerank import rerank_factory
    ensure_skillbox(agent_conn)
    ensure_scan_history(agent_conn)
    scratch = DBFS(agent_conn)
    rerank_status = ensure_reranker(agent_conn)
    rerank = rerank_factory(
        agent_conn,
        rerank_status["model_name"] if rerank_status["loaded"] else None,
    )
    print(f"  Reranker: {rerank_status['reason']} "
          f"(active={rerank_status['loaded']}, model={rerank_status['model_name']!r})")
    init_tools(agent_conn, memory_client, rerank=rerank, scratch=scratch)
    print(f"  Tools registered (scratchpad mounted at /scratch).")

    # Periodic schema-rescan job. Opt-in via SCAN_INTERVAL_MIN env (minutes
    # between scans). With it unset, no DBMS_SCHEDULER job is created;
    # scans only happen on `tool_scan_database` or POST /api/data/scan/<owner>.
    import os as _os
    from config import DEMO_USER as _DEMO
    _interval = int(_os.environ.get("SCAN_INTERVAL_MIN", "0"))
    if _interval > 0:
        sched = ensure_scheduler(agent_conn, _interval, _DEMO.upper())
        print(f"  Scheduler: {sched['reason']} "
              f"(job={sched['job_name']!r}, interval={sched['interval_min']}min, "
              f"owner={sched['owner']!r})")
        # Drain any rows the scheduler queued while we were down so the
        # institutional knowledge catches up before the first user message.
        ran = drain_queued_scans(agent_conn, memory_client)
        if ran:
            print(f"  Drained {ran} backlogged scan(s) from scan_history.")
    else:
        print("  Scheduler: not requested (set SCAN_INTERVAL_MIN to enable).")

    print("\n[4/4] Initializing LLM client...")
    from agent.llm import build_llm_client
    llm_client = build_llm_client()
    print("  LLM client ready.")

    from api.data_routes import data_bp, init_data_routes
    from api.events import init_events, register_events
    from api.routes import api_bp, init_routes
    from api.world_routes import init_world_routes, world_bp

    init_routes(agent_conn=agent_conn, memory_client=memory_client, llm_client=llm_client)
    app.register_blueprint(api_bp)

    init_data_routes(agent_conn=agent_conn, memory_client=memory_client)
    app.register_blueprint(data_bp)

    init_world_routes(agent_conn=agent_conn)
    app.register_blueprint(world_bp)

    init_events(agent_conn=agent_conn, memory_client=memory_client,
                llm_client=llm_client, socketio=socketio)
    register_events(socketio)

    print("\n=== Backend ready! ===\n")


init_app()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG)
