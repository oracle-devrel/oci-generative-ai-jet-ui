import os
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uuid
import time

from .pdf_processor import PDFProcessor
from .store import VectorStore
from .local_rag_agent import LocalRAGAgent


# Try to import OraDBVectorStore
try:
    from .OraDBVectorStore import OraDBVectorStore
    ORACLE_DB_AVAILABLE = True
except ImportError:
    ORACLE_DB_AVAILABLE = False

# A2A Protocol imports
from .a2a_models import A2ARequest, A2AResponse
from .a2a_handler import A2AHandler
from .agent_card import get_agent_card

# OpenAI-compatible API for Open WebUI integration
from .openai_compat import router as openai_router, init_openai_compat

# Settings API
from .settings import router as settings_router, register_model_change_callback

# Reasoning ensemble import
try:
    from .reasoning.rag_ensemble import RAGReasoningEnsemble
    REASONING_ENSEMBLE_AVAILABLE = True
except ImportError:
    REASONING_ENSEMBLE_AVAILABLE = False
    print("⚠️ Reasoning ensemble not available")

# Event Logger import
try:
    from .OraDBEventLogger import OraDBEventLogger
    event_logger = OraDBEventLogger()
    EVENT_LOGGING_ENABLED = True
    print("✅ Event logging enabled with Oracle DB")
except Exception as e:
    print(f"⚠️ Event logging disabled: {str(e)}")
    event_logger = None
    EVENT_LOGGING_ENABLED = False

# File handler import
try:
    from .file_handler import FileHandler
    from .file_routes import router as file_router, upload_page_router, init_file_routes
    FILE_HANDLER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ File handler not available: {str(e)}")
    FILE_HANDLER_AVAILABLE = False

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Agentic RAG API with A2A Protocol",
    description="API for processing PDFs and answering queries using an agentic RAG system with Agent2Agent (A2A) protocol support",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
try:
    pdf_processor = PDFProcessor()
except Exception as e:
    print(f"⚠️ PDFProcessor init failed (Oracle DB unavailable): {e}")
    pdf_processor = None

# Initialize vector store (prefer Oracle DB if available)
if ORACLE_DB_AVAILABLE:
    try:
        vector_store = OraDBVectorStore()
        print("Using Oracle AI Database 26ai for vector storage")
    except Exception as e:
        print(f"Error initializing Oracle DB: {str(e)}")
        print("Falling back to ChromaDB")
        vector_store = VectorStore()
else:
    vector_store = VectorStore()
    print("Using ChromaDB for vector storage (Oracle DB not available)")

# Check for Ollama availability
try:
    import ollama  # noqa: F401
    ollama_available = True
    print("\nOllama is available. You can use Ollama models for RAG.")
except ImportError:
    ollama_available = False
    print("\nOllama not installed. You can install it with: pip install ollama")

# Initialize RAG agent - using Ollama with gemma3:270m (default)
try:
    print("\nInitializing Local RAG Agent with gemma3:270m...")
    rag_agent = LocalRAGAgent(vector_store=vector_store, model_name="gemma3:270m")
    print("Successfully initialized Local RAG Agent.")
except Exception as e:
    print(f"\nFailed to initialize Local RAG Agent: {str(e)}")
    if not ollama_available:
        print("Ollama is not installed or running. Please check your configuration.")
    raise e

# Initialize A2A handler
print("\nInitializing A2A Protocol handler...")
a2a_handler = A2AHandler(rag_agent, vector_store, event_logger=event_logger if EVENT_LOGGING_ENABLED else None)
print("A2A Protocol handler initialized successfully.")

# Initialize Reasoning Ensemble for OpenAI-compatible API
reasoning_ensemble = None
if REASONING_ENSEMBLE_AVAILABLE:
    try:
        print("\nInitializing Reasoning Ensemble for OpenAI-compatible API...")
        reasoning_ensemble = RAGReasoningEnsemble(
            model_name="gemma3:270m",
            vector_store=vector_store,
            event_logger=event_logger if EVENT_LOGGING_ENABLED else None
        )
        print("Reasoning Ensemble initialized successfully.")
    except Exception as e:
        print(f"⚠️ Failed to initialize Reasoning Ensemble: {str(e)}")

# Initialize File Handler for @file references
file_handler = None
if FILE_HANDLER_AVAILABLE:
    try:
        print("\nInitializing File Handler for @file references...")
        file_handler = FileHandler(documents_dir="./documents", vector_store=vector_store)
        init_file_routes(file_handler)
        print("File Handler initialized. Documents directory: ./documents")
    except Exception as e:
        print(f"⚠️ Failed to initialize File Handler: {str(e)}")

