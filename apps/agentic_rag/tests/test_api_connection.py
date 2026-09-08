#!/usr/bin/env python3
"""
Test script to verify API connectivity on port 8000
Tests all major endpoints to ensure the API is accessible
"""

import json
import sys
from typing import Any

import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 10

def check_endpoint(method: str, endpoint: str, data: dict[str, Any] = None, files: dict = None) -> dict[str, Any]:
    """Check a single API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing: {method} {endpoint}")
    print(f"URL: {url}")
    print(f"{'='*60}")

    try:
        if method == "GET":
            response = requests.get(url, timeout=TIMEOUT)
        elif method == "POST":
            if files:
                response = requests.post(url, data=data, files=files, timeout=TIMEOUT)
            else:
                response = requests.post(url, json=data, timeout=TIMEOUT)
        else:
            return {"error": f"Unsupported method: {method}"}

        print(f"Status Code: {response.status_code}")

        try:
            response_json = response.json()
            print(f"Response: {json.dumps(response_json, indent=2)}")
            return {"status_code": response.status_code, "response": response_json, "success": True}
        except Exception:
            print(f"Response (text): {response.text[:500]}")
            return {"status_code": response.status_code, "response": response.text, "success": response.status_code < 400}

    except requests.exceptions.ConnectionError as e:
        error_msg = f"[ERROR] Connection Error: Cannot connect to {BASE_URL}"
        print(error_msg)
        print(f"   Details: {str(e)}")
        return {"error": error_msg, "success": False}
    except requests.exceptions.Timeout:
        error_msg = f"[ERROR] Timeout: Request to {BASE_URL} timed out after {TIMEOUT}s"
        print(error_msg)
        return {"error": error_msg, "success": False}
    except Exception as e:
        error_msg = f"[ERROR] Error: {str(e)}"
        print(error_msg)
        return {"error": error_msg, "success": False}

def main():
    """Run all API tests"""
    print("\n" + "="*60)
    print("API Connection Test Suite")
    print(f"Testing API at: {BASE_URL}")
    print("="*60)

    results = []

    # Test 1: Health Check
    print("\n[Test 1] Health Check")
    result = check_endpoint("GET", "/a2a/health")
    results.append(("Health Check", result))

    # Test 2: Agent Card
    print("\n[Test 2] Agent Card")
    result = check_endpoint("GET", "/agent_card")
    results.append(("Agent Card", result))

    # Test 3: A2A Protocol - Health Check
    print("\n[Test 3] A2A Protocol Health Check")
    a2a_health = {
        "jsonrpc": "2.0",
        "method": "health.check",
        "params": {},
        "id": "test-1"
    }
    result = check_endpoint("POST", "/a2a", a2a_health)
    results.append(("A2A Health", result))

    # Test 4: A2A Protocol - Document Query
    print("\n[Test 4] A2A Protocol Document Query")
    a2a_query = {
        "jsonrpc": "2.0",
        "method": "document.query",
        "params": {
            "query": "What is artificial intelligence?",
            "collection": "General",
            "use_cot": False,
            "max_results": 3
        },
        "id": "test-2"
    }
    result = check_endpoint("POST", "/a2a", a2a_query)
    results.append(("A2A Document Query", result))

    # Test 5: Standard Query Endpoint
    print("\n[Test 5] Standard Query Endpoint")
    query_data = {
        "query": "What is machine learning?",
        "use_cot": False
    }
    result = check_endpoint("POST", "/query", query_data)
    results.append(("Standard Query", result))

    # Test 6: API Documentation
    print("\n[Test 6] API Documentation")
    result = check_endpoint("GET", "/docs")
    results.append(("API Docs", result))

    # Test 7: OpenAPI Schema
    print("\n[Test 7] OpenAPI Schema")
    result = check_endpoint("GET", "/openapi.json")
    results.append(("OpenAPI Schema", result))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = 0
    failed = 0

    for test_name, result in results:
        if result.get("success"):
            print(f"[PASS] {test_name}: PASSED")
            passed += 1
        elif "error" in result:
            print(f"[FAIL] {test_name}: FAILED - {result.get('error', 'Unknown error')}")
            failed += 1
        else:
            status = result.get("status_code", "Unknown")
            if 200 <= status < 400:
                print(f"[PASS] {test_name}: PASSED (Status: {status})")
                passed += 1
            else:
                print(f"[FAIL] {test_name}: FAILED (Status: {status})")
                failed += 1

    print(f"\nTotal: {passed + failed} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("="*60)

    if failed > 0:
        print("\n[WARNING] Some tests failed. Please check:")
        print("   1. Is the API server running? (python main.py)")
        print("   2. Is it running on port 8000?")
        print("   3. Are there any firewall or network issues?")
        print("   4. Check the server logs for errors")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All tests passed! API is accessible and working.")
        sys.exit(0)

if __name__ == "__main__":
    main()

