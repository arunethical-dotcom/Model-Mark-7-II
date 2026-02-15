#!/usr/bin/env python3
"""
JARVIIS Main Entry Point
Demonstrates the cognitive core in action.

This script shows:
1. Core initialization
2. Request processing through state machine
3. Observable state transitions
4. Clean error handling

Run: python main.py
"""

import sys
from core import Orchestrator
from config import get_settings
from reasoning.hybrid_reasoner import HybridReasoner


def print_banner():
    """Display JARVIIS startup banner."""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄               ║
║    ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌              ║
║     ▀▀▀▀▀█░█▀▀▀ ▐░█▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀▀▀▀█░▌              ║
║          ▐░▌    ▐░▌       ▐░▌▐░▌       ▐░▌              ║
║          ▐░▌    ▐░█▄▄▄▄▄▄▄█░▌▐░█▄▄▄▄▄▄▄█░▌              ║
║          ▐░▌    ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌              ║
║          ▐░▌    ▐░█▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀█░█▀▀               ║
║     ▄▄▄▄▄█░▌    ▐░▌       ▐░▌▐░▌     ▐░▌                ║
║    ▐░░░░░░░▌    ▐░▌       ▐░▌▐░▌      ▐░▌               ║
║     ▀▀▀▀▀▀▀      ▀         ▀  ▀        ▀                ║
║                                                          ║
║              V  I  I  S                                  ║
║          Cognitive Operating System                     ║
║                  v0.1.0                                  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def demonstrate_core():
    """
    Demonstrate core functionality with example interactions.
    """
    settings = get_settings()
    
    print(f"\n🧠 Initializing {settings.system_name} Core...")
    print(f"   Version: {settings.version}")
    print(f"   Architecture: FSM-Driven Orchestration")
    print(f"   State Validation: {'STRICT' if settings.strict_state_validation else 'PERMISSIVE'}")
    print()
    
    # Initialize orchestrator
    orchestrator = Orchestrator(reasoner=HybridReasoner())
    
    # Show initial status
    print("📊 Initial Status:")
    status = orchestrator.get_status()
    print(f"   State: {status['state']}")
    print(f"   Subsystems: All interfaces defined, implementations pending")
    print()
    
    # Example interactions
    test_inputs = [
        "Hello JARVIIS!",
        "What is the meaning of life?",
        "Calculate 2 + 2",
    ]
    
    print("=" * 60)
    print("🚀 PROCESSING TEST REQUESTS")
    print("=" * 60)
    print()
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n{'─' * 60}")
        print(f"Request {i}: {user_input}")
        print('─' * 60)
        
        response = orchestrator.process_request(user_input)
        
        print(f"\n💬 Response:")
        print(f"   {response}")
        print()
    
    # Show final status
    print("\n" + "=" * 60)
    print("📊 FINAL STATUS")
    print("=" * 60)
    final_status = orchestrator.get_status()
    print(f"Current State: {final_status['state']}")
    print(f"Total Requests Processed: {final_status['request_count']}")
    print(f"State History (last 5): {' -> '.join(final_status['state_history'])}")
    print()
    
    # Show what's next
    print("=" * 60)
    print("🔮 NEXT STEPS")
    print("=" * 60)
    print("""
To make JARVIIS intelligent, implement these interfaces:

1. ReasoningInterface → Connect local LLM (Ollama/llama.cpp)
2. MemoryInterface    → Add vector database (ChromaDB/FAISS)
3. ToolInterface      → Create tool executors (filesystem, web, etc.)
4. LearningInterface  → Implement feedback learning
5. ReflectionInterface → Add meta-cognitive evaluation

Then inject into orchestrator:
    orchestrator = Orchestrator(
        reasoner=YourLLMReasoner(),
        memory=YourVectorMemory(),
        tools=YourToolExecutor()
    )

The core is ready. Build on it.
""")
    
    print("✅ Core demonstration complete.\n")


def interactive_mode():
    """
    Run JARVIIS in interactive mode.
    """
    print("\n🎮 Entering Interactive Mode")
    print("Type 'quit', 'exit', or 'q' to stop\n")
    
    orchestrator = Orchestrator(reasoner=HybridReasoner())
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q', '']:
                print("\n👋 Goodbye!\n")
                break
            
            response = orchestrator.process_request(user_input)
            print(f"JARVIIS: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def main():
    """
    Main entry point.
    """
    print_banner()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--interactive':
            interactive_mode()
        elif sys.argv[1] == '--status':
            orchestrator = Orchestrator(reasoner=HybridReasoner())
            status = orchestrator.get_status()
            print("\n📊 System Status:")
            for key, value in status.items():
                print(f"   {key}: {value}")
            print()
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python main.py [--interactive|--status]")
    else:
        # Default: Run demonstration
        demonstrate_core()


if __name__ == "__main__":
    main()
