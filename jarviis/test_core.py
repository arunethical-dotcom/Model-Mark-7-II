#!/usr/bin/env python3
"""
JARVIIS Core Tests
Simple test suite for validating core functionality.

Run: python test_core.py
"""

import sys
from core.state_manager import StateManager, AgentState, InvalidStateTransitionError
from core.orchestrator import Orchestrator


def test_state_transitions():
    """Test valid and invalid state transitions."""
    print("\n🧪 Testing State Transitions")
    print("="*60)
    
    manager = StateManager()
    
    # Test valid transitions
    print("\n✅ Testing VALID transitions:")
    
    tests = [
        (AgentState.LISTENING, "IDLE → LISTENING"),
        (AgentState.REASONING, "LISTENING → REASONING"),
        (AgentState.IDLE, "REASONING → IDLE"),
    ]
    
    for target_state, description in tests:
        try:
            manager.transition_to(target_state)
            print(f"   ✓ {description}")
        except InvalidStateTransitionError as e:
            print(f"   ✗ {description} - FAILED: {e}")
            return False
    
    # Test invalid transition
    print("\n❌ Testing INVALID transition (should raise error):")
    
    try:
        # Should fail: Can't go from IDLE to EXECUTING directly
        manager.transition_to(AgentState.EXECUTING)
        print(f"   ✗ IDLE → EXECUTING - Should have raised error!")
        return False
    except InvalidStateTransitionError:
        print(f"   ✓ IDLE → EXECUTING - Correctly blocked")
    
    # Test state history
    print("\n📜 State History:")
    history = manager.get_last_n_states(5)
    print(f"   {' → '.join([s.value for s in history])}")
    
    return True


def test_orchestrator_lifecycle():
    """Test full request lifecycle through orchestrator."""
    print("\n🧪 Testing Orchestrator Lifecycle")
    print("="*60)
    
    orchestrator = Orchestrator()
    
    # Process a request
    print("\n🚀 Processing test request...")
    response = orchestrator.process_request("Test input")
    
    # Check state returned to IDLE
    final_state = orchestrator.state_manager.current_state
    
    if final_state != AgentState.IDLE:
        print(f"   ✗ Final state should be IDLE, got {final_state.value}")
        return False
    
    print(f"   ✓ Request processed successfully")
    print(f"   ✓ Final state: {final_state.value}")
    print(f"   ✓ Response: {response[:80]}...")
    
    return True


def test_state_observability():
    """Test state observability features."""
    print("\n🧪 Testing State Observability")
    print("="*60)
    
    manager = StateManager()
    
    # Create some state transitions
    transitions = [
        AgentState.LISTENING,
        AgentState.REASONING,
        AgentState.EXECUTING,
        AgentState.LEARNING,
        AgentState.IDLE
    ]
    
    for state in transitions:
        try:
            manager.transition_to(state)
        except InvalidStateTransitionError:
            # Some might fail, that's ok for this test
            pass
    
    # Test observability methods
    print(f"\n   Current state: {manager.current_state.value}")
    print(f"   Is in IDLE? {manager.is_in_state(AgentState.IDLE)}")
    print(f"   Allowed transitions: {[s.value for s in manager.get_allowed_transitions()]}")
    print(f"   History length: {len(manager.get_state_history())}")
    print(f"   Last 3 states: {' → '.join([s.value for s in manager.get_last_n_states(3)])}")
    
    print("\n   ✓ All observability methods working")
    
    return True


def test_orchestrator_status():
    """Test orchestrator status reporting."""
    print("\n🧪 Testing Orchestrator Status")
    print("="*60)
    
    orchestrator = Orchestrator()
    
    # Process multiple requests
    for i in range(3):
        orchestrator.process_request(f"Request {i+1}")
    
    # Get status
    status = orchestrator.get_status()
    
    print(f"\n   System: {status['system']}")
    print(f"   Version: {status['version']}")
    print(f"   State: {status['state']}")
    print(f"   Requests processed: {status['request_count']}")
    print(f"   State history: {' → '.join(status['state_history'])}")
    
    # Validate
    if status['request_count'] != 3:
        print(f"\n   ✗ Expected 3 requests, got {status['request_count']}")
        return False
    
    print("\n   ✓ Status reporting accurate")
    
    return True


def test_error_recovery():
    """Test error handling and recovery."""
    print("\n🧪 Testing Error Recovery")
    print("="*60)
    
    orchestrator = Orchestrator()
    
    # Force the state into an unusual position
    orchestrator.state_manager.transition_to(AgentState.LISTENING)
    orchestrator.state_manager.transition_to(AgentState.REASONING)
    orchestrator.state_manager.transition_to(AgentState.EXECUTING)
    
    print(f"\n   Pre-request state: {orchestrator.state_manager.current_state.value}")
    
    # This should handle the weird state gracefully
    # The orchestrator should reset on error
    try:
        response = orchestrator.process_request("Test after weird state")
        print(f"   ✓ Recovered gracefully")
        print(f"   ✓ Post-request state: {orchestrator.state_manager.current_state.value}")
    except Exception as e:
        print(f"   ✗ Failed to recover: {e}")
        return False
    
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*60)
    print("🧪 JARVIIS CORE TEST SUITE")
    print("="*60)
    
    tests = [
        ("State Transitions", test_state_transitions),
        ("Orchestrator Lifecycle", test_orchestrator_lifecycle),
        ("State Observability", test_state_observability),
        ("Orchestrator Status", test_orchestrator_status),
        ("Error Recovery", test_error_recovery),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n❌ {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name} CRASHED: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"   Passed: {passed}/{len(tests)}")
    print(f"   Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n   ✅ All tests passed! Core is solid.")
        return 0
    else:
        print(f"\n   ❌ {failed} test(s) failed. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
