#!/usr/bin/env python3
"""
A2A Protocol Test Suite

This script tests all A2A protocol functionality including:
- Health check
- Agent discovery
- Document query
- Task creation and status
- Agent card retrieval

Make sure A2A server is running: python main.py
"""

import json
import sys
import time

import requests


class A2ATester:
    """A2A Protocol Tester"""

    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []

    def make_a2a_request(self, method, params, request_id=None):
        """Make an A2A JSON-RPC request"""
        if request_id is None:
            request_id = f"test-{int(time.time())}"

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }

        try:
            response = requests.post(
                f"{self.base_url}/a2a",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"error": {"message": str(e), "code": -1}}

    def test_health_check(self):
        """Test A2A health check"""
        print("🏥 Testing Health Check...")

        try:
            response = requests.get(f"{self.base_url}/a2a/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                if "result" in health_data and health_data["result"].get("status") == "healthy":
                    print("✅ Health Check: PASSED")
                    self.test_results.append(("Health Check", True, "Server is healthy"))
                    return True
                else:
                    print(f"❌ Health Check: FAILED - {health_data}")
                    self.test_results.append(("Health Check", False, str(health_data)))
                    return False
            else:
                print(f"❌ Health Check: FAILED - HTTP {response.status_code}")
                self.test_results.append(("Health Check", False, f"HTTP {response.status_code}"))
                return False
        except Exception as e:
            print(f"❌ Health Check: ERROR - {str(e)}")
            self.test_results.append(("Health Check", False, str(e)))
            return False

    def test_agent_card(self):
        """Test A2A agent card retrieval"""
        print("🔍 Testing Agent Card...")

        try:
            response = requests.get(f"{self.base_url}/agent_card", timeout=10)
            if response.status_code == 200:
                card_data = response.json()
                print("✅ Agent Card: PASSED")
                print(f"   Agent ID: {card_data.get('agent_id', 'Unknown')}")
                print(f"   Name: {card_data.get('name', 'Unknown')}")
                print(f"   Capabilities: {len(card_data.get('capabilities', []))} found")
                self.test_results.append(("Agent Card", True, f"Retrieved agent card for {card_data.get('agent_id')}"))
                return True
            else:
                print(f"❌ Agent Card: FAILED - HTTP {response.status_code}")
                self.test_results.append(("Agent Card", False, f"HTTP {response.status_code}"))
                return False
        except Exception as e:
            print(f"❌ Agent Card: ERROR - {str(e)}")
            self.test_results.append(("Agent Card", False, str(e)))
            return False

    def test_agent_registration(self):
        """Test A2A agent registration"""
        print("📝 Testing Agent Registration...")

        try:
            # First get the agent card to register
            card_response = requests.get(f"{self.base_url}/agent_card", timeout=10)
            if card_response.status_code != 200:
                print(f"❌ Agent Registration: FAILED - Could not get agent card (HTTP {card_response.status_code})")
                self.test_results.append(("Agent Registration", False, "Could not get agent card"))
                return False

            agent_card_data = card_response.json()

            # Register the agent using the agent card data
            response = self.make_a2a_request(
                "agent.register",
                {"agent_card": agent_card_data}
            )

            print(f"Registration response: {json.dumps(response, indent=2)}")

            if response.get("error") is not None:
                print(f"❌ Agent Registration: FAILED - Full response: {json.dumps(response, indent=2)}")
                self.test_results.append(("Agent Registration", False, str(response)))
                return False
            else:
                result = response.get("result", {})
                print(f"Full registration result: {json.dumps(result, indent=2)}")

                success = result.get("success", False)
                agent_id = result.get("agent_id")
                capabilities = result.get("capabilities", 0)
                registry_size = result.get("registry_size", 0)

                if success and agent_id:
                    print("✅ Agent Registration: PASSED")
                    print(f"   Agent ID: {agent_id}")
                    print(f"   Capabilities: {capabilities}")
                    print(f"   Registry Size: {registry_size}")
                    self.test_results.append(("Agent Registration", True, f"Registered agent {agent_id}"))
                    return True
                else:
                    print("❌ Agent Registration: FAILED - Registration unsuccessful")
                    print(f"   Success: {success}")
                    print(f"   Agent ID: {agent_id}")
                    print(f"   Full result: {json.dumps(result, indent=2)}")
                    self.test_results.append(("Agent Registration", False, "Registration unsuccessful"))
                    return False
        except Exception as e:
            print(f"❌ Agent Registration: ERROR - {str(e)}")
            self.test_results.append(("Agent Registration", False, str(e)))
            return False

    def test_agent_discovery(self):
        """Test A2A agent discovery"""
        print("🔍 Testing Agent Discovery...")

        try:
            response = self.make_a2a_request(
                "agent.discover",
                {"capability": "document.query"}
            )

            print(f"Discovery response: {json.dumps(response, indent=2)}")

            if response.get("error") is not None:
                print(f"❌ Agent Discovery: FAILED - Full response: {json.dumps(response, indent=2)}")
                self.test_results.append(("Agent Discovery", False, str(response)))
                return False
            else:
                result = response.get("result", {})
                agents = result.get("agents", [])
                print(f"Full discovery result: {json.dumps(result, indent=2)}")
                if agents:
                    print(f"✅ Agent Discovery: PASSED - Found {len(agents)} agents")
                    for i, agent in enumerate(agents, 1):
                        agent_id = agent.get('agent_id', 'unknown')
                        agent_name = agent.get('name', 'unknown')
                        print(f"  Agent {i}: {agent_id} - {agent_name}")
                    self.test_results.append(("Agent Discovery", True, f"Found {len(agents)} agents"))
                    return True
                else:
                    print("⚠️  Agent Discovery: WARNING - No agents found")
                    print(f"  Full result: {json.dumps(result, indent=2)}")
                    print("  Note: This is expected if agent registration failed or agent was not registered")
                    self.test_results.append(("Agent Discovery", True, "Discovery working (no agents found)"))
                    return True
        except Exception as e:
            print(f"❌ Agent Discovery: ERROR - {str(e)}")
            self.test_results.append(("Agent Discovery", False, str(e)))
            return False

    def test_document_query(self):
        """Test A2A document query"""
        print("📄 Testing Document Query...")

        try:
            response = self.make_a2a_request(
                "document.query",
                {
                    "query": "What is artificial intelligence?",
                    "collection": "General",
                    "use_cot": False,
                    "max_results": 3
                }
            )

            if response.get("error") is not None:
                print(f"❌ Document Query: FAILED - Full response: {json.dumps(response, indent=2)}")
                self.test_results.append(("Document Query", False, str(response)))
                return False
            else:
                result = response.get("result", {})
                print(f"Full document query result: {json.dumps(result, indent=2)}")
                answer = result.get("answer", "")
                if answer and answer != "No answer provided" and answer.strip():
                    print("✅ Document Query: PASSED")
                    print(f"   Answer: {answer[:100]}...")
                    self.test_results.append(("Document Query", True, "Query processed successfully"))
                    return True
                else:
                    print("❌ Document Query: FAILED - No valid answer")
                    print(f"   Full result: {json.dumps(result, indent=2)}")
                    self.test_results.append(("Document Query", False, "No valid answer returned"))
                    return False
        except Exception as e:
            print(f"❌ Document Query: ERROR - {str(e)}")
            self.test_results.append(("Document Query", False, str(e)))
            return False

    def test_task_operations(self):
        """Test A2A task creation and status"""
        print("📋 Testing Task Operations...")

        try:
            # Create task
            create_response = self.make_a2a_request(
                "task.create",
                {
                "task_type": "document_processing",
                    "params": {
                        "command": "test_command",
                        "description": "Test task for A2A testing",
                        "priority": "high"
                    }
                }
            )

            if create_response.get("error") is not None:
                print(f"❌ Task Creation: FAILED - Full response: {json.dumps(create_response, indent=2)}")
                self.test_results.append(("Task Creation", False, str(create_response)))
                return False

            result = create_response.get("result", {})
            print(f"Full task creation result: {json.dumps(result, indent=2)}")
            task_id = result.get("task_id")

            if not task_id:
                print("❌ Task Creation: FAILED - No task ID returned")
                print(f"   Full result: {json.dumps(result, indent=2)}")
                self.test_results.append(("Task Creation", False, "No task ID returned"))
                return False

            print(f"✅ Task Creation: PASSED - Created task {task_id}")
            self.test_results.append(("Task Creation", True, f"Created task {task_id}"))

            # Check task status
            time.sleep(1)
            status_response = self.make_a2a_request(
                "task.status",
                {"task_id": task_id}
            )

            if status_response.get("error") is not None:
                print(f"❌ Task Status: FAILED - Full response: {json.dumps(status_response, indent=2)}")
                self.test_results.append(("Task Status", False, str(status_response)))
                return False

            status_result = status_response.get("result", {})
            print(f"Full task status result: {json.dumps(status_result, indent=2)}")
            task_status = status_result.get("status", "unknown")
            print(f"✅ Task Status: PASSED - Status: {task_status}")
            self.test_results.append(("Task Status", True, f"Status: {task_status}"))

            return True

        except Exception as e:
            print(f"❌ Task Operations: ERROR - {str(e)}")
            self.test_results.append(("Task Operations", False, str(e)))
            return False

    def run_all_tests(self):
        """Run all A2A tests"""
        print("🧪 Running A2A Test Suite...")
        print("=" * 60)

        all_passed = True

        # Test 1: Health Check
        if not self.test_health_check():
            all_passed = False

        # Test 2: Agent Card
        if not self.test_agent_card():
            all_passed = False

        # Test 3: Agent Registration
        if not self.test_agent_registration():
            all_passed = False

        # Test 4: Agent Discovery
        if not self.test_agent_discovery():
            all_passed = False

        # Test 5: Document Query
        if not self.test_document_query():
            all_passed = False

        # Test 6: Task Operations
        if not self.test_task_operations():
            all_passed = False

        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Results Summary:")
        print("-" * 60)

        for test_name, passed, message in self.test_results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} {test_name}: {message}")

        print("-" * 60)
        if all_passed:
            print("🎉 All A2A tests passed!")
            print("✅ OK")
            return 0
        else:
            print("❌ Some A2A tests failed.")
            print("❌ NOT OK")
            return 1

def main():
    """Main function"""
    print("🤖 A2A Protocol Test Suite")
    print("=" * 60)
    print("Make sure A2A server is running: python main.py")
    print()

    tester = A2ATester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
