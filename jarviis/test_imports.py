import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

print(f"Current dir: {CURRENT_DIR}")
print(f"Project root: {PROJECT_ROOT}")

# Add paths
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print(f"\nsys.path:")
for p in sys.path[:5]:
    print(f"  {p}")

print("\nTrying imports...")

try:
    from reasoning.reasoning_engine import ReasoningEngine
    print("✅ ReasoningEngine imported")
except Exception as e:
    print(f"❌ ReasoningEngine import failed: {e}")

try:
    from reasoning.hybrid_reasoner import HybridReasoner
    print("✅ HybridReasoner imported")
except Exception as e:
    print(f"❌ HybridReasoner import failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from core.orchestrator import Orchestrator
    print("✅ Orchestrator imported")
except Exception as e:
    print(f"❌ Orchestrator import failed: {e}")
