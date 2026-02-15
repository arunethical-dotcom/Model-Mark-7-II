import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("Testing imports...")

try:
    from reasoning.governed_llm_backend import GovernedLLMBackend
    print("✅ GovernedLLMBackend imported")
    
    backend = GovernedLLMBackend(backend_type="mock", verbose=True)
    print("✅ Mock backend initialized")
    
    response = backend.generate("Test")
    print(f"✅ Response: {response}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
