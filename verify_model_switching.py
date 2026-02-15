
import sys
import os
import time

# Add fallback paths
current_dir = os.path.dirname(os.path.abspath(__file__))
jarviis_dir = os.path.join(current_dir, "jarviis")
sys.path.insert(0, jarviis_dir)
governance_dir = os.path.join(current_dir, "governance")
sys.path.insert(0, governance_dir)

sys.path.insert(0, governance_dir)

from reasoning.reasoning_engine import ReasoningEngine

def test_live_switching():
    print("Initializing ReasoningEngine...")
    # Initialize with actual LLM connection to get real debug prints
    engine = ReasoningEngine(enable_llm=True, use_governance=True)
    
    print("\n--- TEST: Simple Query (Should be qwen-local) ---")
    query_simple = "hi"
    print(f"Query: '{query_simple}'")
    model_simple = engine._select_model(query_simple)
    print(f"Selected Model Logic: {model_simple}")
    
    print("\n--- TEST: Complex Query (Should be hermes-local) ---")
    query_complex = "write a python script to sort a list of numbers"
    print(f"Query: '{query_complex}'")
    model_complex = engine._select_model(query_complex)
    print(f"Selected Model Logic: {model_complex}")

    # Now let's try to actually run one to see the debug output from llm_backends
    # This will trigger the [DEBUG] OLLAMA Request prints we added
    print("\n--- LIVE EXECUTION: Simple Query ---")
    try:
        response = engine.governed_backend.generate(
            prompt=query_simple,
            model=model_simple 
        )
        print("Response received.")
    except Exception as e:
        print(f"Execution failed: {e}")

if __name__ == "__main__":
    test_live_switching()
