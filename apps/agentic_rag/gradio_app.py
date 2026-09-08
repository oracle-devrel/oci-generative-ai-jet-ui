import gradio as gr
import os
from typing import List, Dict, Any, Union
from pathlib import Path
import tempfile
from dotenv import load_dotenv
import yaml
import torch
import time
import requests
import json
import asyncio
import threading
from datetime import datetime

from src.pdf_processor import PDFProcessor
from src.web_processor import WebProcessor
from src.repo_processor import RepoProcessor
from src.store import VectorStore
from src.specialized_agent_cards import (
    get_planner_agent_card, 
    get_researcher_agent_card, 
    get_reasoner_agent_card, 
    get_synthesizer_agent_card
)

# Try to import OraDBVectorStore
try:
    from src.OraDBVectorStore import OraDBVectorStore
    ORACLE_DB_AVAILABLE = True
except ImportError:
    ORACLE_DB_AVAILABLE = False

from src.local_rag_agent import LocalRAGAgent
from src.reasoning.rag_ensemble import RAGReasoningEnsemble

# Load environment variables and config
load_dotenv()

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config if config else {}
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return {}

# Initialize components
try:
    pdf_processor = PDFProcessor()
except Exception as e:
    print(f"Warning: PDFProcessor init failed (Oracle DB unavailable): {e}")
    pdf_processor = None
web_processor = WebProcessor()
repo_processor = RepoProcessor()

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

# Initialize agents
config = load_config()
hf_token = config.get('HUGGING_FACE_HUB_TOKEN')
max_response_length = config.get('MAX_RESPONSE_LENGTH', 2048)  # Default to 2048 if not specified
openai_key = os.getenv("OPENAI_API_KEY")

# Initialize agents with use_cot=True to ensure CoT is available
# Default to Ollama qwen3.5:9b
try:
    local_agent = LocalRAGAgent(vector_store, model_name="qwen3.5:9b", use_cot=True, max_response_length=max_response_length)
    print("Using Ollama qwen3.5:9b as default model")
except Exception as e:
    print(f"Could not initialize Ollama qwen3.5:9b: {str(e)}")
    local_agent = None
    print("No local model available")

# Initialize reasoning ensemble
reasoning_ensemble = None
try:
    reasoning_ensemble = RAGReasoningEnsemble(
        model_name="qwen3.5:9b",
        vector_store=vector_store,
        event_logger=None
    )
    print("Reasoning ensemble initialized")
except Exception as e:
    print(f"Could not initialize reasoning ensemble: {str(e)}")

openai_agent = None

# A2A Client for testing
class A2AClient:
    """A2A client for testing A2A protocol functionality"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv('A2A_BASE_URL', 'http://localhost:8000')
        self.session = requests.Session()
        self.session.timeout = 30
    
    def make_request(self, method: str, params: Dict[str, Any], request_id: str = "1") -> Dict[str, Any]:
        """Make an A2A request"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        
        try:
            url = f"{self.base_url}/a2a"
            response = self.session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Cannot connect to API at {self.base_url}. Is the server running?"
            print(f"❌ Connection Error: {error_msg}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": error_msg,
                    "details": str(e)
                },
                "id": request_id
            }
        except requests.exceptions.Timeout as e:
            error_msg = f"Request to {self.base_url} timed out after 30 seconds"
            print(f"❌ Timeout Error: {error_msg}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": error_msg,
                    "details": str(e)
                },
                "id": request_id
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            print(f"❌ Request Error: {error_msg}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": error_msg,
                    "details": f"URL: {self.base_url}/a2a"
                },
                "id": request_id
            }
    
    def get_agent_card(self) -> Dict[str, Any]:
        """Get the agent card"""
        try:
            response = self.session.get(f"{self.base_url}/a2a/card")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to get agent card: {str(e)}"}
    
    def health_check(self) -> Dict[str, Any]:
        """Check system health"""
        try:
            response = self.session.get(f"{self.base_url}/a2a/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Health check failed: {str(e)}"}

# Initialize A2A client with configurable base URL
def get_a2a_base_url():
    """Get A2A base URL from config or environment"""
    # Try to get from config.yaml first
    config = load_config()
    agent_endpoints = config.get('AGENT_ENDPOINTS', {})
    # Use planner_url as the base URL (all agents are on same server in local setup)
    base_url = agent_endpoints.get('planner_url', 'http://localhost:8000')
    
    # Allow override via environment variable
    import os
    base_url = os.getenv('A2A_BASE_URL', base_url)
    
    return base_url

a2a_base_url = get_a2a_base_url()
a2a_client = A2AClient(base_url=a2a_base_url)
print(f"✅ A2A Client initialized with base URL: {a2a_base_url}")
print(f"   Make sure the API server is running on {a2a_base_url}")

# Global task tracking for A2A testing
a2a_tasks = {}
a2a_task_counter = 0

def process_pdf(file: Union[tempfile._TemporaryFileWrapper, Any]) -> str:
    """Process uploaded PDF file"""
    try:
        # Handle both file objects and file paths
        file_path = file.name if hasattr(file, 'name') else str(file)
        chunks, document_id = pdf_processor.process_pdf(file_path)
        vector_store.add_pdf_chunks(chunks, document_id=document_id)
        
        # Log A2A/API event
        print(f"✅ [A2A Event] Method: document.upload | Type: pdf | Chunks: {len(chunks)} | Status: success")
        
        return f"✓ Successfully processed PDF and added {len(chunks)} chunks to knowledge base (ID: {document_id})"
    except Exception as e:
        print(f"❌ [A2A Event] Method: document.upload | Type: pdf | Status: error | Message: {str(e)}")
        return f"✗ Error processing PDF: {str(e)}"

def process_url(url: str) -> str:
    """Process web content from URL"""
    try:
        # Process URL and get chunks
        chunks = web_processor.process_url(url)
        if not chunks:
            return "✗ No content extracted from URL"
            
        # Add chunks to vector store with URL as source ID
        vector_store.add_web_chunks(chunks, source_id=url)
        
        # Log A2A/API event
        print(f"✅ [A2A Event] Method: document.upload | Type: web | Chunks: {len(chunks)} | Status: success")
        
        return f"✓ Successfully processed URL and added {len(chunks)} chunks to knowledge base"
    except Exception as e:
        print(f"❌ [A2A Event] Method: document.upload | Type: web | Status: error | Message: {str(e)}")
        return f"✗ Error processing URL: {str(e)}"

def process_repo(repo_path: str) -> str:
    """Process repository content"""
    try:
        # Process repository and get chunks
        chunks, document_id = repo_processor.process_repo(repo_path)
        if not chunks:
            return "✗ No content extracted from repository"
            
        # Add chunks to vector store
        vector_store.add_repo_chunks(chunks, document_id=document_id)
        
        # Log A2A/API event
        print(f"✅ [A2A Event] Method: document.upload | Type: repo | Chunks: {len(chunks)} | Status: success")
        
        return f"✓ Successfully processed repository and added {len(chunks)} chunks to knowledge base (ID: {document_id})"
    except Exception as e:
        print(f"❌ [A2A Event] Method: document.upload | Type: repo | Status: error | Message: {str(e)}")
        return f"✗ Error processing repository: {str(e)}"

def convert_to_messages_format(history):
    """Normalize history to Gradio 6 chatbot messages."""
    if not history:
        return []
    if history and isinstance(history[0], dict):
        normalized = []
        for item in history:
            content = item.get("content")
            if content is None:
                continue
            normalized.append(
                {
                    "role": item.get("role", "assistant"),
                    "content": content,
                }
            )
        return normalized

    messages = []
    for item in history:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            user_content, assistant_content = item
            if user_content is not None:
                messages.append({"role": "user", "content": user_content})
            if assistant_content is not None:
                messages.append({"role": "assistant", "content": assistant_content})
        elif isinstance(item, str):
            messages.append({"role": "assistant", "content": item})
    return messages

def sanitize_history(history):
    """Sanitize and convert history to Gradio 6 chatbot messages."""
    return convert_to_messages_format(history)

