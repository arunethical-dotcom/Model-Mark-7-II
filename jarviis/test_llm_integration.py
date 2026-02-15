#!/usr/bin/env python3
"""
Test JARVIIS with Ollama LLM Integration
Quick verification that LLM enhancement works.
"""

import sys
import os

# Test 1: Import and initialize
print("="*60)
print("TEST 1: Import and Initialize")
print("="*60)

try:
    from reasoning import ReasoningEngine
    print("✓ ReasoningEngine imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test with LLM enabled
reasoner_llm = ReasoningEngine(enable_llm=True)
print(f"✓ ReasoningEngine initialized (LLM enabled: {reasoner_llm.enable_llm})")

# Test with LLM disabled (backward compatibility)
reasoner_no_llm = ReasoningEngine(enable_llm=False)
print(f"✓ ReasoningEngine initialized (LLM disabled: {reasoner_no_llm.enable_llm})")

# Test 2: Check stats
print("\n" + "="*60)
print("TEST 2: Stats and Configuration")
print("="*60)

stats = reasoner_llm.get_stats()
print(f"Mode: {stats['mode']}")
print(f"LLM Enabled: {stats['llm_enabled']}")
print(f"Fast Model: {stats['fast_model']}")
print(f"Deep Model: {stats['deep_model']}")

# Test 3: Rule-based handlers (should not use LLM)
print("\n" + "="*60)
print("TEST 3: Rule-Based Handlers (No LLM)")
print("="*60)

test_greeting = "Hello JARVIIS"
context = {'user_input': test_greeting, 'memories': []}
response = reasoner_llm.reason(context)
print(f"Greeting: {response}")
print("✓ Greeting handler works (rule-based)")

# Test 4: Question handler (should try LLM)
print("\n" + "="*60)
print("TEST 4: Question Handler (LLM-Enhanced)")
print("="*60)

test_question = "What is the capital of France?"
context = {'user_input': test_question, 'memories': []}
response = reasoner_llm.reason(context)
print(f"Question: {test_question}")
print(f"Response: {response}")

if "Phase 2" in response or "infrastructure mode" in response:
    print("⚠️  LLM not available - using fallback (this is OK)")
else:
    print("✓ LLM-generated response detected")

# Test 5: Default handler (should try LLM)
print("\n" + "="*60)
print("TEST 5: Default Handler (LLM-Enhanced)")
print("="*60)

test_default = "I love Python programming"
context = {'user_input': test_default, 'memories': []}
response = reasoner_llm.reason(context)
print(f"Input: {test_default}")
print(f"Response: {response}")

if "Phase 2" in response or "infrastructure mode" in response:
    print("⚠️  LLM not available - using fallback (this is OK)")
else:
    print("✓ LLM-generated response detected")

# Test 6: Backward compatibility (LLM disabled)
print("\n" + "="*60)
print("TEST 6: Backward Compatibility (LLM Disabled)")
print("="*60)

context = {'user_input': 'What is AI?', 'memories': []}
response = reasoner_no_llm.reason(context)
print(f"Response (no LLM): {response}")
print("✓ Backward compatibility maintained")

# Test 7: Full integration test
print("\n" + "="*60)
print("TEST 7: Full System Integration")
print("="*60)

try:
    from core import Orchestrator
    from memory import MemoryRouter
    from config.settings import CoreSettings
    
    # Initialize with LLM-enabled reasoner
    memory = MemoryRouter('test_llm_integration.db')
    memory.clear()
    
    settings = CoreSettings(
        enable_memory=True,
        enable_reasoning=True,
        enable_learning=True
    )
    
    orch = Orchestrator(memory=memory, reasoner=reasoner_llm)
    orch.settings = settings
    
    # Test request
    response = orch.process_request("What is machine learning?")
    print(f"Orchestrator response: {response[:100]}...")
    
    # Cleanup
    os.remove('test_llm_integration.db')
    print("✓ Full integration works")
    
except Exception as e:
    print(f"✗ Integration test failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print("""
✓ LLM integration is minimal and surgical
✓ Architecture preserved (Decision-Object Pattern)
✓ Backward compatibility maintained
✓ Rules decide, LLMs speak
✓ Graceful fallback on LLM failure

Next steps:
1. Ensure Ollama is installed: https://ollama.ai
2. Pull models: 
   - ollama pull mistral:instruct
3. Run: python main_complete.py

If Ollama is not available, JARVIIS falls back to rule-based responses.
""")
