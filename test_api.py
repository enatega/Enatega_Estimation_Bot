#!/usr/bin/env python3
"""
Quick test script for the Estimation Bot API
Run this after starting the server to test endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing /api/v1/health...")
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_features():
    """Test features endpoint"""
    print("Testing /api/v1/features...")
    response = requests.get(f"{BASE_URL}/api/v1/features")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total Features: {data.get('total_count', 0)}")
    print(f"Features: {json.dumps(data.get('features', [])[:2], indent=2)}...")
    print()

def test_estimate():
    """Test estimate endpoint"""
    print("Testing /api/v1/estimate...")
    payload = {
        "requirements": "I need a client onboarding system with user authentication, dashboard, and payment processing",
        "hourly_rate": 100.0,
        "include_breakdown": True
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/estimate",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total Time: {data.get('total_time_hours')} hours")
        print(f"Total Cost: ${data.get('total_cost'):.2f}")
        print(f"Timeline: {data.get('timeline')}")
        print(f"Breakdown Items: {len(data.get('breakdown', []))}")
        print(f"Summary Preview: {data.get('summary', '')[:200]}...")
    else:
        print(f"Error: {response.text}")
    print()

def test_chat():
    """Test chat endpoint"""
    print("Testing /api/v1/chat...")
    payload = {
        "message": "What would it cost to build a simple client onboarding system?",
        "conversation_history": []
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response Preview: {data.get('response', '')[:300]}...")
    else:
        print(f"Error: {response.text}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Estimation Bot API Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_health()
        test_features()
        test_estimate()
        test_chat()
        
        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API.")
        print("Make sure the server is running: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"ERROR: {e}")
