#!/usr/bin/env python3
"""
JARVIIS with Memory - Integration Example
Demonstrates the memory subsystem working with the cognitive core.

Run: python example_with_memory.py
"""

from core import Orchestrator
from memory import MemoryRouter
from config.settings import CoreSettings


def print_banner():
    """Display banner."""
    print("\n" + "="*70)
    print("🧠 JARVIIS with Memory Subsystem")
    print("   Phase 2A: Structured Episodic Memory")
    print("="*70 + "\n")


def demonstrate_memory():
    """Demonstrate memory-enabled JARVIIS."""
    
    # Create memory router
    memory = MemoryRouter("jarviis_memory.db")
    
    # Create custom settings with learning enabled
    settings = CoreSettings(enable_learning=True)
    
    # Create orchestrator with memory
    orchestrator = Orchestrator(memory=memory)
    orchestrator.settings = settings
    
    print("📊 Initial Memory Stats:")
    stats = memory.get_stats()
    print(f"   Active memories: {stats['active_memories']}")
    print(f"   Avg importance: {stats['avg_importance']}")
    print()
    
    # Example conversations
    conversations = [
        "Hello! My name is Alice.",
        "Remember that I prefer dark mode.",
        "What's 2 + 2?",
        "Actually, that's wrong. 2 + 2 = 4.",
        "I like Python programming.",
        "What did I say my name was?",
    ]
    
    print("="*70)
    print("💬 CONVERSATIONS")
    print("="*70 + "\n")
    
    for i, user_input in enumerate(conversations, 1):
        print(f"{'─'*70}")
        print(f"Turn {i}")
        print(f"{'─'*70}")
        print(f"You: {user_input}")
        
        response = orchestrator.process_request(user_input)
        print(f"JARVIIS: {response}")
        print()
    
    # Show what was remembered
    print("="*70)
    print("🧠 MEMORY CONTENTS")
    print("="*70 + "\n")
    
    print("📌 Recent Memories:")
    recent = memory.get_recent(limit=10)
    for mem in recent[:5]:  # Show first 5
        print(f"   [{mem['memory_type']}] {mem['summary'][:60]}...")
        print(f"      Importance: {mem['importance_score']}, "
              f"Reinforced: {mem['reinforcement_count']} times")
    print()
    
    print("⭐ Important Memories (score >= 3):")
    important = memory.get_important(min_importance=3)
    for mem in important:
        print(f"   [{mem['memory_type']}] {mem['summary'][:60]}...")
        print(f"      Score: {mem['importance_score']}")
    print()
    
    print("💡 Preferences Learned:")
    preferences = memory.get_by_type('preference')
    for pref in preferences:
        print(f"   • {pref['summary'][:60]}...")
    print()
    
    # Final stats
    print("="*70)
    print("📊 FINAL STATISTICS")
    print("="*70)
    final_stats = memory.get_stats()
    print(f"   Total interactions: {final_stats['interaction_count']}")
    print(f"   Memories stored: {final_stats['active_memories']}")
    print(f"   Average importance: {final_stats['avg_importance']}")
    print(f"   Type breakdown: {final_stats['type_breakdown']}")
    print()
    
    # Show retrieval example
    print("="*70)
    print("🔍 RETRIEVAL DEMONSTRATION")
    print("="*70)
    print("\nQuery: 'What are my preferences?'")
    print("Retrieved memories:")
    
    retrieved = memory.retrieve("preferences", limit=3)
    for mem in retrieved:
        print(f"   • {mem['summary'][:60]}...")
        print(f"     (type={mem['memory_type']}, importance={mem['importance_score']})")
    print()


def show_architecture():
    """Show memory subsystem architecture."""
    print("\n" + "="*70)
    print("🏗️  MEMORY ARCHITECTURE")
    print("="*70)
    print("""
    JARVIIS Core (Orchestrator)
         │
         │ During REASONING: memory.retrieve()
         │ During LEARNING:  memory.store()
         │
         ▼
    MemoryRouter (Decision Layer)
         │
         ├─► Compute importance score (rule-based heuristics)
         ├─► Classify memory type (interaction/fact/preference/error)
         ├─► Generate summary
         ├─► Decide whether to store
         │
         ▼
    SQLiteStore (Storage Layer)
         │
         └─► SQLite Database (jarviis_memory.db)
              • memories table (episodes)
              • memory_tags table (future)
              • Indexes for fast retrieval
    
    Key Features:
    ✅ Importance-aware storage (trivial chatter ignored)
    ✅ Type classification (interaction/fact/preference/error/system)
    ✅ Reinforcement learning (memories strengthen when recalled)
    ✅ Human-debuggable (SQLite, readable schema)
    ✅ Zero core changes required (paste-safe integration)
    ✅ Extensible schema (ready for embeddings/graphs)
    """)


def main():
    """Main entry point."""
    print_banner()
    show_architecture()
    
    print("\n" + "="*70)
    print("Press Enter to run demonstration...")
    print("="*70)
    input()
    
    demonstrate_memory()
    
    print("="*70)
    print("✅ Memory Demonstration Complete")
    print("="*70)
    print("\nMemory persists in 'jarviis_memory.db'")
    print("Use SQLite browser to inspect: sqlite3 jarviis_memory.db")
    print("\nTo clear memory: memory.clear()")
    print()


if __name__ == "__main__":
    main()
