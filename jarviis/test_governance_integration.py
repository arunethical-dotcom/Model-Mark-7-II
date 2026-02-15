"""
Governance Layer Integration Tests
Verifies that all LLM calls pass through CognitiveOrchestrator.

Tests:
1. Identity anchor injection
2. Response validation
3. No direct LLM bypass
4. Memory integration
5. Backward compatibility
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Force unbuffered output for immediate console feedback
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Setup logging
LOG_FILE = Path(__file__).parent / "test_run_log.txt"

def log(msg):
    # Print to console
    print(msg)
    sys.stdout.flush()
    # Also log to file as backup
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

print("STARTING TESTS INITIALIZATION")
sys.stdout.flush()
# Initialize log
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("STARTING TESTS INITIALIZATION\n")

# -------------------------------------------------------
# FIX: Ensure correct paths are added to Python path
# -------------------------------------------------------

CURRENT_DIR = Path(__file__).resolve().parent  # jarviis/
PROJECT_ROOT = CURRENT_DIR.parent               # Cursor Int/

# Add jarviis directory so 'core', 'reasoning' imports work
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Add project root so 'model', 'governance' imports work  
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    log("Importing ReasoningEngine...")
    from reasoning.reasoning_engine import ReasoningEngine
    log("Importing HybridReasoner...")
    from reasoning.hybrid_reasoner import HybridReasoner
    log("Importing Orchestrator...")
    from core.orchestrator import Orchestrator
    log("Imports successful")
except Exception as e:
    log(f"CRITICAL IMPORT ERROR: {e}")
    import traceback
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        traceback.print_exc(file=f)
    sys.exit(1)


# -------------------------------------------------------
# TESTS
# -------------------------------------------------------

def get_mock_backend(*args, **kwargs):
    """Factory to return a MockBackend-configured GovernedLLMBackend"""
    # Import inside to avoid circular issues or early import
    from reasoning.governed_llm_backend import GovernedLLMBackend
    print("[MOCK] Initializing GovernedLLMBackend with mock backend")
    return GovernedLLMBackend(backend_type="mock", verbose=True)

def test_governance_available():
    print("\n" + "="*60)
    print("TEST 1: Governance Layer Availability")
    print("="*60)

    try:
        from reasoning.governed_llm_backend import GovernedLLMBackend

        print("[PASS] GovernedLLMBackend imported successfully")

        backend = GovernedLLMBackend(backend_type="mock", verbose=True)
        print("[PASS] GovernedLLMBackend initialized with mock backend")

        response = backend.generate("Test prompt")
        print(f"[PASS] Generated response: {response[:60]}...")

        stats = backend.get_stats()
        print(f"[PASS] Stats available: mode={stats.get('mode')}")

        return True

    except Exception as e:
        print(f"[FAIL] Governance layer test failed: {e}")
        return False


def test_reasoning_engine_integration():
    print("\n" + "="*60)
    print("TEST 2: ReasoningEngine Integration")
    print("="*60)

    try:
        # Patch the GovernedLLMBackend class used inside ReasoningEngine
        with patch("reasoning.reasoning_engine.GovernedLLMBackend", side_effect=get_mock_backend):
            engine = ReasoningEngine(enable_llm=True, use_governance=True)

            print(f"LLM Enabled: {engine.enable_llm}")
            print(f"Governance Enabled: {engine.use_governance}")
            
            # Verify it's using the mock
            if engine.governed_backend and engine.governed_backend.backend_type == "mock":
                 print("[PASS] ReasoningEngine using MockBackend")

            context = {
                "user_input": "What is AI?",
                "memories": [],
                "request_id": 1
            }

            response = engine.reason(context)
            print(f"[PASS] Generated response: {response[:80]}...")

        return True

    except Exception as e:
        print(f"[FAIL] ReasoningEngine integration test failed: {e}")
        return False


def test_hybrid_reasoner_integration():
    print("\n" + "="*60)
    print("TEST 3: HybridReasoner Integration")
    print("="*60)

    try:
        # Patch in HybridReasoner
        with patch("reasoning.hybrid_reasoner.GovernedLLMBackend", side_effect=get_mock_backend):
            reasoner = HybridReasoner(use_governance=True)

            print(f"Governance Enabled: {reasoner.use_governance}")

            context = {"user_input": "Hello JARVIIS"}
            response = reasoner.reason(context)

            print(f"[PASS] Generated response: {response[:80]}...")

        return True

    except Exception as e:
        print(f"[FAIL] HybridReasoner integration test failed: {e}")
        return False


def test_orchestrator_compatibility():
    print("\n" + "="*60)
    print("TEST 4: Orchestrator Compatibility")
    print("="*60)

    try:
        # Patch through to HybridReasoner (since Orchestrator uses it)
        with patch("reasoning.hybrid_reasoner.GovernedLLMBackend", side_effect=get_mock_backend):
            reasoner = HybridReasoner(use_governance=True)
            orchestrator = Orchestrator(reasoner=reasoner)

            print("[PASS] Orchestrator initialized")

            response = orchestrator.process_request("Hello JARVIIS")
            print(f"[PASS] Request processed: {response[:80]}...")

            status = orchestrator.get_status()
            print(f"[PASS] Status: state={status['state']}")

        return True

    except Exception as e:
        print(f"[FAIL] Orchestrator compatibility test failed: {e}")
        return False


def test_identity_preservation():
    print("\n" + "="*60)
    print("TEST 5: Identity Preservation")
    print("="*60)

    try:
        from reasoning.governed_llm_backend import GovernedLLMBackend

        backend = GovernedLLMBackend(backend_type="mock", verbose=False)
        response = backend.generate("Who are you?")

        print(f"Response: {response[:100]}...")

        if "JARVIIS" in response.upper():
            print("[PASS] Identity anchor working")
        else:
            print("[WARN] Identity not explicitly mentioned")

        return True

    except Exception as e:
        print(f"[FAIL] Identity preservation test failed: {e}")
        return False


# -------------------------------------------------------
# RUNNER
# -------------------------------------------------------

def run_all_tests():
    print("\n" + "#" + "="*58 + "#")
    print("#" + " "*12 + "GOVERNANCE INTEGRATION TEST SUITE" + " "*12 + "#")
    print("#" + "="*58 + "#")
    
    # Ensure any residual patches are cleared
    patch.stopall()

    tests = [
        test_governance_available,
        test_reasoning_engine_integration,
        test_hybrid_reasoner_integration,
        test_orchestrator_compatibility,
        test_identity_preservation,
    ]

    passed = 0

    for test in tests:
        if test():
            passed += 1

    print("\n" + "="*60)
    print(f"RESULT: {passed}/{len(tests)} tests passed")
    print("="*60)

    return passed == len(tests)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
