"""Flask application entry point."""

import eventlet

eventlet.monkey_patch()


from config import (  # noqa: E402
    ARCH_MODE,
    EMBEDDING_MODEL_NAME,
    FLASK_DEBUG,
    FLASK_PORT,
    FLASK_SECRET_KEY,
    OPENAI_API_KEY,
)
from flask import Flask  # noqa: E402
from flask_cors import CORS  # noqa: E402
from flask_socketio import SocketIO  # noqa: E402

# Initialize Flask + extensions
app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


def _try_connect_oracle():
    """Try to connect to Oracle. Returns conn or None."""
    try:
        from database.connection import connect_to_oracle

        conn = connect_to_oracle()
        print("  Oracle connected.")
        return conn
    except Exception as e:
        print(f"  Oracle not available: {e}")
        return None


def _try_connect_sprawl():
    """Try to connect to all sprawl databases. Returns extra dict."""
    try:
        from database.sprawl_connection import (
            connect_to_mongodb,
            connect_to_neo4j,
            connect_to_postgres,
            connect_to_qdrant,
        )
    except ImportError as e:
        print(f"  Sprawl connection modules not available: {e}")
        return None

    pg_conn = None
    neo4j_driver = None
    mongo_db = None
    qdrant_client = None

    try:
        pg_conn = connect_to_postgres()
        print("  PostgreSQL connected.")
    except Exception as e:
        print(f"  PostgreSQL not available: {e}")

    try:
        neo4j_driver = connect_to_neo4j()
        print("  Neo4j connected.")
    except Exception as e:
        print(f"  Neo4j not available: {e}")

    try:
        _mongo_client, mongo_db = connect_to_mongodb()
        print("  MongoDB connected.")
    except Exception as e:
        print(f"  MongoDB not available: {e}")

    try:
        qdrant_client = connect_to_qdrant()
        print("  Qdrant connected.")
    except Exception as e:
        print(f"  Qdrant not available: {e}")

    # Only return extra if at least PG is up (needed as primary conn for sprawl)
    if not pg_conn:
        return None

    return {
        "pg_conn": pg_conn,
        "neo4j_driver": neo4j_driver,
        "mongo_db": mongo_db,
        "qdrant_client": qdrant_client,
    }