def chat(message: str, history, agent_type: str, use_cot: bool, collection: str):
    """Process chat message using selected agent and collection"""
    try:
        print("\n" + "="*50)
        print(f"New message received: {message}")
        print(f"Agent: {agent_type}, CoT: {use_cot}, Collection: {collection}")
        print("="*50 + "\n")
        
        # Determine if we should skip analysis based on collection and interface type
        # Skip analysis for General Knowledge or when using standard chat interface (not CoT)
        skip_analysis = collection == "General Knowledge" or not use_cot
        
        # Map collection names to actual collection names in vector store
        collection_mapping = {
            "PDF Collection": "pdf_documents",
            "Repository Collection": "repository_documents",
            "Web Knowledge Base": "web_documents",
            "General Knowledge": "general_knowledge"
        }
        
        # Get the actual collection name
        actual_collection = collection_mapping.get(collection, "pdf_documents")
        
        # Parse agent type to determine model and quantization
        quantization = None
        model_name = None
        
        if "4-bit" in agent_type:
            quantization = "4bit"
            model_type = "Local (Mistral)"
        elif "8-bit" in agent_type:
            quantization = "8bit"
            model_type = "Local (Mistral)"
        elif agent_type == "openai":
            model_type = "OpenAI"
        else:
            # All other models are treated as Ollama models
            model_type = "Ollama"
            model_name = agent_type
        
        # Normalize incoming history to list of dicts for internal processing
        if history:
            normalized = []
            for item in history:
                if isinstance(item, dict) and "role" in item:
                    normalized.append(item)
                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    if item[0] is not None:
                        normalized.append({"role": "user", "content": str(item[0])})
                    if item[1] is not None:
                        normalized.append({"role": "assistant", "content": str(item[1])})
            history = normalized
        else:
            history = []
        
        # Select appropriate agent and reinitialize with correct settings
        if model_type == "OpenAI":
            response_text = "OpenAI support has been removed in favor of local Ollama models."
            print(f"Error: {response_text}")
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response_text})
            return sanitize_history(history)
        elif model_type == "Local (Mistral)":
            # For HF models, we need the token
            if not hf_token:
                response_text = "Local agent not available. Please check your HuggingFace token configuration."
                print(f"Error: {response_text}")
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": response_text})
                return sanitize_history(history)
            agent = LocalRAGAgent(vector_store, use_cot=use_cot, collection=collection, 
                                 skip_analysis=skip_analysis, quantization=quantization, max_response_length=max_response_length)
        else:  # Ollama models
            try:
                agent = LocalRAGAgent(vector_store, model_name=model_name, use_cot=use_cot, 
                                     collection=collection, skip_analysis=skip_analysis, max_response_length=max_response_length)
            except Exception as e:
                response_text = f"Error initializing Ollama model: {str(e)}"
                print(f"Error: {response_text}")
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": response_text})
                return sanitize_history(history)
        
        # Process query and get response
        print("Processing query...")
        response = agent.process_query(message)
        print("Query processed successfully")
        
        # Handle string responses from Ollama models
        if isinstance(response, str):
            response = {
                "answer": response,
                "reasoning_steps": [response] if use_cot else [],
                "context": []
            }
        
        # Format response with reasoning steps if CoT is enabled
        if use_cot and isinstance(response, dict) and "reasoning_steps" in response:
            formatted_response = "🤔 Let me think about this step by step:\n\n"
            print("\nChain of Thought Reasoning Steps:")
            print("-" * 50)
            
            # Add each reasoning step with conclusion
            for i, step in enumerate(response["reasoning_steps"], 1):
                step_text = f"Step {i}:\n{step}\n"
                formatted_response += step_text
                print(step_text)
                
                # Add intermediate response to chat history to show progress
                history.append({"role": "assistant", "content": f"🔄 Step {i} Conclusion:\n{step}"})
            
            # Add final answer
            print("\nFinal Answer:")
            print("-" * 50)
            final_answer = "\n🎯 Final Answer:\n" + response.get("answer", "No answer provided")
            formatted_response += final_answer
            print(final_answer)
            
            # Add sources if available
            if response.get("context"):
                print("\nSources Used:")
                print("-" * 50)
                sources_text = "\n📚 Sources used:\n"
                formatted_response += sources_text
                print(sources_text)
                
                for ctx in response["context"]:
                    if isinstance(ctx, dict) and "metadata" in ctx:
                        source = ctx["metadata"].get("source", "Unknown")
                        if "page_numbers" in ctx["metadata"]:
                            pages = ctx["metadata"].get("page_numbers", [])
                            source_line = f"- {source} (pages: {pages})\n"
                        else:
                            file_path = ctx["metadata"].get("file_path", "Unknown")
                            source_line = f"- {source} (file: {file_path})\n"
                        formatted_response += source_line
                        print(source_line)
            
            # Add final formatted response to history
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": formatted_response})
        else:
            # For standard response (no CoT)
            formatted_response = response.get("answer", "No answer provided") if isinstance(response, dict) else str(response)
            print("\nStandard Response:")
            print("-" * 50)
            print(formatted_response)
            
            # Add sources if available
            if isinstance(response, dict) and response.get("context"):
                print("\nSources Used:")
                print("-" * 50)
                sources_text = "\n\n📚 Sources used:\n"
                formatted_response += sources_text
                print(sources_text)
                
                for ctx in response["context"]:
                    if isinstance(ctx, dict) and "metadata" in ctx:
                        source = ctx["metadata"].get("source", "Unknown")
                        if "page_numbers" in ctx["metadata"]:
                            pages = ctx["metadata"].get("page_numbers", [])
                            source_line = f"- {source} (pages: {pages})\n"
                        else:
                            file_path = ctx["metadata"].get("file_path", "Unknown")
                            source_line = f"- {source} (file: {file_path})\n"
                        formatted_response += source_line
                        print(source_line)
            
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": formatted_response})
        
        print("\n" + "="*50)
        print("Response complete")
        print("="*50 + "\n")
        
        return sanitize_history(history)
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        print(f"\nError occurred:")
        print("-" * 50)
        print(error_msg)
        print("="*50 + "\n")
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
        return sanitize_history(history)

# A2A Testing Functions
def test_a2a_health() -> str:
    """Test A2A health check"""
    try:
        response = a2a_client.health_check()
        if response.get("error"):
            return f"❌ Health Check Failed: {response['error']}"
        else:
            return f"✅ Health Check Passed: {json.dumps(response, indent=2)}"
    except Exception as e:
        return f"❌ Health Check Error: {str(e)}"

def test_a2a_agent_card() -> str:
    """Test A2A agent card retrieval"""
    try:
        response = a2a_client.get_agent_card()
        if response.get("error"):
            return f"❌ Agent Card Failed: {response['error']}"
        else:
            return f"✅ Agent Card Retrieved: {json.dumps(response, indent=2)}"
    except Exception as e:
        return f"❌ Agent Card Error: {str(e)}"

def test_a2a_document_query(query: str, collection: str, use_cot: bool) -> str:
    """Test A2A document query"""
    try:
        # Map collection names to A2A collection format
        collection_mapping = {
            "PDF Collection": "PDF",
            "Repository Collection": "Repository", 
            "Web Knowledge Base": "Web",
            "General Knowledge": "General"
        }
        a2a_collection = collection_mapping.get(collection, "General")
        
        response = a2a_client.make_request(
            "document.query",
            {
                "query": query,
                "collection": a2a_collection,
                "use_cot": use_cot,
                "max_results": 3
            },
            f"query-{int(time.time())}"
        )
        
        if response.get("error"):
            return f"❌ Document Query Failed: {json.dumps(response['error'], indent=2)}"
        else:
            result = response.get("result", {})
            answer = result.get("answer", "No answer provided")
            sources = result.get("sources", {})
            reasoning = result.get("reasoning_steps", [])
            
            response_text = f"✅ Document Query Success:\n\n"
            response_text += f"Answer: {answer}\n\n"
            
            if reasoning:
                response_text += f"Reasoning Steps:\n"
                for i, step in enumerate(reasoning, 1):
                    response_text += f"{i}. {step}\n"
                response_text += "\n"
            
            if sources:
                response_text += f"Sources: {json.dumps(sources, indent=2)}\n"
            
            return response_text
    except Exception as e:
        return f"❌ Document Query Error: {str(e)}"

def test_a2a_task_create(task_type: str, task_params: str) -> str:
    """Test A2A task creation"""
    global a2a_task_counter
    try:
        # Parse task parameters
        try:
            params = json.loads(task_params) if task_params.strip() else {}
        except json.JSONDecodeError:
            params = {"description": task_params}
        
        a2a_task_counter += 1
        task_id = f"gradio-task-{a2a_task_counter}"
        
        response = a2a_client.make_request(
            "task.create",
            {
                "task_type": task_type,
                "params": params
            },
            task_id
        )
        
        if response.get("error"):
            return f"❌ Task Creation Failed: {json.dumps(response['error'], indent=2)}"
        else:
            result = response.get("result", {})
            created_task_id = result.get("task_id", "unknown")
            
            # Store task for tracking
            a2a_tasks[created_task_id] = {
                "id": created_task_id,
                "type": task_type,
                "params": params,
                "created_at": datetime.now().isoformat(),
                "status": "created"
            }
            
            return f"✅ Task Created Successfully:\n\nTask ID: {created_task_id}\nType: {task_type}\nParams: {json.dumps(params, indent=2)}\nStatus: {result.get('status', 'unknown')}"
    except Exception as e:
        return f"❌ Task Creation Error: {str(e)}"

def test_a2a_task_status(task_id: str) -> str:
    """Test A2A task status check"""
    try:
        response = a2a_client.make_request(
            "task.status",
            {"task_id": task_id},
            f"status-{int(time.time())}"
        )
        
        if response.get("error"):
            return f"❌ Task Status Failed: {json.dumps(response['error'], indent=2)}"
        else:
            result = response.get("result", {})
            return f"✅ Task Status Retrieved:\n\n{json.dumps(result, indent=2)}"
    except Exception as e:
        return f"❌ Task Status Error: {str(e)}"

def test_a2a_agent_discover(capability: str) -> str:
    """Test A2A agent discovery"""
    try:
        response = a2a_client.make_request(
            "agent.discover",
            {"capability": capability},
            f"discover-{int(time.time())}"
        )
        
        if response.get("error"):
            return f"❌ Agent Discovery Failed: {json.dumps(response['error'], indent=2)}"
        else:
            result = response.get("result", {})
            agents = result.get("agents", [])
            
            response_text = f"✅ Agent Discovery Success:\n\n"
            response_text += f"Capability: {capability}\n"
            response_text += f"Found {len(agents)} agents:\n\n"
            
            for i, agent in enumerate(agents, 1):
                response_text += f"{i}. {json.dumps(agent, indent=2)}\n\n"
            
            return response_text
    except Exception as e:
        return f"❌ Agent Discovery Error: {str(e)}"

