#!/usr/bin/env python3
"""
JARVIIS Interactive Mode

Clean interactive CLI without demo sequences.
Directly interact with JARVIIS.

Run:
    python main_complete.py
"""

import sys
import time

# Core subsystems
from core import Orchestrator
from config.settings import CoreSettings
from memory import MemoryRouter
from reasoning import ReasoningEngine
from tools import ToolManager
from learning import LearningManager
from monitoring import ResourceMonitor


from core.state_manager import StateManager

def initialize_system():
    """
    Initialize all JARVIIS subsystems with new orchestration logic.
    """
    settings = CoreSettings(
        enable_memory=True,
        enable_reasoning=True,
        enable_tools=True,
        enable_learning=True,
        enable_reflection=False
    )

    state_manager = StateManager()
    memory = MemoryRouter("jarviis_demo.db")
    reasoner = ReasoningEngine()
    tools = ToolManager()
    learner = LearningManager(memory_router=memory)
    monitor = ResourceMonitor()

    orchestrator = Orchestrator(
        state_manager=state_manager,
        memory_router=memory,
        reasoning_engine=reasoner,
        tool_manager=tools,
        learning_manager=learner,
        resource_monitor=monitor
    )
    orchestrator.settings = settings

    return {
        "orchestrator": orchestrator,
        "monitor": monitor
    }


def interactive_loop(system):
    """
    Start direct interactive conversation loop.
    """
    orchestrator = system["orchestrator"]
    monitor = system["monitor"]

    print("\n🧠 JARVIIS is online.")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                print("\nJARVIIS: Goodbye.\n")
                break

            start_time = time.time()

            response = orchestrator.process_request(user_input)

            latency_ms = monitor.measure_latency(start_time)

            print(f"JARVIIS: {response}")
            print(f"(Latency: {latency_ms}ms)\n")

        except KeyboardInterrupt:
            print("\n\nJARVIIS: Session interrupted. Goodbye.\n")
            break

        except Exception as e:
            print(f"\n[ERROR] {e}\n")


def main_complete():
    """
    Entry point.
    """
    system = initialize_system()
    interactive_loop(system)


if __name__ == "__main__":
    main()