# Initialize OpenAI-compatible API
print("\nInitializing OpenAI-compatible API (for Open WebUI)...")
init_openai_compat(
    vector_store=vector_store,
    reasoning_ensemble=reasoning_ensemble,
    local_agent=rag_agent,
    config={},
    event_logger=event_logger if EVENT_LOGGING_ENABLED else None,
    file_handler=file_handler,
    a2a_handler=a2a_handler
)
print("OpenAI-compatible API initialized successfully.")

# Include OpenAI-compatible router
app.include_router(openai_router)

# Include Settings router
app.include_router(settings_router)

# Include File routes
if FILE_HANDLER_AVAILABLE:
    app.include_router(file_router)
    app.include_router(upload_page_router)


# Register callback to update reasoning ensemble when model changes
def on_model_change(new_model_name: str):
    """Callback to reinitialize components when model changes."""
    global reasoning_ensemble, rag_agent

    print(f"\n🔄 Switching LLM model to: {new_model_name}")

    # Reinitialize reasoning ensemble
    if REASONING_ENSEMBLE_AVAILABLE:
        try:
            reasoning_ensemble = RAGReasoningEnsemble(
                model_name=new_model_name,
                vector_store=vector_store,
                event_logger=event_logger if EVENT_LOGGING_ENABLED else None
            )
            print(f"✅ Reasoning Ensemble updated to {new_model_name}")
        except Exception as e:
            print(f"⚠️ Failed to update Reasoning Ensemble: {str(e)}")

    # Reinitialize local agent
    try:
        rag_agent = LocalRAGAgent(vector_store=vector_store, model_name=new_model_name)
        print(f"✅ Local RAG Agent updated to {new_model_name}")
    except Exception as e:
        print(f"⚠️ Failed to update Local RAG Agent: {str(e)}")

    # Update OpenAI-compatible API
    init_openai_compat(
        vector_store=vector_store,
        reasoning_ensemble=reasoning_ensemble,
        local_agent=rag_agent,
        config={"model_name": new_model_name},
        event_logger=event_logger if EVENT_LOGGING_ENABLED else None,
        file_handler=file_handler,
        a2a_handler=a2a_handler
    )
    print("✅ OpenAI-compatible API updated")


register_model_change_callback(on_model_change)

class QueryRequest(BaseModel):
    query: str
    use_cot: bool = False
    model: Optional[str] = None  # Allow specifying model in the request

class QueryResponse(BaseModel):
    answer: str
    reasoning: Optional[str] = None
    context: List[dict]