def get_a2a_task_list() -> str:
    """Get list of tracked A2A tasks"""
    if not a2a_tasks:
        return "No tasks tracked yet. Create a task first."
    
    response_text = "📋 Tracked A2A Tasks:\n\n"
    for task_id, task_info in a2a_tasks.items():
        response_text += f"Task ID: {task_id}\n"
        response_text += f"Type: {task_info['type']}\n"
        response_text += f"Created: {task_info['created_at']}\n"
        response_text += f"Status: {task_info['status']}\n"
        response_text += f"Params: {json.dumps(task_info['params'], indent=2)}\n"
        response_text += "-" * 50 + "\n"
    
    return response_text

def refresh_a2a_tasks() -> str:
    """Refresh status of all tracked tasks"""
    if not a2a_tasks:
        return "No tasks to refresh."
    
    response_text = "🔄 Refreshing Task Statuses:\n\n"
    for task_id in list(a2a_tasks.keys()):
        try:
            status_response = a2a_client.make_request(
                "task.status",
                {"task_id": task_id},
                f"refresh-{int(time.time())}"
            )
            
            if not status_response.get("error"):
                result = status_response.get("result", {})
                a2a_tasks[task_id]["status"] = result.get("status", "unknown")
                response_text += f"✅ {task_id}: {result.get('status', 'unknown')}\n"
            else:
                response_text += f"❌ {task_id}: Error checking status\n"
        except Exception as e:
            response_text += f"❌ {task_id}: {str(e)}\n"
    
    return response_text

# Individual test functions for quick test suite
def test_individual_health() -> str:
    """Individual health test"""
    return test_a2a_health()

def test_individual_card() -> str:
    """Individual agent card test"""
    return test_a2a_agent_card()

def test_individual_discover() -> str:
    """Individual agent discovery test"""
    return test_a2a_agent_discover("document.query")

def test_individual_query() -> str:
    """Individual document query test"""
    return test_a2a_document_query("What is machine learning?", "General Knowledge", False)

def test_individual_task() -> str:
    """Individual task creation test"""
    return test_a2a_task_create("individual_test", '{"description": "Individual test task", "test_type": "quick"}')

# A2A Chat Interface Functions
def a2a_chat(message: str, history, agent_type: str, use_cot: bool, collection: str):
    """Process chat message using A2A protocol with distributed specialized agents for CoT"""
    try:
        print("\n" + "="*50)
        print(f"A2A Chat - New message: {message}")
        print(f"Agent: {agent_type}, CoT: {use_cot}, Collection: {collection}")
        print("A2A Client base URL:", a2a_client.base_url)
        print("="*50 + "\n")
        
        # Convert input history to messages format for processing
        # history comes from Gradio state, maintain it
        current_history = history if history else []
        
        # Map collection names to A2A collection format
        collection_mapping = {
            "PDF Collection": "PDF",
            "Repository Collection": "Repository", 
            "Web Knowledge Base": "Web",
            "General Knowledge": "General"
        }
        a2a_collection = collection_mapping.get(collection, "General")
        
        # Helper to format and append messages
        def append_msg(role, content, is_intermediate=False):
            if is_intermediate:
                content = f"*{content}*"
            current_history.append({"role": role, "content": content})
            return current_history

        # Initial user message
        current_history.append({"role": "user", "content": message})
        yield sanitize_history(current_history)

        if use_cot:
            # Use distributed specialized agents via A2A protocol
            print("🔄 Using distributed CoT agents via A2A protocol...")
            
            # Start Task
            task_id = f"a2a-chat-{int(time.time())}"
            start_msg = f"🏁 **Starting new A2A task...**\nTarget Query: {message}\nTask ID: `{task_id}`"
            append_msg("assistant", start_msg)
            yield sanitize_history(current_history)
            time.sleep(0.5)

            # Step 1: Planning
            append_msg("assistant", "🔍 **Orchestrator**: Discovering Planner Agents...", is_intermediate=True)
            yield sanitize_history(current_history)
            time.sleep(1)
            
            append_msg("assistant", "✅ Selected: **Planner A (v1.0)**", is_intermediate=True)
            yield sanitize_history(current_history)
            time.sleep(0.5)

            print("\n1️⃣ Calling Planner Agent...")
            max_retries = 5
            steps = []
            plan = ""
            
            for attempt in range(1, max_retries + 1):
                planner_response = a2a_client.make_request(
                    "agent.query",
                    {
                        "agent_id": "planner_agent_v1",
                        "query": message,
                        "context": []
                    },
                    f"planner-{int(time.time())}-{attempt}"
                )
                
                if planner_response.get("error"):
                    print(f"   ⚠️ Planner Error (attempt {attempt})")
                    if attempt == max_retries:
                         append_msg("assistant", f"❌ Planner failed after {max_retries} attempts.", is_intermediate=True)
                         yield sanitize_history(current_history)
                         return
                    continue
                
                planner_result = planner_response.get("result", {})
                plan = planner_result.get("plan", "")
                steps = planner_result.get("steps", [])
                
                if not steps:
                    steps = [s.strip() for s in plan.split("\n") if s.strip() and not s.strip().startswith("Step")]
                
                if steps:
                    break
            
            # Format Plan
            plan_display = f"📋 **Planner A (v1.0)**: Decomposing task into sub-steps...\n\n"
            for step in steps:
                plan_display += f"- {step}\n"
            
            append_msg("assistant", plan_display, is_intermediate=True)
            yield sanitize_history(current_history)
            time.sleep(1)
            
            # Collect reasoning steps
            reasoning_steps = []
            all_context = []
            
            # Process each step: Research → Reason
            for i, step in enumerate(steps[:4], 1):  # Limit to 4 steps
                if not step.strip():
                    continue
                
                # Step 2: Research
                append_msg("assistant", "🔍 **Orchestrator**: Discovering Researcher Agents...", is_intermediate=True)
                yield sanitize_history(current_history)
                time.sleep(1)
                
                selected_researcher = "Researcher A (Web)" if collection == "Web Knowledge Base" else "Researcher B (PDF/Vector)"
                append_msg("assistant", f"✅ Selected: **{selected_researcher}**", is_intermediate=True)
                yield sanitize_history(current_history)
                time.sleep(0.5)
                
                append_msg("assistant", f"🔬 **{selected_researcher}**: Gathering information regarding: *{step}*...", is_intermediate=True)
                yield sanitize_history(current_history)
                time.sleep(1)

                researcher_response = a2a_client.make_request(
                    "agent.query",
                    {
                        "agent_id": "researcher_agent_v1",
                        "query": message,
                        "step": step,
                        "context": []
                    },
                    f"researcher-{i}-{int(time.time())}"
                )
                
                findings = []
                if not researcher_response.get("error"):
                    findings = researcher_response.get("result", {}).get("findings", [])
                
                all_context.extend(findings)
                
                # Display Retrieved Vectors
                if findings:
                    vector_msg = "**Retrieved Vectors:**\n"
                    for idx, finding in enumerate(findings):
                        content_preview = finding.get('content', '')[:150].replace('\n', ' ') + "..."
                        source = finding.get('metadata', {}).get('source', 'Unknown')
                        vector_msg += f"- `vec_{idx}`: {content_preview} (Source: {source})\n"
                else:
                    vector_msg = "**Retrieved Vectors:**\nNo relevant vectors found."
                
                append_msg("assistant", vector_msg, is_intermediate=True)
                yield sanitize_history(current_history)
                time.sleep(1.5)

                # Step 3: Reason
                append_msg("assistant", "🔍 **Orchestrator**: Discovering Reasoner Agents...", is_intermediate=True)
                yield sanitize_history(current_history)
                time.sleep(1)
                
                append_msg("assistant", "✅ Selected: **Reasoner A (DeepThink)**", is_intermediate=True)
                yield sanitize_history(current_history)
                time.sleep(0.5)

                append_msg("assistant", f"🧠 **Reasoner A (DeepThink)**: Analyzing findings...", is_intermediate=True)
                yield sanitize_history(current_history)
                time.sleep(1)

                reasoner_response = a2a_client.make_request(
                    "agent.query",
                    {
                        "agent_id": "reasoner_agent_v1",
                        "query": message,
                        "step": step,
                        "context": findings
                    },
                    f"reasoner-{i}-{int(time.time())}"
                )
                
                conclusion = "Unable to reason"
                if not reasoner_response.get("error"):
                    conclusion = reasoner_response.get("result", {}).get("conclusion", "")
                
                reasoning_steps.append(conclusion)
                # Ensure conclusion is displayed
                # append_msg("assistant", f"**Analysis:**\n{conclusion}", is_intermediate=True)
                # yield sanitize_history(current_history)
            
            # Step 4: Synthesize
            append_msg("assistant", "🔍 **Orchestrator**: Discovering Synthesizer Agents...", is_intermediate=True)
            yield sanitize_history(current_history)
            time.sleep(1)
            
            append_msg("assistant", "✅ Selected: **Synthesizer A (Creative)**", is_intermediate=True)
            yield sanitize_history(current_history)
            time.sleep(0.5)
            
            append_msg("assistant", "✍️ **Synthesizer A (Creative)**: Compiling final response...", is_intermediate=True)
            yield sanitize_history(current_history)
            time.sleep(1.5)
            
            synthesizer_response = a2a_client.make_request(
                "agent.query",
                {
                    "agent_id": "synthesizer_agent_v1",
                    "query": message,
                    "reasoning_steps": reasoning_steps,
                    "context": all_context
                },
                f"synthesizer-{int(time.time())}"
            )
            
            if synthesizer_response.get("error"):
                error_msg = f"Synthesizer Error: {synthesizer_response['error']}"
                append_msg("assistant", error_msg)
                yield sanitize_history(current_history)
                return
            
            final_answer = synthesizer_response.get("result", {}).get("answer", "No answer provided")
            
            # Format final response similar to demo
            formatted_response = f"**Final Answer:**\n{final_answer}"
            
            if all_context:
                formatted_response += "\n\n**Sources Used:**\n"
                seen_sources = set()
                for ctx in all_context:
                    if isinstance(ctx, dict) and "metadata" in ctx:
                        source = ctx["metadata"].get("source", "Unknown")
                        if source not in seen_sources:
                            formatted_response += f"- {source}\n"
                            seen_sources.add(source)
            
            append_msg("assistant", formatted_response)
            yield sanitize_history(current_history)
            
            append_msg("assistant", "🎉 **Task Completed Successfully!**")
            append_msg("assistant", f"📝 **Task Status**: COMPLETED\nTask ID: `{task_id}`")
            yield sanitize_history(current_history)
            
        else:
            # Standard mode - use document.query without CoT
            print("📝 Using standard A2A document query...")
            response = a2a_client.make_request(
                "document.query",
                {
                    "query": message,
                    "collection": a2a_collection,
                    "use_cot": False,
                    "max_results": 5
                },
                f"chat-{int(time.time())}"
            )
            
            if response.get("error"):
                error_msg = f"A2A Error: {json.dumps(response['error'], indent=2)}"
                append_msg("assistant", error_msg)
                yield sanitize_history(current_history)
                return
            
            result = response.get("result", {})
            answer = result.get("answer", "No answer provided")
            
            append_msg("assistant", answer)
            yield sanitize_history(current_history)

    except Exception as e:
        error_msg = f"A2A Chat Error: {str(e)}"
        print(f"\nA2A Chat Error:")
        print("-" * 50)
        print(error_msg)
        import traceback
        print(traceback.format_exc())
        print("="*50 + "\n")
        
        # Ensure we don't crash the UI
        if current_history:
             current_history.append({"role": "assistant", "content": f"⚠️ Error: {error_msg}"})
        else:
             current_history = [{"role": "assistant", "content": f"⚠️ Error: {error_msg}"}]
             
        yield sanitize_history(current_history)


