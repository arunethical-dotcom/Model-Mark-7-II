#!/usr/bin/env python3
"""
JARVIIS Memory Subsystem Tests
Tests for memory storage, retrieval, and importance scoring.

Run: python test_memory.py
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory import MemoryRouter


def test_basic_storage():
    """Test basic memory storage."""
    print("\n🧪 Test: Basic Storage")
    print("="*60)
    
    # Use temporary database
    memory = MemoryRouter("test_memory.db")
    memory.clear()
    
    # Store a memory
    memory.store({
        'user_input': 'What is Python?',
        'system_response': 'Python is a programming language.',
        'timestamp': datetime.now().isoformat()
    })
    
    # Check it was stored
    stats = memory.get_stats()
    
    if stats['active_memories'] == 1:
        print("   ✓ Memory stored successfully")
        return True
    else:
        print(f"   ✗ Expected 1 memory, got {stats['active_memories']}")
        return False


def test_importance_scoring():
    """Test importance score computation."""
    print("\n🧪 Test: Importance Scoring")
    print("="*60)
    
    memory = MemoryRouter("test_memory.db")
    memory.clear()
    
    test_cases = [
        ("Hello", "Hi", 1, "Base score"),
        ("Remember that I like coffee", "Noted", 4, "Explicit + preference"),
        ("What is AI?", "AI stands for...", 2, "Question"),
        ("That was wrong, it's actually XYZ", "Corrected", 3, "Error correction"),
    ]
    
    all_passed = True
    
    for user_input, system_response, expected_min, description in test_cases:
        memory.store({
            'user_input': user_input,
            'system_response': system_response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Get the last stored memory
        recent = memory.get_recent(limit=1)
        if recent:
            score = recent[0]['importance_score']
            if score >= expected_min:
                print(f"   ✓ {description}: score={score} (>={expected_min})")
            else:
                print(f"   ✗ {description}: score={score} (expected >={expected_min})")
                all_passed = False
        else:
            print(f"   ✗ {description}: Memory not stored")
            all_passed = False
    
    return all_passed


def test_retrieval_strategies():
    """Test different retrieval strategies."""
    print("\n🧪 Test: Retrieval Strategies")
    print("="*60)
    
    memory = MemoryRouter("test_memory.db")
    memory.clear()
    
    # Store memories with varying importance
    memories_data = [
        ("Low importance chat", "OK", 1),
        ("Remember my name is Alice", "Got it", 4),
        ("What's the weather?", "Sunny", 2),
        ("I prefer dark mode", "Noted", 2),
        ("That's wrong!", "Sorry", 3),
    ]
    
    for i, (user_input, response, _) in enumerate(memories_data):
        memory.store({
            'user_input': user_input,
            'system_response': response,
            'timestamp': datetime.now().isoformat()
        })
    
    # Test retrieval
    all_memories = memory.retrieve("anything", limit=10)
    important_only = memory.get_important(min_importance=3, limit=10)
    
    print(f"   Retrieved {len(all_memories)} memories (recent + important)")
    print(f"   Retrieved {len(important_only)} highly important memories")
    
    if len(all_memories) >= 5:
        print("   ✓ Retrieval working")
    else:
        print("   ✗ Expected at least 5 memories")
        return False
    
    if len(important_only) >= 1:
        print("   ✓ Important memory filtering working")
    else:
        print("   ✗ Expected at least 1 important memory")
        return False
    
    return True


def test_memory_types():
    """Test memory type classification."""
    print("\n🧪 Test: Memory Type Classification")
    print("="*60)
    
    memory = MemoryRouter("test_memory.db")
    memory.clear()
    
    test_cases = [
        ("I like pizza", "preference"),
        ("Remember that the meeting is at 3pm", "fact"),
        ("That's wrong, it's 4pm", "error"),
        ("Hello", "interaction"),
    ]
    
    all_passed = True
    
    for user_input, expected_type in test_cases:
        memory.store({
            'user_input': user_input,
            'system_response': "OK",
            'timestamp': datetime.now().isoformat()
        })
        
        recent = memory.get_recent(limit=1)
        if recent:
            actual_type = recent[0]['memory_type']
            if actual_type == expected_type:
                print(f"   ✓ '{user_input[:30]}...' → {actual_type}")
            else:
                print(f"   ✗ '{user_input[:30]}...' → {actual_type} (expected {expected_type})")
                all_passed = False
        else:
            print(f"   ✗ Memory not stored")
            all_passed = False
    
    return all_passed


def test_reinforcement():
    """Test memory reinforcement."""
    print("\n🧪 Test: Memory Reinforcement")
    print("="*60)
    
    memory = MemoryRouter("test_memory.db")
    memory.clear()
    
    # Store a memory
    memory.store({
        'user_input': 'Important fact',
        'system_response': 'Noted',
        'timestamp': datetime.now().isoformat()
    })
    
    # Get initial reinforcement count
    mem1 = memory.get_recent(limit=1)[0]
    initial_count = mem1['reinforcement_count']
    
    # Retrieve (which reinforces)
    memory.retrieve("test", limit=5)
    
    # Check reinforcement increased
    mem2 = memory.get_recent(limit=1)[0]
    final_count = mem2['reinforcement_count']
    
    if final_count > initial_count:
        print(f"   ✓ Reinforcement working: {initial_count} → {final_count}")
        return True
    else:
        print(f"   ✗ Reinforcement failed: count={final_count}")
        return False


def test_stats():
    """Test statistics gathering."""
    print("\n🧪 Test: Statistics")
    print("="*60)
    
    memory = MemoryRouter("test_memory.db")
    memory.clear()
    
    # Store diverse memories
    for i in range(5):
        memory.store({
            'user_input': f'Message {i}',
            'system_response': 'OK',
            'timestamp': datetime.now().isoformat()
        })
    
    stats = memory.get_stats()
    
    print(f"   Active memories: {stats['active_memories']}")
    print(f"   Avg importance: {stats['avg_importance']}")
    print(f"   Type breakdown: {stats['type_breakdown']}")
    
    if stats['active_memories'] == 5:
        print("   ✓ Statistics accurate")
        return True
    else:
        print("   ✗ Statistics incorrect")
        return False


def test_core_integration():
    """Test integration with JARVIIS core."""
    print("\n🧪 Test: Core Integration")
    print("="*60)
    
    try:
        from core import Orchestrator
        from memory import MemoryRouter
        from config.settings import CoreSettings
        
        # Create custom settings with learning enabled
        settings = CoreSettings(
            enable_learning=True  # Enable learning to trigger memory.store()
        )
        
        # Create orchestrator with real memory
        memory = MemoryRouter("test_memory.db")
        memory.clear()
        
        # Create orchestrator with memory and custom settings
        orchestrator = Orchestrator(memory=memory)
        orchestrator.settings = settings  # Override settings
        
        # Process a request
        response = orchestrator.process_request("Remember that I love Python")
        
        # Check memory was stored
        memories = memory.get_recent(limit=1)
        
        if memories and 'Python' in memories[0]['user_input']:
            print("   ✓ Core integration working")
            print(f"   ✓ Stored: {memories[0]['summary'][:50]}...")
            return True
        else:
            print("   ✗ Memory not stored during orchestration")
            return False
            
    except Exception as e:
        print(f"   ✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup():
    """Remove test database."""
    try:
        if os.path.exists("test_memory.db"):
            os.remove("test_memory.db")
        print("\n🧹 Cleaned up test database")
    except Exception as e:
        print(f"\n⚠️  Failed to cleanup: {e}")


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*60)
    print("🧪 JARVIIS MEMORY SUBSYSTEM TEST SUITE")
    print("="*60)
    
    tests = [
        ("Basic Storage", test_basic_storage),
        ("Importance Scoring", test_importance_scoring),
        ("Retrieval Strategies", test_retrieval_strategies),
        ("Memory Types", test_memory_types),
        ("Reinforcement", test_reinforcement),
        ("Statistics", test_stats),
        ("Core Integration", test_core_integration),
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
            import traceback
            traceback.print_exc()
    
    # Cleanup
    cleanup()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"   Passed: {passed}/{len(tests)}")
    print(f"   Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n   ✅ All memory tests passed! System ready.")
        return 0
    else:
        print(f"\n   ❌ {failed} test(s) failed. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
