#!/usr/bin/env python3
"""
A2A Protocol Demo Script

This script demonstrates the A2A protocol functionality by making
sample requests to the agentic_rag system.
"""

import json
import requests
from typing import Dict, Any


class A2AClient:
    """Simple A2A client for testing"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def make_request(self, method: str, params: Dict[str, Any], request_id: str = "1") -> Dict[str, Any]:
        """Make an A2A request"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/a2a",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Request failed: {str(e)}"
                },
                "id": request_id
            }
    
    def get_agent_card(self) -> Dict[str, Any]:
        """Get the agent card"""
        try:
            response = self.session.get(f"{self.base_url}/agent_card")
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


def print_response(title: str, response: Dict[str, Any]):
    """Print formatted response"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")
    print(json.dumps(response, indent=2))


def main():
    """Run A2A demo"""
    print("🤖 A2A Protocol Demo")
    print("=" * 60)
    print("This demo shows the A2A protocol functionality")
    print("Make sure the agentic_rag server is running on localhost:8000")
    print("=" * 60)
    
    client = A2AClient()
    
    # Test 1: Health Check
    print("\n1. Testing Health Check...")
    health_response = client.health_check()
    print_response("Health Check Response", health_response)
    
    # Test 2: Get Agent Card
    print("\n2. Getting Agent Card...")
    card_response = client.get_agent_card()
    print_response("Agent Card", card_response)
    
    # Test 3: Document Query
    print("\n3. Testing Document Query...")
    query_response = client.make_request(
        "document.query",
        {
            "query": "What is artificial intelligence?",
            "collection": "General",
            "use_cot": False,
            "max_results": 3
        },
        "query-1"
    )
    print_response("Document Query Response", query_response)
    
    # Test 4: Task Creation
    print("\n4. Testing Task Creation...")
    task_response = client.make_request(
        "task.create",
        {
            "task_type": "document_processing",
            "params": {
                "document": "demo_document.pdf",
                "chunk_count": 10
            }
        },
        "task-1"
    )
    print_response("Task Creation Response", task_response)
    
    # Test 5: Task Status (if task was created)
    if "result" in task_response and "task_id" in task_response["result"]:
        task_id = task_response["result"]["task_id"]
        print(f"\n5. Checking Task Status for {task_id}...")
        
        # Wait a moment for task to start
        import time
        time.sleep(2)
        
        status_response = client.make_request(
            "task.status",
            {"task_id": task_id},
            "status-1"
        )
        print_response("Task Status Response", status_response)
    
    # Test 6: Agent Discovery
    print("\n6. Testing Agent Discovery...")
    discover_response = client.make_request(
        "agent.discover",
        {"capability": "document.query"},
        "discover-1"
    )
    print_response("Agent Discovery Response", discover_response)
    
    # Test 7: Error Handling
    print("\n7. Testing Error Handling...")
    error_response = client.make_request(
        "unknown.method",
        {"param": "value"},
        "error-1"
    )
    print_response("Error Response", error_response)
    
    print("\n" + "="*60)
    print("🎉 A2A Demo completed!")
    print("="*60)


if __name__ == "__main__":
    main()