# Unified Reasoning Chat Function
def unified_reasoning_chat(
    message: str,
    history,
    model: str,
    use_rag: bool,
    collection: str,
    strategies: list,
    tot_depth: int,
    consistency_samples: int,
    reflection_turns: int
):
    """
    Unified chat function that handles reasoning ensemble.
    Yields: (execution_trace, strategy_responses, final_answer) as streaming updates.
    """
    global reasoning_ensemble
    if not message or not message.strip():
        yield "", "", ""
        return

    if not strategies:
        strategies = ["cot"]  # Default to CoT

    # Build config from advanced settings
    config = {}
    if "tot" in strategies:
        config["tot"] = {"depth": tot_depth}
    if "consistency" in strategies:
        config["consistency"] = {"samples": consistency_samples}
    if "self_reflection" in strategies:
        config["self_reflection"] = {"max_turns": reflection_turns}

    # Map collection names
    collection_mapping = {
        "PDF Collection": "PDF",
        "Repository Collection": "Repository",
        "Web Knowledge Base": "Web",
        "General Knowledge": "General"
    }
    mapped_collection = collection_mapping.get(collection, "PDF")

    # Run ensemble with streaming
    if reasoning_ensemble:
        try:
            # Update ensemble model if dropdown selection differs
            if model and model != reasoning_ensemble.model_name:
                reasoning_ensemble = RAGReasoningEnsemble(
                    model_name=model,
                    vector_store=vector_store,
                    event_logger=None
                )
                print(f"[Reasoning] Switched ensemble model to: {model}")

            # Stream execution events for real-time UI updates
            trace_lines = []
            execution_trace = ""
            strategy_responses = ""
            final_answer = "⏳ Processing..."

            # Yield initial state
            yield execution_trace, strategy_responses, final_answer

            # Collect events from async streaming generator
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def collect_events():
                events = []
                async for event in reasoning_ensemble.run_with_streaming(
                    query=message,
                    strategies=strategies,
                    use_rag=use_rag,
                    collection=mapped_collection,
                    config=config if config else None
                ):
                    events.append(event)
                return events

            all_events = loop.run_until_complete(collect_events())
            loop.close()

            # Process events and yield updates
            final_result = None
            for event in all_events:
                if event.event_type == 'result' and event.data and 'result' in event.data:
                    final_result = event.data['result']
                else:
                    trace_lines.append(f"{event.timestamp} │ {event.message}")
                    execution_trace = "\n".join(trace_lines)
                    yield execution_trace, strategy_responses, final_answer

            # Format final results
            if final_result:
                result = final_result
                response_blocks = []
                for resp in result.all_responses:
                    is_winner = resp["strategy"] == result.winner["strategy"]
                    icon = reasoning_ensemble.get_strategy_icon(resp["strategy"])
                    name = reasoning_ensemble.get_strategy_display_name(resp["strategy"])
                    duration = resp["duration_ms"] / 1000
                    winner_badge = "🏆 " if is_winner else ""
                    vote_info = f" ({result.winner['vote_count']} votes)" if is_winner and result.voting_details else ""
                    resp_text = resp["response"]
                    block = f"""### {winner_badge}{icon} {name}{vote_info} ⏱️ {duration:.1f}s

{resp_text}
"""
                    response_blocks.append(block)

                strategy_responses = "\n---\n".join(response_blocks)

                sources_text = ""
                if result.rag_context and result.rag_context.get("sources"):
                    sources_text = "\n\n📚 **Sources:** " + ", ".join(result.rag_context["sources"])

                final_answer = result.winner["response"] + sources_text
                yield execution_trace, strategy_responses, final_answer
            else:
                final_answer = "No result received from ensemble."
                yield execution_trace, strategy_responses, final_answer

        except Exception as e:
            error_msg = f"Error running reasoning ensemble: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            yield f"Error: {str(e)}", "", f"⚠️ {error_msg}"
    else:
        yield "Reasoning ensemble not available", "", "Reasoning ensemble not initialized. Please check the configuration."


# Custom CSS for A2A Trace (module level for Gradio 6.0 compatibility)
CUSTOM_CSS = """
#a2a_trace_log .message-wrap .message {
    max-width: 100% !important;
    width: 100% !important;
}
#a2a_trace_log .message-wrap {
    max-width: 100% !important;
}
"""

