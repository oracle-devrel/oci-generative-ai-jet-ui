"""
Simple API Examples for Agentic RAG System
==========================================

This script demonstrates how to make requests to the API endpoints
defined in main.py with different models and configurations.

Make sure your server is running: python main.py
"""

import requests
import json
from pathlib import Path


def make_request(method, endpoint, data=None, files=None, base_url="http://localhost:8000"):
    """
    Make a request to the Agentic RAG API
    
    Args:
        method: HTTP method ('GET', 'POST')
        endpoint: API endpoint (e.g., '/query', '/upload/pdf')
        data: JSON data for POST requests
        files: Files for multipart requests
        base_url: API base URL
    
    Returns:
        API response as dictionary
    """
    url = f"{base_url}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files)
            else:
                response = requests.post(url, json=data)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {base_url}. Is the server running?"}
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = response.json()
            return {"error": f"HTTP {e.response.status_code}: {error_detail.get('detail', str(e))}"}
        except Exception:
            return {"error": f"HTTP {e.response.status_code}: {str(e)}"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}


def print_response(response, title="Response"):
    """Pretty print the API response"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")
    
    if "error" in response:
        print(f"❌ Error: {response['error']}")
    else:
        print(json.dumps(response, indent=2, ensure_ascii=False))
    
    print(f"{'='*60}\n")


def demo_query_endpoint():
    """Demonstrate the /query endpoint from main.py"""
    print("🔍 QUERY ENDPOINT EXAMPLES")
    print("="*50)
    
    # Example 1: Basic query with auto model selection
    print("\n1. Basic Query (Auto Model Selection):")
    response = make_request("POST", "/query", {
        "query": "What is machine learning?"
    })
    print_response(response, "Basic Query Response")
    
    # Example 2: Query with OpenAI model
    print("\n2. Query with OpenAI Model:")
    response = make_request("POST", "/query", {
        "query": "Explain the difference between supervised and unsupervised learning",
        "model": "openai",
        "use_cot": True
    })
    print_response(response, "OpenAI Query with Chain of Thought")
    
    # Example 3: Query with Ollama model
    print("\n3. Query with Ollama Model:")
    response = make_request("POST", "/query", {
        "query": "What are the benefits of using vector databases?",
        "model": "ollama:llama3",
        "use_cot": False
    })
    print_response(response, "Ollama Query Response")
    
    # Example 4: Complex query with Chain of Thought
    print("\n4. Complex Query with Chain of Thought:")
    response = make_request("POST", "/query", {
        "query": "Compare and contrast RAG systems with fine-tuned language models. "
                "What are the advantages and disadvantages of each approach?",
        "use_cot": True
    })
    print_response(response, "Complex CoT Query Response")


def demo_upload_endpoint(pdf_path=None):
    """Demonstrate the /upload/pdf endpoint from main.py"""
    print("📄 UPLOAD ENDPOINT EXAMPLE")
    print("="*50)
    
    if not pdf_path:
        print("\n⚠️  No PDF file provided. Skipping upload demo.")
        print("   To test upload, provide a PDF file path.")
        return
    
    if not Path(pdf_path).exists():
        print(f"\n❌ File not found: {pdf_path}")
        return
    
    print(f"\n1. Uploading PDF: {pdf_path}")
    with open(pdf_path, 'rb') as f:
        files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
        response = make_request("POST", "/upload/pdf", files=files)
    print_response(response, "PDF Upload Response")


def demo_a2a_endpoints():
    """Demonstrate A2A protocol endpoints from main.py"""
    print("🤖 A2A PROTOCOL EXAMPLES")
    print("="*50)
    
    # Example 1: Document query via A2A
    print("\n1. Document Query via A2A:")
    response = make_request("POST", "/a2a", {
        "jsonrpc": "2.0",
        "method": "document.query",
        "params": {
            "query": "What is artificial intelligence?",
            "collection": "PDF",
            "use_cot": True
        },
        "id": "1"
    })
    print_response(response, "A2A Document Query")
    
    # Example 2: Health check via A2A
    print("\n2. Health Check via A2A:")
    response = make_request("POST", "/a2a", {
        "jsonrpc": "2.0",
        "method": "health.check",
        "params": {},
        "id": "2"
    })
    print_response(response, "A2A Health Check")
    
    # Example 3: Agent discovery via A2A
    print("\n3. Agent Discovery via A2A:")
    response = make_request("POST", "/a2a", {
        "jsonrpc": "2.0",
        "method": "agent.discover",
        "params": {
            "capability": "document.query"
        },
        "id": "3"
    })
    print_response(response, "A2A Agent Discovery")


def demo_agent_card():
    """Demonstrate the /agent_card endpoint from main.py"""
    print("📋 AGENT CARD EXAMPLE")
    print("="*50)
    
    print("\n1. Getting Agent Card:")
    response = make_request("GET", "/agent_card")
    print_response(response, "Agent Card")


def main():
    """Run example API calls"""
    
    print("🤖 Agentic RAG API Examples")
    print("="*50)
    print("Make sure your server is running: python main.py")
    print("="*50)
    
    # Run all demonstrations
    demo_query_endpoint()
    demo_upload_endpoint()  # No PDF provided, will skip
    demo_a2a_endpoints()
    demo_agent_card()
    
    print("✅ All examples completed!")
    print("\nTo test with your own queries:")
    print("python -c \"from query_examples import make_request; print(make_request('POST', '/query', {'query': 'Your question here'}))\"")
    print("\nTo test PDF upload:")
    print("python -c \"from query_examples import demo_upload_endpoint; demo_upload_endpoint('path/to/your/file.pdf')\"")


if __name__ == "__main__":
    main()