def init_app():
    """Initialize all backend components.

    Always tries to connect to BOTH Oracle and sprawl databases.
    ARCH_MODE ('converged' or 'sprawl') controls which is the primary
    backend for normal chat messages. The Compare button on the frontend
    works automatically whenever both stacks are available — no config change needed.
    """
    mode_label = (
        "Converged (Oracle)" if ARCH_MODE != "sprawl" else "Sprawl (Postgres+Neo4j+MongoDB+Qdrant)"
    )
    print("\n=== AFSA - Agentic Financial Service Assistant - Backend Startup ===")
    print(f"=== Primary architecture: {mode_label} ===\n")

    # 1. Connect to ALL available databases
    print("[1/6] Connecting to databases...")
    oracle_conn = _try_connect_oracle()
    sprawl_extra = _try_connect_sprawl()

    # Determine primary conn + extra based on ARCH_MODE
    if ARCH_MODE == "sprawl":
        conn = sprawl_extra["pg_conn"] if sprawl_extra else None
        extra = sprawl_extra
    else:
        conn = oracle_conn
        extra = sprawl_extra  # still pass sprawl connections for comparison

    # For comparison: the "other" backend
    # If primary is converged, converged_conn is the Oracle conn used by comparison
    # If primary is sprawl, converged_conn is also Oracle (comparison always benchmarks Oracle vs sprawl)
    converged_conn = oracle_conn

    # 2. Embedding model
    print("\n[2/6] Loading embedding model...")
    from langchain_huggingface import HuggingFaceEmbeddings

    try:
        embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        print(f"  Loaded: {EMBEDDING_MODEL_NAME}")
    except Exception as e:
        print(f"  WARNING: Could not load embedding model: {e}")
        embedding_model = None

    # 3. Vector stores + memory manager
    print("\n[3/6] Initializing vector stores and memory manager...")
    knowledge_base_vs = None
    memory_manager = None
    converged_memory_manager = None

    def _init_oracle_memory(oc):
        """Helper to create an Oracle MemoryManager."""
        from langchain_community.vectorstores.utils import DistanceStrategy
        from langchain_oracledb.vectorstores import OracleVS
        from memory.manager import MemoryManager

        vs_configs = {}
        for table_name in [
            "KNOWLEDGE_BASE",
            "ENTITY_MEMORY",
            "WORKFLOW_MEMORY",
            "TOOLBOX_MEMORY",
            "SUMMARY_MEMORY",
        ]:
            vs_configs[table_name] = OracleVS(
                client=oc,
                embedding_function=embedding_model,
                table_name=table_name,
                distance_strategy=DistanceStrategy.COSINE,
            )
        mm = MemoryManager(
            conn=oc,
            conversation_table="CONVERSATIONAL_MEMORY",
            knowledge_base_vs=vs_configs["KNOWLEDGE_BASE"],
            workflow_vs=vs_configs["WORKFLOW_MEMORY"],
            toolbox_vs=vs_configs["TOOLBOX_MEMORY"],
            entity_vs=vs_configs["ENTITY_MEMORY"],
            summary_vs=vs_configs["SUMMARY_MEMORY"],
            embedding_model=embedding_model,
        )
        return mm, vs_configs["KNOWLEDGE_BASE"]

    def _init_sprawl_memory(sprawl_conns):
        """Helper to create a SprawlMemoryManager."""
        from memory.sprawl_manager import SprawlMemoryManager

        return SprawlMemoryManager(
            pg_conn=sprawl_conns["pg_conn"],
            qdrant_client=sprawl_conns.get("qdrant_client"),
            embedding_model=embedding_model,
            mongo_db=sprawl_conns.get("mongo_db"),
        )

    # Primary memory manager (based on ARCH_MODE)
    if ARCH_MODE == "sprawl":
        if sprawl_extra and embedding_model:
            try:
                memory_manager = _init_sprawl_memory(sprawl_extra)
                print("  Sprawl memory manager initialized (primary).")
            except Exception as e:
                print(f"  WARNING: Could not init sprawl memory manager: {e}")
        else:
            print("  Skipped sprawl memory (missing connections or embedding model).")
    else:
        if oracle_conn and embedding_model:
            try:
                memory_manager, knowledge_base_vs = _init_oracle_memory(oracle_conn)
                print("  Oracle memory manager initialized (primary).")
            except Exception as e:
                print(f"  WARNING: Could not init Oracle memory manager: {e}")
        else:
            print("  Skipped Oracle memory (no connection or embedding model).")

    # Secondary memory managers (for comparison — always try both)
    if oracle_conn and embedding_model:
        try:
            converged_memory_manager, kb_vs = _init_oracle_memory(oracle_conn)
            if not knowledge_base_vs:
                knowledge_base_vs = kb_vs
            print("  Oracle memory manager initialized (comparison).")
        except Exception as e:
            print(f"  Oracle memory manager for comparison not available: {e}")

    sprawl_memory_manager = None
    if sprawl_extra and embedding_model:
        try:
            sprawl_memory_manager = _init_sprawl_memory(sprawl_extra)
            print("  Sprawl memory manager initialized (comparison).")
        except Exception as e:
            print(f"  Sprawl memory manager for comparison not available: {e}")

    comparison_available = bool(
        converged_memory_manager and sprawl_memory_manager and oracle_conn and sprawl_extra
    )
    if comparison_available:
        print("  Comparison mode: AVAILABLE (both architectures connected)")
    else:
        print("  Comparison mode: NOT available (need both Oracle + sprawl running)")

    # 4. LLM client
    print("\n[4/6] Initializing OpenAI client...")
    llm_client = None
    if OPENAI_API_KEY:
        from openai import OpenAI

        llm_client = OpenAI(api_key=OPENAI_API_KEY)
        print("  OpenAI client ready.")
    else:
        print("  WARNING: No OPENAI_API_KEY set. Agent will not function.")

    # 4b. Seed toolbox (one-time LLM augmentation)
    if llm_client and memory_manager:
        print("\n[4b] Seeding toolbox memory...")
        try:
            from agent.tool_augmentation import seed_toolbox
            from agent.tools import TOOL_SCHEMAS

            seed_toolbox(memory_manager, llm_client, TOOL_SCHEMAS)
        except Exception as e:
            print(f"  WARNING: Toolbox seeding failed: {e}")
    else:
        print("\n[4b] Toolbox seeding skipped (no LLM client or memory manager).")

    # 5. Query logger
    print("\n[5/6] Initializing query logger...")
    from database.query_logger import QueryLogger

    query_logger = QueryLogger(socketio=socketio)
    print("  Query logger ready.")

    # 6. File ingestor
    print("\n[6/6] Initializing file ingestor...")
    file_ingestor = None
    if knowledge_base_vs or (ARCH_MODE == "sprawl" and memory_manager):
        try:
            from ingestion.chunker import DocumentChunker
            from ingestion.file_processor import FileProcessor
            from ingestion.ingestor import FileIngestor

            file_ingestor = FileIngestor(
                file_processor=FileProcessor(),
                chunker=DocumentChunker(),
                knowledge_base_vs=knowledge_base_vs,
                socketio=socketio,
                query_logger=query_logger,
            )
            print("  File ingestor ready.")
        except Exception as e:
            print(f"  WARNING: File ingestor failed: {e}")
            file_ingestor = None
    else:
        print("  Skipped (no knowledge base vector store).")

    # Register routes
    from api.events import init_events, register_events
    from api.routes import api_bp, init_routes

    init_routes(
        conn=conn,
        embedding_model=embedding_model,
        memory_manager=memory_manager,
        knowledge_base_vs=knowledge_base_vs,
        llm_client=llm_client,
        query_logger=query_logger,
        file_ingestor=file_ingestor,
        socketio=socketio,
    )
    app.register_blueprint(api_bp)

    init_events(
        conn=conn,
        embedding_model=embedding_model,
        memory_manager=memory_manager,
        llm_client=llm_client,
        query_logger=query_logger,
        socketio=socketio,
        extra_connections=extra,
        converged_conn=converged_conn,
        converged_memory_manager=converged_memory_manager,
        sprawl_extra=sprawl_extra,
    )
    register_events(socketio)

    print(f"\n=== Backend ready! (Primary: {mode_label}) ===")
    if comparison_available:
        print("=== Compare button enabled — both architectures connected ===\n")
    else:
        print("=== Compare button disabled — start both DB stacks to enable ===\n")


# Initialize on import
init_app()


if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
    )