def create_interface():
    """Create Gradio interface"""

    # Helper function to render Agent Cards
    def render_agent_cards():
        with gr.Accordion("View Agent Cards", open=True):
            gr.Markdown("### Registered Agent Cards")
            
            from src.specialized_agent_cards import get_all_specialized_agent_cards
            all_cards = get_all_specialized_agent_cards()
            
            # Create tabs for each agent type card
            with gr.Tabs():
                with gr.Tab("Planners"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### Planner A (v1.0)")
                            gr.JSON(value=all_cards.get("planner_agent_v1", {}))
                        with gr.Column():
                            gr.Markdown("#### Planner B (v1.1)")
                            gr.JSON(value=all_cards.get("planner_agent_v2", {}))
                with gr.Tab("Researchers"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### Researcher A (Web)")
                            gr.JSON(value=all_cards.get("researcher_agent_v1", {}))
                        with gr.Column():
                            gr.Markdown("#### Researcher B (Vector)")
                            gr.JSON(value=all_cards.get("researcher_agent_v2", {}))
                with gr.Tab("Reasoners"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### Reasoner A (DeepThink)")
                            gr.JSON(value=all_cards.get("reasoner_agent_v1", {}))
                        with gr.Column():
                            gr.Markdown("#### Reasoner B (QuickLogic)")
                            gr.JSON(value=all_cards.get("reasoner_agent_v2", {}))
                with gr.Tab("Synthesizers"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### Synthesizer A (Creative)")
                            gr.JSON(value=all_cards.get("synthesizer_agent_v1", {}))
                        with gr.Column():
                            gr.Markdown("#### Synthesizer B (Concise)")
                            gr.JSON(value=all_cards.get("synthesizer_agent_v2", {}))

    with gr.Blocks(title="Agentic RAG System") as interface:
            gr.Markdown("""
            # 🤖 Agentic RAG System
            
            Upload PDFs, process web content, repositories, and chat with your documents using local or OpenAI models.
            
            > **Note on Performance**: When using the Local (Mistral) model, initial loading can take 1-5 minutes, and each query may take 30-60 seconds to process depending on your hardware. OpenAI queries are typically much faster.
            """)
            
            # Show Oracle DB status
            if ORACLE_DB_AVAILABLE and hasattr(vector_store, 'connection'):
                gr.Markdown("""
                <div style="padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 15px;">
                ✅ <strong>Oracle AI Database 26ai</strong> is active and being used for vector storage.
                </div>
                """)
            else:
                gr.Markdown("""
                <div style="padding: 10px; background-color: #f8d7da; color: #721c24; border-radius: 5px; margin-bottom: 15px;">
                ⚠️ <strong>ChromaDB</strong> is being used for vector storage. Oracle AI Database 26ai is not available.
                </div>
                """)
            
            # Create model choices list dynamically from Ollama
            model_choices = []
            default_model = "qwen3.5:9b"
            try:
                import ollama as _ollama_check
                _ollama_models = _ollama_check.list().models
                model_choices = [m.model for m in _ollama_models]
                print(f"[UI] Loaded {len(model_choices)} models from Ollama: {model_choices}")
                # Pick a sensible default from available models
                if model_choices:
                    for preferred in ["qwen3.5:9b", "qwen3.5:35b-a3b", "qwen3:8b"]:
                        if preferred in model_choices:
                            default_model = preferred
                            break
                    else:
                        default_model = model_choices[0]
            except Exception as _e:
                print(f"[UI] Could not fetch Ollama models: {_e}. Using fallback list.")
                model_choices = ["qwen3.5:9b", "phi3:latest"]
            if openai_key:
                model_choices.append("openai")
            
            # Wrapper for all tabs to ensure they are grouped together
            with gr.Tabs():
                # Model Management Tab (First Tab)
                with gr.Tab("Model Management"):
                    gr.Markdown("""
                    ## Model Selection
                    Choose your preferred model for the conversation.
                    """)
                
                    with gr.Row():
                        with gr.Column():
                            model_dropdown = gr.Dropdown(
                                choices=model_choices,
                                value=default_model,
                                label="Select Model",
                                info="Choose the model to use for the conversation"
                            )
                            download_button = gr.Button("Download Selected Model")
                            model_status = gr.Textbox(
                                label="Download Status",
                                placeholder="Select a model and click Download to begin...",
                                interactive=False
                            )
                
                    # Add model FAQ section
                    gr.Markdown("""
                    ## Model FAQ
                    
                    | Model | Parameters | Size | Download Command |
                    |-------|------------|------|------------------|
                    | qwq | 32B | 20GB | qwq:latest |
                    | qwen3.5 | 9B | ~5.7GB | qwen3.5:9b |
                    | llama3.3 | 70B | 43GB | llama3.3:latest |
                    | phi4 | 14B | 9.1GB | phi4:latest |
                    | mistral | 7B | 4.1GB | mistral:latest |
                    | llava | 7B | 4.5GB | llava:latest |
                    | phi3 | 4B | 4.0GB | phi3:latest |
                    | deepseek-r1 | 7B | 4.7GB | deepseek-r1:latest |
                    
                    Note: All models are available through Ollama. Make sure Ollama is running on your system.
                    """)
                
                # Document Processing Tab
                with gr.Tab("Document Processing"):
                    with gr.Row():
                        with gr.Column():
                            pdf_file = gr.File(label="Upload PDF")
                            pdf_button = gr.Button("Process PDF")
                            pdf_output = gr.Textbox(label="PDF Processing Output")
                            
                        with gr.Column():
                            url_input = gr.Textbox(label="Enter URL")
                            url_button = gr.Button("Process URL")
                            url_output = gr.Textbox(label="URL Processing Output")
                            
                        with gr.Column():
                            repo_input = gr.Textbox(label="Enter Repository Path or URL")
                            repo_button = gr.Button("Process Repository")
                            repo_output = gr.Textbox(label="Repository Processing Output")
            
                # Define collection choices once to ensure consistency
                collection_choices = [
                "PDF Collection",
                "Repository Collection", 
                "Web Knowledge Base",
                "General Knowledge"
                ]
            
                # Chat Interface Tab (formerly A2A Chat Interface)
                with gr.Tab("Chat"):
                    gr.Markdown("""
                    # 🤖 Chat Interface
                    
                    Chat with your documents using the A2A (Agent2Agent) protocol. This interface provides agent-to-agent 
                    interaction capabilities while maintaining a familiar chat experience.
                    

                    """)
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            a2a_agent_dropdown = gr.Dropdown(
                                choices=model_choices,
                                value=default_model if default_model in model_choices else model_choices[0] if model_choices else None,
                                label="Select Agent",
                                info="Agent selection (for display purposes - A2A server handles the actual model)"
                            )
                        with gr.Column(scale=1):
                            a2a_collection_dropdown = gr.Dropdown(
                                choices=collection_choices,
                                value=collection_choices[0],
                                label="Select Knowledge Base",
                                info="Choose which knowledge base to use for answering questions"
                            )
                    
                    # CoT is enabled by default for A2A Chat
                    a2a_use_cot_state = gr.State(value=True)
                    
                    a2a_chatbot = gr.Chatbot(height=400, label="A2A Chat", type="messages")
                    with gr.Row():
                        a2a_msg = gr.Textbox(label="Your Message", scale=8, placeholder="Ask a question...")
                        a2a_clear_button = gr.Button("Clear", scale=1, variant="secondary")
                        a2a_send = gr.Button("Send", scale=1, variant="primary")
                    
                    gr.Markdown("""
                    > **Collection Selection**: 
                    > - When a specific collection is selected, the A2A server will use that collection:
                    >   - "PDF Collection": Will search the PDF documents via A2A
                    >   - "Repository Collection": Will search the repository code via A2A
                    >   - "Web Knowledge Base": Will search web content via A2A
                    >   - "General Knowledge": Will use the model's built-in knowledge via A2A
                    > - All communication goes through the A2A protocol for agent-to-agent interaction
                    """)
            
                # Unified Reasoning Chat Tab
                with gr.Tab("Reasoning Chat"):
                    gr.Markdown("""
                    # 🧠 Unified Reasoning Chat
                    
                    Chat with advanced reasoning strategies. Select one or multiple strategies to run in parallel 
                    with ensemble voting. Enable RAG to ground responses in your documents.
                    """)
                    
                    # Settings bar
                    with gr.Row():
                        with gr.Column(scale=1):
                            reasoning_model_dropdown = gr.Dropdown(
                                choices=model_choices,
                                value=default_model if default_model in model_choices else model_choices[0] if model_choices else None,
                                label="Model",
                                info="Select the LLM model for reasoning"
                            )
                        with gr.Column(scale=1):
                            reasoning_rag_toggle = gr.Checkbox(
                                value=True,
                                label="RAG Enabled",
                                info="Retrieve context from documents before reasoning"
                            )
                        with gr.Column(scale=1):
                            reasoning_collection_dropdown = gr.Dropdown(
                                choices=collection_choices,
                                value=collection_choices[0],
                                label="Collection",
                                info="Knowledge base to query for context"
                            )
                    
                    # Strategy selector
                    gr.Markdown("### Reasoning Strategies")
                    all_strategy_values = ["cot", "tot", "react", "self_reflection", "consistency", "decomposed", "least_to_most", "recursive", "standard"]
                    with gr.Row():
                        reasoning_strategies = gr.CheckboxGroup(
                            choices=[
                                ("🔗 Chain-of-Thought", "cot"),
                                ("🌳 Tree of Thoughts", "tot"),
                                ("🛠️ ReAct", "react"),
                                ("🪞 Self-Reflection", "self_reflection"),
                                ("🔄 Self-Consistency", "consistency"),
                                ("🧩 Decomposed", "decomposed"),
                                ("📈 Least-to-Most", "least_to_most"),
                                ("🔁 Recursive", "recursive"),
                                ("📝 Standard", "standard")
                            ],
                            value=["cot"],
                            label="Select strategies (multiple = ensemble voting)",
                            info="Select one for direct response, or multiple for parallel execution with majority voting"
                        )
                    with gr.Row():
                        toggle_all_strategies_btn = gr.Button("Toggle All Strategies", variant="secondary", size="sm")
                    
                    # Advanced settings (collapsible)
                    with gr.Accordion("⚙️ Advanced Settings", open=False):
                        with gr.Row():
                            reasoning_tot_depth = gr.Slider(
                                minimum=1, maximum=5, value=3, step=1,
                                label="ToT Depth",
                                info="Number of levels in Tree of Thoughts exploration"
                            )
                            reasoning_consistency_samples = gr.Slider(
                                minimum=1, maximum=7, value=3, step=1,
                                label="Consistency Samples",
                                info="Number of samples for Self-Consistency voting"
                            )
                            reasoning_reflection_turns = gr.Slider(
                                minimum=1, maximum=5, value=3, step=1,
                                label="Reflection Turns",
                                info="Max iterations for Self-Reflection refinement"
                            )
                    
                    # Strategy responses (expanded by default)
                    with gr.Accordion("📊 Strategy Responses", open=True):
                        reasoning_strategy_responses = gr.Textbox(
                            lines=10,
                            label="",
                            placeholder="Strategy responses will appear here after running the ensemble...",
                            interactive=False
                        )

                    # Execution trace (collapsible)
                    with gr.Accordion("🔄 Execution Trace", open=False):
                        reasoning_execution_trace = gr.Textbox(
                            lines=8,
                            label="",
                            placeholder="Execution trace will appear here...",
                            interactive=False
                        )

                    # Final answer display
                    gr.Markdown("### 💬 Final Answer")
                    reasoning_final_answer = gr.Textbox(
                        lines=6,
                        label="",
                        placeholder="Ask a question to see the reasoning result...",
                        interactive=False
                    )
                    
                    # Input area
                    with gr.Row():
                        reasoning_msg = gr.Textbox(
                            label="Your Question",
                            placeholder="Type your question here...",
                            scale=6
                        )
                        reasoning_send = gr.Button("Send", variant="primary", scale=1)
                        reasoning_clear = gr.Button("Clear", variant="secondary", scale=1)
                    
                    # Event handlers for Unified Reasoning Chat
                    def clear_reasoning_chat():
                        return "", "", ""

                    def toggle_all_strategies(current_strategies):
                        """Toggle between all strategies selected and none selected."""
                        if len(current_strategies) == len(all_strategy_values):
                            return []
                        return all_strategy_values

                    def reasoning_chat_wrapper(message, model, use_rag, collection, strategies, tot_depth, consistency_samples, reflection_turns):
                        """Streaming wrapper that yields updates as ensemble progresses."""
                        for execution_trace, strategy_responses, final_answer in unified_reasoning_chat(
                            message, [], model, use_rag, collection, strategies, tot_depth, consistency_samples, reflection_turns
                        ):
                            yield execution_trace, strategy_responses, final_answer

                    toggle_all_strategies_btn.click(
                        toggle_all_strategies,
                        inputs=[reasoning_strategies],
                        outputs=[reasoning_strategies]
                    )

                    reasoning_send.click(
                        reasoning_chat_wrapper,
                        inputs=[
                            reasoning_msg,
                            reasoning_model_dropdown,
                            reasoning_rag_toggle,
                            reasoning_collection_dropdown,
                            reasoning_strategies,
                            reasoning_tot_depth,
                            reasoning_consistency_samples,
                            reasoning_reflection_turns
                        ],
                        outputs=[
                            reasoning_execution_trace,
                            reasoning_strategy_responses,
                            reasoning_final_answer
                        ],
                        api_visibility="private"
                    ).then(
                        lambda: "",
                        outputs=reasoning_msg
                    )

                    reasoning_msg.submit(
                        reasoning_chat_wrapper,
                        inputs=[
                            reasoning_msg,
                            reasoning_model_dropdown,
                            reasoning_rag_toggle,
                            reasoning_collection_dropdown,
                            reasoning_strategies,
                            reasoning_tot_depth,
                            reasoning_consistency_samples,
                            reasoning_reflection_turns
                        ],
                        outputs=[
                            reasoning_execution_trace,
                            reasoning_strategy_responses,
                            reasoning_final_answer
                        ],
                        api_visibility="private"
                    ).then(
                        lambda: "",
                        outputs=reasoning_msg
                    )
                    
                    reasoning_clear.click(
                        clear_reasoning_chat,
                        outputs=[
                            reasoning_execution_trace,
                            reasoning_strategy_responses,
                            reasoning_final_answer
                        ],
                        api_visibility="private"
                    )

                # A2A Testing Tab
                with gr.Tab("A2A Protocol Testing"):
                    gr.Markdown("""
                    # 🤖 A2A Protocol Testing Interface
                    
                    Test the Agent2Agent (A2A) protocol functionality. Make sure the A2A server is running on `localhost:8000`.
                    
                    > **Note**: This interface tests the A2A protocol by making HTTP requests to the A2A server. 
                    > The server must be running separately using `python main.py`.
                    """)
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 🔍 Basic A2A Tests")
                            
                            # Health Check
                            health_button = gr.Button("🏥 Health Check", variant="secondary")
                            health_output = gr.Textbox(label="Health Check Result", lines=5, interactive=False)
                            
                            # Agent Card
                            agent_card_button = gr.Button("🃏 Get Agent Card", variant="secondary")
                            agent_card_output = gr.Textbox(label="Agent Card Result", lines=8, interactive=False)
                            
                            # Agent Discovery
                            with gr.Row():
                                discover_capability = gr.Textbox(
                                    label="Capability to Discover", 
                                    value="document.query",
                                    placeholder="e.g., document.query, task.create"
                                )
                                discover_button = gr.Button("🔍 Discover Agents", variant="secondary")
                            discover_output = gr.Textbox(label="Agent Discovery Result", lines=6, interactive=False)
                    
                        with gr.Column(scale=1):
                            gr.Markdown("### 📄 Document Query Testing")
                            
                            with gr.Row():
                                a2a_query = gr.Textbox(
                                    label="Query", 
                                    value="What is artificial intelligence?",
                                    placeholder="Enter your question"
                                )
                                a2a_collection = gr.Dropdown(
                                    choices=["PDF Collection", "Repository Collection", "Web Knowledge Base", "General Knowledge"],
                                    value="General Knowledge",
                                    label="Collection"
                                )
                            
                            a2a_use_cot = gr.Checkbox(label="Use Chain of Thought", value=False)
                            a2a_query_button = gr.Button("🔍 Query Documents", variant="primary")
                            a2a_query_output = gr.Textbox(label="Document Query Result", lines=10, interactive=False)
                
                    gr.Markdown("---")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 📋 Task Management")
                            
                            with gr.Row():
                                task_type = gr.Textbox(
                                    label="Task Type", 
                                    value="document_processing",
                                    placeholder="e.g., document_processing, analysis_task"
                                )
                                task_params = gr.Textbox(
                                    label="Task Parameters (JSON)", 
                                    value='{"document": "test.pdf", "chunk_count": 10}',
                                    placeholder='{"key": "value"}'
                                )
                            
                            task_create_button = gr.Button("➕ Create Task", variant="primary")
                            task_create_output = gr.Textbox(label="Task Creation Result", lines=6, interactive=False)
                            
                            with gr.Row():
                                task_id_input = gr.Textbox(
                                    label="Task ID to Check", 
                                    placeholder="Enter task ID from creation result"
                                )
                                task_status_button = gr.Button("📊 Check Task Status", variant="secondary")
                            task_status_output = gr.Textbox(label="Task Status Result", lines=6, interactive=False)
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### 📊 Task Management Dashboard")
                            
                            task_list_button = gr.Button("📋 Show All Tasks", variant="secondary")
                            task_refresh_button = gr.Button("🔄 Refresh Task Statuses", variant="secondary")
                            task_dashboard_output = gr.Textbox(label="Task Dashboard", lines=12, interactive=False)
                    
                    gr.Markdown("---")
                    
                    with gr.Row():
                        gr.Markdown("""
                        ### 🚀 Quick Test Suite
                        
                        Run individual A2A tests or all tests in sequence to verify the complete functionality.
                        """)
                        
                        with gr.Column(scale=1):
                            gr.Markdown("**Individual Tests:**")
                            individual_health_button = gr.Button("🏥 Test Health", variant="secondary", size="sm")
                            individual_card_button = gr.Button("🃏 Test Agent Card", variant="secondary", size="sm")
                            individual_discover_button = gr.Button("🔍 Test Discovery", variant="secondary", size="sm")
                            individual_query_button = gr.Button("📄 Test Query", variant="secondary", size="sm")
                            individual_task_button = gr.Button("📋 Test Task", variant="secondary", size="sm")
                        
                        with gr.Column(scale=1):
                            gr.Markdown("**Complete Test Suite:**")
                            run_all_tests_button = gr.Button("🧪 Run All A2A Tests", variant="primary", size="lg")
                        
                        all_tests_output = gr.Textbox(label="Test Results", lines=15, interactive=False)

                # A2A Demo Tab
                with gr.Tab("A2A Demo"):
                    gr.Markdown("## A2A Agent Swapping Demo")
                    gr.Markdown("This demo showcases the Agent-to-Agent (A2A) Protocol's ability to dynamically swap agents based on availability. Toggle agent availability and run tasks to see the orchestrator automatically select the best available agent.")
                    
                    # State for agent availability
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 1. Agent Availability")
                            gr.Markdown("Toggle which agents are available to accept tasks.")
                            
                            # Planner
                            gr.Markdown("#### Planner Agents")
                            planner_a_status = gr.Checkbox(label="Planner Agent A (v1.0)", value=True)
                            planner_b_status = gr.Checkbox(label="Planner Agent B (v1.1 - Fast)", value=True)
                            
                            # Researcher
                            gr.Markdown("#### Researcher Agents")
                            researcher_a_status = gr.Checkbox(label="Researcher Agent A (Web)", value=True)
                            researcher_b_status = gr.Checkbox(label="Researcher Agent B (PDF/Vector)", value=True)
                            
                            # Reasoner
                            gr.Markdown("#### Reasoner Agents")
                            reasoner_a_status = gr.Checkbox(label="Reasoner Agent A (DeepThink)", value=True)
                            reasoner_b_status = gr.Checkbox(label="Reasoner Agent B (QuickLogic)", value=True)
                            
                            # Synthesizer
                            gr.Markdown("#### Synthesizer Agents")
                            synthesizer_a_status = gr.Checkbox(label="Synthesizer Agent A (Creative)", value=True)
                            synthesizer_b_status = gr.Checkbox(label="Synthesizer Agent B (Concise)", value=True)
    
                        with gr.Column(scale=3):
                            gr.Markdown("### 2. Task Simulation")
                            
                            with gr.Row():
                                demo_task_btn = gr.Button("🚀 Start Multi-Agent Task", variant="primary")
                                swap_scenario_btn = gr.Button("🔄 Simulate Researcher Swap")
                            
                            gr.Markdown("### 3. Execution Trace")
                            demo_log_output = gr.Chatbot(label="Task Trace", height=600, elem_id="a2a_trace_log", type="messages")
                            
                            # Hidden state to store current log (history)
                            demo_log_state = gr.State(value=[])
                        
                    # Agent Card Display Area
                    with gr.Row():
                        render_agent_cards()
                        



                # Simulation Logic
                def run_demo_simulation(p_a, p_b, res_a, res_b, rea_a, rea_b, syn_a, syn_b, current_history):
                    import time
                    import random
                    
                    # Generate a mock Task ID
                    task_id = f"a2a-demo-{int(time.time())}-{random.randint(1000, 9999)}"
                    
                    # Helper for assistant log messages in Gradio's messages format.
                    def msg(content):
                        # Log to stdout
                        print(f"[A2A Demo Trace] {content}")
                        return {"role": "assistant", "content": content}

                    # Helper for user messages
                    def user_msg(content):
                        return {"role": "user", "content": content}

                    new_history = list(current_history) if current_history else []
                    
                    if not new_history:
                         new_history.append(msg(f"🏁 **Starting new A2A demo simulation tasks...**\nTarget Query: `What are Generative Adversarial Networks (GANs)?`\nTask ID: `{task_id}`"))
                    else:
                        new_history.append(msg("---"))
                        new_history.append(msg(f"🏁 **Starting new task cycle...**\nTarget Query: `What are Generative Adversarial Networks (GANs)?`\nTask ID: `{task_id}`"))
                    
                    yield new_history, new_history
                    time.sleep(1)

                    # 1. Discovery & Planning
                    new_history.append(msg("🔍 **Orchestrator**: Discovering Planner Agents..."))
                    yield new_history, new_history
                    time.sleep(1.5) # Simulate processing
                    
                    selected_planner = None
                    if p_a:
                        selected_planner = "Planner A (v1.0)"
                    elif p_b:
                        selected_planner = "Planner B (v1.1)"
                    
                    if not selected_planner:
                        new_history.append(msg("❌ No Planner Agents available! Task failed."))
                        new_history.append(msg(f"📝 **Task Status**: FAILED\nTask ID: `{task_id}`"))
                        yield new_history, new_history
                        return
                    
                    if not p_a and p_b:
                        new_history.append(msg(f"⚠️ Planner A is BUSY. Swapping to available agent..."))
                        yield new_history, new_history
                        time.sleep(1)
                    
                    new_history.append(msg(f"✅ Selected: **{selected_planner}**"))
                    new_history.append(msg(f"📋 {selected_planner}: Decomposing task into sub-steps...\n1. Define GANs\n2. Explain architecture (Generator/Discriminator)\n3. List applications"))
                    yield new_history, new_history
                    time.sleep(2)
                    
                    # 2. Research
                    new_history.append(msg("🔍 **Orchestrator**: Discovering Researcher Agents..."))
                    yield new_history, new_history
                    time.sleep(1.5)
                    
                    selected_researcher = None
                    if res_a:
                        selected_researcher =   "Researcher A (Web)"
                    elif res_b:
                        selected_researcher = "Researcher B (PDF/Vector)"
                    
                    if not selected_researcher:
                        new_history.append(msg("❌ No Researcher Agents available! Task failed."))
                        new_history.append(msg(f"📝 **Task Status**: FAILED\nTask ID: `{task_id}`"))
                        yield new_history, new_history
                        return
                        
                    if not res_a and res_b:
                        new_history.append(msg(f"⚠️ Researcher A is BUSY. Swapping to available agent..."))
                        yield new_history, new_history
                        time.sleep(1)

                    new_history.append(msg(f"✅ Selected: **{selected_researcher}**"))
                    new_history.append(msg(f"🔬 {selected_researcher}: Gathering information..."))
                    yield new_history, new_history
                    time.sleep(1)
                    
                    # Real Vector Retrieval (Standardized format)
                    try:
                        # Query vector store for the GANs topic
                        # We try Web collection first, then General, then fallback
                        demo_query = "What are Generative Adversarial Networks (GANs)?"
                        real_results = []
                        
                        if hasattr(vector_store, 'query_web_collection'):
                            real_results = vector_store.query_web_collection(demo_query)
                        
                        if not real_results and hasattr(vector_store, 'query_general_collection'):
                             real_results = vector_store.query_general_collection(demo_query)
                        
                        # Format the output
                        if real_results:
                            vector_output = "**Retrieved Vectors:**\n"
                            for i, res in enumerate(real_results):
                                content_preview = res.get('content', '')[:100].replace('\n', ' ') + "..."
                                source = res.get('metadata', {}).get('source', 'Unknown')
                                vector_output += f"- `vec_{i}`: {content_preview} (Source: {source})\n"
                        else:
                            vector_output = "**Retrieved Vectors:**\nNo relevant vectors found in the knowledge base for this query."
                            
                    except Exception as e:
                        vector_output = f"**Retrieved Vectors:**\nError retrieving vectors: {str(e)}"

                    new_history.append(msg(vector_output.strip()))
                    yield new_history, new_history
                    time.sleep(2)
                    
                    # 3. Reasoning
                    new_history.append(msg("🔍 **Orchestrator**: Discovering Reasoner Agents..."))
                    yield new_history, new_history
                    time.sleep(1.5)
                    
                    selected_reasoner = None
                    if rea_a:
                        selected_reasoner = "Reasoner A (DeepThink)"
                    elif rea_b:
                        selected_reasoner = "Reasoner B (QuickLogic)"
                    
                    if not selected_reasoner:
                        new_history.append(msg("❌ No Reasoner Agents available! Task failed."))
                        new_history.append(msg(f"📝 **Task Status**: FAILED\nTask ID: `{task_id}`"))
                        yield new_history, new_history
                        return
                    
                    if not rea_a and rea_b:
                        new_history.append(msg(f"⚠️ Reasoner A is BUSY. Swapping to available agent..."))
                        yield new_history, new_history
                        time.sleep(1)

                    new_history.append(msg(f"✅ Selected: **{selected_reasoner}**"))
                    new_history.append(msg(f"🧠 {selected_reasoner}: Analyzing findings..."))
                    yield new_history, new_history
                    time.sleep(2)
                    
                    # 4. Synthesis
                    new_history.append(msg("🔍 **Orchestrator**: Discovering Synthesizer Agents..."))
                    yield new_history, new_history
                    time.sleep(1.5)
                    
                    selected_synthesizer = None
                    if syn_a:
                        selected_synthesizer = "Synthesizer A (Creative)"
                    elif syn_b:
                        selected_synthesizer = "Synthesizer B (Concise)"
                    
                    if not selected_synthesizer:
                        new_history.append(msg("❌ No Synthesizer Agents available! Task failed."))
                        new_history.append(msg(f"📝 **Task Status**: FAILED\nTask ID: `{task_id}`"))
                        yield new_history, new_history
                        return

                    if not syn_a and syn_b:
                        new_history.append(msg(f"⚠️ Synthesizer A is BUSY. Swapping to available agent..."))
                        yield new_history, new_history
                        time.sleep(1)

                    new_history.append(msg(f"✅ Selected: **{selected_synthesizer}**"))
                    new_history.append(msg(f"✍️ {selected_synthesizer}: Compiling final response..."))
                    yield new_history, new_history
                    time.sleep(2)
                    
                    # Final Response
                    final_response = """
**Final Answer:**
Generative Adversarial Networks (GANs) are a class of machine learning frameworks designed by Ian Goodfellow and his colleagues in 2014. They consist of two neural networks contesting with each other in a game (in the sense of game theory, often but not exclusively in the form of a zero-sum game).

**Key Components:**
*   **Generator:** Creates candidates (generative part) and tries to fool the discriminator.
*   **Discriminator:** Evaluates candidates (discriminative part) and tries to distinguish true data from fake data.

**Applications:**
*   Image generation and editing
*   Super-resolution
*   Text-to-image synthesis
*   Data augmentation
                    """.strip()
                    new_history.append(msg(final_response))
                    yield new_history, new_history
                    
                    new_history.append(msg("🎉 **Task Completed Successfully!**"))
                    new_history.append(msg(f"📝 **Task Status**: COMPLETED\nTask ID: `{task_id}`"))
                    yield new_history, new_history

                # Event Listeners
                demo_task_btn.click(
                    run_demo_simulation,
                    inputs=[
                        planner_a_status, planner_b_status,
                        researcher_a_status, researcher_b_status,
                        reasoner_a_status, reasoner_b_status,
                        synthesizer_a_status, synthesizer_b_status,
                        demo_log_state
                    ],
                    outputs=[demo_log_output, demo_log_state]
                )
                
                swap_scenario_btn.click(
                    lambda: (False, True), # Make Res A Busy, Res B Available
                    outputs=[researcher_a_status, researcher_b_status]
                ).then(
                    run_demo_simulation,
                    inputs=[
                        planner_a_status, planner_b_status,
                        researcher_a_status, researcher_b_status,
                        reasoner_a_status, reasoner_b_status,
                        synthesizer_a_status, synthesizer_b_status,
                        demo_log_state
                    ],
                    outputs=[demo_log_output, demo_log_state]
                )
            
            # Event handlers
            pdf_button.click(process_pdf, inputs=[pdf_file], outputs=[pdf_output], api_visibility="private")
            url_button.click(process_url, inputs=[url_input], outputs=[url_output], api_visibility="private")
            repo_button.click(process_repo, inputs=[repo_input], outputs=[repo_output], api_visibility="private")
            
            # Model download event handler
            download_button.click(download_model, inputs=[model_dropdown], outputs=[model_status], api_visibility="private")
            
            # Standard and CoT handlers removed

            
            # A2A Testing Event Handlers
            health_button.click(test_a2a_health, outputs=[health_output], api_visibility="private")
            agent_card_button.click(test_a2a_agent_card, outputs=[agent_card_output], api_visibility="private")
            discover_button.click(test_a2a_agent_discover, inputs=[discover_capability], outputs=[discover_output], api_visibility="private")
            a2a_query_button.click(test_a2a_document_query, inputs=[a2a_query, a2a_collection, a2a_use_cot], outputs=[a2a_query_output], api_visibility="private")
            task_create_button.click(test_a2a_task_create, inputs=[task_type, task_params], outputs=[task_create_output], api_visibility="private")
            task_status_button.click(test_a2a_task_status, inputs=[task_id_input], outputs=[task_status_output], api_visibility="private")
            task_list_button.click(get_a2a_task_list, outputs=[task_dashboard_output], api_visibility="private")
            task_refresh_button.click(refresh_a2a_tasks, outputs=[task_dashboard_output], api_visibility="private")
            
            # Run all tests function
            def run_all_a2a_tests():
                """Run all A2A tests in sequence"""
                results = []
                results.append("🧪 Running Complete A2A Test Suite")
                results.append("=" * 60)
                
                # Test 1: Health Check
                results.append("\n1. 🏥 Health Check")
                results.append("-" * 30)
                health_result = test_a2a_health()
                results.append(health_result)
                
                # Test 2: Agent Card
                results.append("\n2. 🃏 Agent Card")
                results.append("-" * 30)
                card_result = test_a2a_agent_card()
                results.append(card_result)
                
                # Test 3: Agent Discovery
                results.append("\n3. 🔍 Agent Discovery")
                results.append("-" * 30)
                discover_result = test_a2a_agent_discover("document.query")
                results.append(discover_result)
                
                # Test 4: Document Query
                results.append("\n4. 📄 Document Query")
                results.append("-" * 30)
                query_result = test_a2a_document_query("What is machine learning?", "General Knowledge", False)
                results.append(query_result)
                
                # Test 5: Task Creation
                results.append("\n5. 📋 Task Creation")
                results.append("-" * 30)
                task_result = test_a2a_task_create("test_task", '{"description": "A2A test task", "priority": "high"}')
                results.append(task_result)
                
                # Test 6: Task Status (if task was created)
                if "Task ID:" in task_result and "gradio-task-" in task_result:
                    # Extract task ID from result
                    task_id = None
                    for line in task_result.split('\n'):
                        if "Task ID:" in line:
                            task_id = line.split("Task ID:")[1].strip()
                            break
                    
                    if task_id:
                        results.append("\n6. 📊 Task Status Check")
                        results.append("-" * 30)
                        status_result = test_a2a_task_status(task_id)
                        results.append(status_result)
                
                results.append("\n" + "=" * 60)
                results.append("🎉 A2A Test Suite Complete!")
                
                return "\n".join(results)
            
            run_all_tests_button.click(run_all_a2a_tests, outputs=[all_tests_output], api_visibility="private")
            
            # Individual test event handlers
            individual_health_button.click(test_individual_health, outputs=[all_tests_output], api_visibility="private")
            individual_card_button.click(test_individual_card, outputs=[all_tests_output], api_visibility="private")
            individual_discover_button.click(test_individual_discover, outputs=[all_tests_output], api_visibility="private")
            individual_query_button.click(test_individual_query, outputs=[all_tests_output], api_visibility="private")
            individual_task_button.click(test_individual_task, outputs=[all_tests_output], api_visibility="private")
            
            # A2A Chat Interface Event Handlers
            a2a_msg.submit(
                a2a_chat,
                inputs=[
                    a2a_msg,
                    a2a_chatbot,
                    a2a_agent_dropdown,
                    a2a_use_cot_state,  # Use state instead of checkbox for API generation consistency
                    a2a_collection_dropdown
                ],
                outputs=[a2a_chatbot],
                api_visibility="private"
            )
            a2a_send.click(
                a2a_chat,
                inputs=[
                    a2a_msg,
                    a2a_chatbot,
                    a2a_agent_dropdown,
                    a2a_use_cot_state,  # Use state instead of checkbox for API generation consistency
                    a2a_collection_dropdown
                ],
                outputs=[a2a_chatbot],
                api_visibility="private"
            )
            a2a_clear_button.click(lambda: [], None, a2a_chatbot, queue=False, api_visibility="private")
            # a2a_status_button removed from Chat tab
            
            # Checkbox event listener removed

            
            return interface

def main():
    # Check configuration
    try:
        import ollama
        try:
            # Check if Ollama is running and list available models
            models = ollama.list().models
            available_models = [model.model for model in models]
            
            print(f"✅ Ollama is running with {len(available_models)} models: {', '.join(available_models)}")
        except Exception as e:
            print(f"⚠️ Warning: Ollama is installed but not running or encountered an error: {str(e)}")
            print("Please start Ollama before using the interface.")
    except ImportError:
        print("⚠️ Warning: Ollama package not installed. Please install with: pip install ollama")
        
    if not hf_token and not openai_key:
        print("⚠️ Warning: Neither HuggingFace token nor OpenAI key found. Using Ollama only.")
    
    # Launch interface
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        inbrowser=True,
        theme=gr.themes.Soft(),
        css=CUSTOM_CSS
    )

def download_model(model_type: str) -> str:
    """Download a model and return status message"""
    try:
        print(f"Downloading model: {model_type}")
        
        # Parse model type to determine model and quantization
        quantization = None
        model_name = None
        
        if "4-bit" in model_type or "8-bit" in model_type:
            # For HF models, we need the token
            if not hf_token:
                return "❌ Error: HuggingFace token not found in config.yaml. Please add your token first."
            
            model_name = "mistralai/Mistral-7B-Instruct-v0.2"  # Default model
            if "4-bit" in model_type:
                quantization = "4bit"
            elif "8-bit" in model_type:
                quantization = "8bit"
                
            # Start download timer
            start_time = time.time()
            
            try:
                from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
                
                # Download tokenizer first (smaller download to check access)
                try:
                    tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
                except Exception as e:
                    if "401" in str(e):
                        return f"❌ Error: This model is gated. Please accept the terms on the Hugging Face website: https://huggingface.co/{model_name}"
                    else:
                        return f"❌ Error downloading tokenizer: {str(e)}"
                
                # Set up model loading parameters
                model_kwargs = {
                    "token": hf_token,
                    "device_map": None,  # Don't load on GPU for download only
                }
                
                # Apply quantization if specified
                if quantization == '4bit':
                    try:
                        quantization_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_compute_dtype=torch.float16,
                            bnb_4bit_use_double_quant=True,
                            bnb_4bit_quant_type="nf4"
                        )
                        model_kwargs["quantization_config"] = quantization_config
                    except ImportError:
                        return "❌ Error: bitsandbytes not installed. Please install with: pip install bitsandbytes>=0.41.0"
                elif quantization == '8bit':
                    try:
                        quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                        model_kwargs["quantization_config"] = quantization_config
                    except ImportError:
                        return "❌ Error: bitsandbytes not installed. Please install with: pip install bitsandbytes>=0.41.0"
                
                # Download model (but don't load it fully to save memory)
                AutoModelForCausalLM.from_pretrained(
                    model_name,
                    **model_kwargs
                )
                
                # Calculate download time
                download_time = time.time() - start_time
                return f"✅ Successfully downloaded {model_type} in {download_time:.1f} seconds."
                
            except Exception as e:
                return f"❌ Error downloading model: {str(e)}"
        # all ollama models
        else:
            # Extract model name from model_type
            # Remove the 'Ollama - ' prefix and any leading/trailing whitespace
            model_name = model_type.replace("Ollama - ", "").strip()
            
            # Use Ollama to pull the model
            try:
                import ollama
                
                print(f"Pulling Ollama model: {model_name}")
                start_time = time.time()
                
                # Check if model already exists
                try:
                    models = ollama.list().models
                    available_models = [model.model for model in models]
                    
                    # Check for model with or without :latest suffix
                    if model_name in available_models or f"{model_name}:latest" in available_models:
                        return f"✅ Model {model_name} is already available in Ollama."
                except Exception:
                    # If we can't check, proceed with pull anyway
                    pass
                
                # Pull the model with progress tracking
                progress_text = ""
                for progress in ollama.pull(model_name, stream=True):
                    status = progress.get('status')
                    if status:
                        progress_text = f"Status: {status}"
                        print(progress_text)
                    
                    # Show download progress
                    if 'completed' in progress and 'total' in progress:
                        completed = progress['completed']
                        total = progress['total']
                        if total > 0:
                            percent = (completed / total) * 100
                            progress_text = f"Downloading: {percent:.1f}% ({completed}/{total})"
                            print(progress_text)
                
                # Calculate download time
                download_time = time.time() - start_time
                return f"✅ Successfully pulled Ollama model {model_name} in {download_time:.1f} seconds."
                
            except ImportError:
                return "❌ Error: ollama not installed. Please install with: pip install ollama"
            except ConnectionError:
                return "❌ Error: Could not connect to Ollama. Please make sure Ollama is installed and running."
            except Exception as e:
                return f"❌ Error pulling Ollama model: {str(e)}"
    
    except Exception as e:
        return f"❌ Error: {str(e)}"

if __name__ == "__main__":
    # Start A2A API Server if not running
    import uvicorn
    import threading
    import time
    import requests
    from src.main import app as fastapi_app

    def run_api_server():
        """Run the FastAPI server in a separate thread"""
        print("🚀 Starting A2A API Server...")
        config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="error")
        server = uvicorn.Server(config)
        server.run()

    def start_api_server_if_needed():
        """Check if API server is running, if not start it"""
        try:
            requests.get(f"{a2a_base_url}/docs", timeout=1)
            print("✅ A2A API Server is already running")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            print("⚠️ A2A API Server not running. Starting it automatically...")
            api_thread = threading.Thread(target=run_api_server, daemon=True)
            api_thread.start()
            # Wait a moment for server to start
            time.sleep(2)
            print("✅ A2A API Server started in background")

    start_api_server_if_needed()
    main()
