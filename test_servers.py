#!/usr/bin/env python3
"""
Quick test script for JARVIIS llama.cpp integration
Verifies both servers are running and responding correctly
"""

import json
import urllib.request
import urllib.error

def test_server(name, port):
    """Test if a llama.cpp server is responding"""
    print(f"\nTesting {name} server on port {port}...")
    
    # Test health endpoint
    try:
        req = urllib.request.Request(f"http://localhost:{port}/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                print(f"  ✓ Health check passed")
            else:
                print(f"  ✗ Health check failed: HTTP {resp.status}")
                return False
    except Exception as e:
        print(f"  ✗ Health check failed: {e}")
        return False
    
    # Test chat completion
    try:
        payload = {
            "messages": [
                {"role": "system", "content": "You are JARVIIS, a helpful AI assistant."},
                {"role": "user", "content": "Say 'test successful' if you can read this."}
            ],
            "temperature": 0.3,
            "max_tokens": 50,
            "stream": False
        }
        
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"http://localhost:{port}/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            response_text = result["choices"][0]["message"]["content"]
            print(f"  ✓ Chat completion successful")
            print(f"  Response: {response_text[:100]}...")
            return True
            
    except Exception as e:
        print(f"  ✗ Chat completion failed: {e}")
        return False

def test_jarviis():
    """Test JARVIIS integration"""
    print("\n" + "="*60)
    print("Testing JARVIIS Integration")
    print("="*60)
    
    try:
        import sys
        sys.path.insert(0, 'governance')
        from jarviis import JARVIISAgent
        
        print("\nInitializing JARVIIS...")
        agent = JARVIISAgent(backend="llamacpp", verbose=True)
        
        print("\nSending test message...")
        response = agent.chat("Hello JARVIIS, please introduce yourself briefly.")
        
        print(f"\nJARVIIS Response:")
        print(f"{response}")
        
        # Check for identity leaks
        response_lower = response.lower()
        if any(leak in response_lower for leak in ["i am qwen", "i am mistral", "i am gpt"]):
            print("\n✗ WARNING: Identity leak detected!")
            return False
        else:
            print("\n✓ No identity leaks detected")
            return True
            
    except Exception as e:
        print(f"\n✗ JARVIIS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("JARVIIS llama.cpp Integration Test")
    print("="*60)
    
    # Test both servers
    mistral_ok = test_server("Mistral (Reasoning)", 8080)
    qwen_ok = test_server("Qwen (Governance)", 8081)
    
    if not (mistral_ok and qwen_ok):
        print("\n" + "="*60)
        print("ERROR: Server tests failed")
        print("="*60)
        print("\nPlease ensure both servers are running:")
        print("  1. Run: .\\start_servers.ps1")
        print("  2. Wait for servers to initialize (~10 seconds)")
        print("  3. Run this test again")
        exit(1)
    
    # Test JARVIIS integration
    jarviis_ok = test_jarviis()
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Mistral Server:  {'✓ PASS' if mistral_ok else '✗ FAIL'}")
    print(f"Qwen Server:     {'✓ PASS' if qwen_ok else '✗ FAIL'}")
    print(f"JARVIIS Agent:   {'✓ PASS' if jarviis_ok else '✗ FAIL'}")
    print("="*60)
    
    if mistral_ok and qwen_ok and jarviis_ok:
        print("\n✅ All tests passed! JARVIIS is ready to use.")
        exit(0)
    else:
        print("\n❌ Some tests failed. Please review the output above.")
        exit(1)