@app.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file"""
    start_time = time.time()
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    temp_path = None
    try:
        # Save the uploaded file temporarily
        temp_path = f"temp_{uuid.uuid4()}.pdf"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process the PDF
        if not pdf_processor:
            raise HTTPException(status_code=503, detail="PDF processor not available (Oracle DB may be unreachable)")
        chunks, document_id = pdf_processor.process_pdf(temp_path)
        
        # Add chunks to vector store
        vector_store.add_pdf_chunks(chunks, document_id=document_id)
        
        # Clean up
        os.remove(temp_path)
        
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Log the event
        if EVENT_LOGGING_ENABLED:
            event_logger.log_document_event(
                document_type="pdf",
                document_id=document_id,
                source=file.filename,
                chunks_processed=len(chunks),
                processing_time_ms=processing_time,
                status="success"
            )
            
            event_logger.log_api_event(
                endpoint="/upload/pdf",
                method="POST",
                request_data={"filename": file.filename},
                response_data={"document_id": document_id, "chunks_processed": len(chunks)},
                status_code=200,
                duration_ms=processing_time
            )
        
        return {
            "message": "PDF processed successfully",
            "document_id": document_id,
            "chunks_processed": len(chunks)
        }
        
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Log the error
        if EVENT_LOGGING_ENABLED:
            event_logger.log_document_event(
                document_type="pdf",
                document_id="error",
                source=file.filename if file else "unknown",
                chunks_processed=0,
                processing_time_ms=processing_time,
                status="error",
                error_message=str(e)
            )
        
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Process a query using the RAG agent"""
    start_time = time.time()
    model_name = request.model if request.model else "default"
    
    try:
        # Determine which model to use
        if request.model:
            # Check if model name starts with ollama: prefix, if not add it for logging/handling purposes if needed
            # but LocalRAGAgent handles it.
            # Just instantiate LocalRAGAgent
            rag_agent = LocalRAGAgent(vector_store=vector_store, model_name=request.model, use_cot=request.use_cot)
            model_type = "ollama"
        else:
            # Use default local model initialized globally
            # But we need to handle use_cot per request, so re-init might be needed or update prop
            # LocalRAGAgent is stateful regarding use_cot? Yes in _process_query logic.
            # But here we are re-instantiating.
            rag_agent = LocalRAGAgent(vector_store=vector_store, model_name="gemma3:270m", use_cot=request.use_cot)
            model_type = "ollama"
            
        response = rag_agent.process_query(request.query)
        
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Log the event
        if EVENT_LOGGING_ENABLED:
            # Extract context info
            context_count = len(response.get("context", [])) if isinstance(response, dict) else 0
            answer = response.get("answer", "") if isinstance(response, dict) else str(response)
            
            event_logger.log_model_event(
                model_name=model_name,
                model_type=model_type,
                user_prompt=request.query,
                response=answer[:1000],  # Truncate to 1000 chars
                collection_used="default",
                use_cot=request.use_cot,
                duration_ms=processing_time,
                context_chunks=context_count
            )
            
            event_logger.log_api_event(
                endpoint="/query",
                method="POST",
                request_data={"query": request.query, "use_cot": request.use_cot, "model": model_name},
                response_data={"answer_length": len(answer), "context_chunks": context_count},
                status_code=200,
                duration_ms=processing_time
            )
        
        return response
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        
        # Log the error
        if EVENT_LOGGING_ENABLED:
            event_logger.log_api_event(
                endpoint="/query",
                method="POST",
                request_data={"query": request.query, "use_cot": request.use_cot, "model": model_name},
                response_data={"error": str(e)},
                status_code=500,
                duration_ms=processing_time
            )
        
        raise HTTPException(status_code=500, detail=str(e))

# A2A Protocol endpoints
@app.post("/a2a", response_model=A2AResponse)
async def a2a_endpoint(request: A2ARequest):
    """A2A Protocol endpoint for agent-to-agent communication"""
    start_time = time.time()
    
    try:
        response = await a2a_handler.handle_request(request)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Log A2A API event
        if EVENT_LOGGING_ENABLED:
            event_logger.log_api_event(
                endpoint="/a2a",
                method="POST",
                request_data={"method": request.method, "params": request.params},
                response_data={"result": str(response.result)[:500] if hasattr(response, 'result') else ""},
                status_code=200,
                duration_ms=processing_time
            )
        
        return response
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        
        if EVENT_LOGGING_ENABLED:
            event_logger.log_api_event(
                endpoint="/a2a",
                method="POST",
                request_data={"method": request.method, "params": request.params},
                response_data={"error": str(e)},
                status_code=500,
                duration_ms=processing_time
            )
        raise

@app.get("/agent_card")
async def get_agent_card_endpoint():
    """Get the agent card for this agent"""
    return get_agent_card()

@app.get("/a2a/health")
async def a2a_health_check():
    """A2A health check endpoint"""
    return await a2a_handler.handle_request(A2ARequest(
        method="health.check",
        params={}
    ))

# Event logging endpoints
@app.get("/events/statistics")
async def get_event_statistics():
    """Get event logging statistics"""
    if not EVENT_LOGGING_ENABLED:
        raise HTTPException(status_code=503, detail="Event logging is not enabled")
    
    try:
        stats = event_logger.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/{event_type}")
async def get_events(event_type: str, limit: int = 100):
    """Get events by type (all, a2a, api, model, document, query)"""
    if not EVENT_LOGGING_ENABLED:
        raise HTTPException(status_code=503, detail="Event logging is not enabled")
    
    valid_types = ["all", "a2a", "api", "model", "document", "query"]
    if event_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid event type. Must be one of: {', '.join(valid_types)}")
    
    try:
        events = event_logger.get_events(event_type=event_type, limit=limit)
        
        # Convert datetime objects to strings for JSON serialization
        for event in events:
            if 'TIMESTAMP' in event and event['TIMESTAMP']:
                event['TIMESTAMP'] = str(event['TIMESTAMP'])
        
        return {
            "event_type": event_type,
            "count": len(events),
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/count/{event_type}")
async def get_event_count(event_type: str):
    """Get count of events by type"""
    if not EVENT_LOGGING_ENABLED:
        raise HTTPException(status_code=503, detail="Event logging is not enabled")
    
    valid_types = ["all", "a2a", "api", "model", "document", "query"]
    if event_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid event type. Must be one of: {', '.join(valid_types)}")
    
    try:
        count = event_logger.get_event_count(event_type=event_type)
        return {
            "event_type": event_type,
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Open WebUI Embedding Sync Endpoints
class EmbeddingSyncRequest(BaseModel):
    """Request body for syncing embeddings from Open WebUI to Oracle AI Database."""
    collection_name: str
    documents: List[dict]  # List of {text: str, metadata: dict}
    source: str = "openwebui"


class EmbeddingSyncResponse(BaseModel):
    """Response for embedding sync operation."""
    status: str
    collection: str
    documents_synced: int
    message: str


@app.post("/sync/embeddings", response_model=EmbeddingSyncResponse)
async def sync_openwebui_embeddings(request: EmbeddingSyncRequest):
    """
    Sync embeddings from Open WebUI to Oracle AI Database.

    This endpoint allows Open WebUI or custom pipelines to send document
    embeddings to be stored in Oracle AI Database for unified RAG access.

    Expected document format:
    {
        "text": "document content",
        "metadata": {
            "source": "filename or url",
            "title": "optional title",
            ...
        }
    }
    """
    start_time = time.time()

    try:
        if not vector_store:
            raise HTTPException(status_code=503, detail="Vector store not initialized")

        # Prepare chunks for Oracle DB
        chunks = []
        for doc in request.documents:
            text = doc.get("text", "")
            metadata = doc.get("metadata", {})

            # Add source tracking
            metadata["synced_from"] = request.source
            metadata["original_collection"] = request.collection_name
            metadata["sync_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")

            if text:
                chunks.append({
                    "text": text,
                    "metadata": metadata
                })

        if not chunks:
            return EmbeddingSyncResponse(
                status="warning",
                collection=request.collection_name,
                documents_synced=0,
                message="No valid documents to sync"
            )

        # Determine target collection based on source type
        collection_target = "GENERALCOLLECTION"  # Default
        if "pdf" in request.collection_name.lower() or "file" in request.collection_name.lower():
            collection_target = "PDFCOLLECTION"
        elif "web" in request.collection_name.lower() or "url" in request.collection_name.lower():
            collection_target = "WEBCOLLECTION"

        # Sync to Oracle AI Database
        vector_store._add_chunks_to_collection(chunks, collection_target)

        processing_time = (time.time() - start_time) * 1000

        # Log the sync event
        if EVENT_LOGGING_ENABLED:
            event_logger.log_document_event(
                document_type="openwebui_sync",
                document_id=request.collection_name,
                source=request.source,
                chunks_processed=len(chunks),
                status="success"
            )
            event_logger.log_api_event(
                endpoint="/sync/embeddings",
                method="POST",
                request_data={
                    "collection": request.collection_name,
                    "document_count": len(request.documents),
                    "source": request.source
                },
                response_data={
                    "synced": len(chunks),
                    "target_collection": collection_target
                },
                status_code=200,
                duration_ms=processing_time
            )

        print(f"✅ [Sync] Synced {len(chunks)} documents from Open WebUI collection '{request.collection_name}' to Oracle AI Database ({collection_target})", flush=True)

        return EmbeddingSyncResponse(
            status="success",
            collection=collection_target,
            documents_synced=len(chunks),
            message=f"Successfully synced {len(chunks)} documents to {collection_target}"
        )

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000

        if EVENT_LOGGING_ENABLED:
            event_logger.log_api_event(
                endpoint="/sync/embeddings",
                method="POST",
                request_data={
                    "collection": request.collection_name,
                    "source": request.source
                },
                response_data={"error": str(e)},
                status_code=500,
                duration_ms=processing_time
            )

        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/status")
async def get_sync_status():
    """Get the current sync status and statistics."""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not initialized")

    try:
        # Get collection counts
        collections = {}
        for name in ["PDFCOLLECTION", "WEBCOLLECTION", "GENERALCOLLECTION", "REPOCOLLECTION"]:
            store = vector_store.vector_stores.get(name)
            if store:
                try:
                    # Try to get count (this is Oracle-specific)
                    collections[name] = {"status": "available"}
                except Exception:
                    collections[name] = {"status": "unknown"}
            else:
                collections[name] = {"status": "not_initialized"}

        return {
            "status": "ok",
            "vector_store": "Oracle AI Database",
            "collections": collections,
            "sync_endpoint": "/sync/embeddings"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 