"""
JARVIIS — Full Phase 3 Pipeline
Cognitive Governance + Memory + LLM

This is the main entrypoint. Wire all three layers together.

Usage:
    from jarviis import JARVIISAgent

    agent = JARVIISAgent(backend="ollama")
    response = agent.chat("What architecture does JARVIIS use?")
    print(response)
"""

from cognitive_core import CognitiveOrchestrator, classify_context
from memory_manager import MemoryManager
from llm_backends import OllamaBackend, MockBackend


class JARVIISAgent:
    """
    JARVIIS Phase 3 — complete pipeline.

    Architecture (authority order, highest → lowest):
    ┌─────────────────────────────────────────────┐
    │  1. Identity Anchor      [SYSTEM AUTHORITY]  │
    │  2. Context Mode Frame   [DOMAIN CONTROL]    │
    │  3. Memory Context       [COMPRESSED]        │
    │  4. Conversation History [TRIMMED: 6 turns]  │
    │  5. User Input           [CURRENT TURN]      │
    │                              ↓               │
    │  6. LLM Generation       [MODEL INFERENCE]   │
    │                              ↓               │
    │  7. Response Validation  [GOVERNANCE GATE]   │
    │     → Identity leak check                    │
    │     → Domain leak check                      │
    │     → Mode-specific checks                   │
    │     → Auto-correct or re-generate            │
    └─────────────────────────────────────────────┘
    """

    def __init__(
        self,
        backend: str   = "llamacpp",    # "llamacpp" | "mock"
        model: str     = "mistral:instruct",  # kept for backward compatibility
        db_path: str   = "/tmp/jarviis_memory.db",
        verbose: bool  = False,
    ):
        self.verbose = verbose

        # LLM backends - dual model setup
        if backend == "llamacpp":
            # Qwen 1.5B for governance (fast validation)
            self.governance_llm = LlamaCppBackend(
                host="http://localhost:8081",
                temperature=0.3,
                max_tokens=256
            )
            # Mistral 7B for deep reasoning
            self.reasoning_llm = LlamaCppBackend(
                host="http://localhost:8080",
                temperature=0.4,
                max_tokens=512
            )
        elif backend == "mock":
            self.governance_llm = MockBackend()
            self.reasoning_llm = MockBackend()
        else:
            raise ValueError(f"Unknown backend: {backend}. Use 'llamacpp' or 'mock'")

        # Memory
        self.memory = MemoryManager(db_path=db_path)

        # Orchestrator (wraps LLM with governance)
        self.orchestrator = CognitiveOrchestrator(
            governance_backend=self.governance_llm,
            reasoning_backend=self.reasoning_llm
        )

        # In-session conversation history
        self._history: list[dict] = []

        if verbose:
            if not self.reasoning_llm.health_check():
                print(f"⚠️  WARNING: Reasoning LLM backend not reachable. Check llama-server on port 8080.")
            elif not self.governance_llm.health_check():
                print(f"⚠️  WARNING: Governance LLM backend not reachable. Check llama-server on port 8081.")
            else:
                print(f"✅ JARVIIS online — backend: {backend}")
                print(f"   Governance: Qwen 1.5B (port 8081)")
                print(f"   Reasoning: Mistral 7B (port 8080)")

    def chat(self, user_input: str) -> str:
        """
        Main chat method. Call this for every user turn.
        Returns the governed response string.
        """
        # Retrieve relevant memories
        memory_snippets = self.memory.retrieve(user_input, top_k=6)

        # Run governed pipeline
        response = self.orchestrator.run(
            user_input=user_input,
            memory_snippets=memory_snippets,
            conversation_history=self._history,
        )

        # Update history
        self._history.append({"role": "user",      "content": user_input})
        self._history.append({"role": "assistant",  "content": response})
        self._history = self._history[-12:]  # keep last 6 turns (12 messages)

        # Extract + store key facts from this turn
        self.memory.store_conversation_turn(user_input, response)

        if self.verbose:
            stats = self.orchestrator.last_stats()
            mode  = classify_context(user_input).value
            print(f"\n[JARVIIS] mode={stats.get('mode','?')} | "
                  f"tokens~{stats.get('tokens_estimated','?')} | "
                  f"attempts={stats.get('attempts','?')} | "
                  f"latency={stats.get('latency_ms','?')}ms")

        return response

    def remember(self, fact: str, importance: float = 0.8):
        """Manually inject a high-importance memory."""
        mem_id = self.memory.store(fact, source="user", importance=importance)
        if self.verbose:
            print(f"[MEMORY] Stored: {fact[:60]}... (id={mem_id})")
        return mem_id

    def memory_stats(self) -> dict:
        return self.memory.get_stats()

    def reset_history(self):
        """Clear in-session history (memory persists)."""
        self._history = []

    def run_validation_test(self) -> dict:
        """
        Runs the full governance pipeline against a MockBackend
        that deliberately injects identity violations.
        Returns a test report.
        """
        from cognitive_core import ResponseValidator, ContextMode

        validator = ResponseValidator()
        test_cases = [
            {
                "input": "I am Qwen, a language model made by Alibaba.",
                "mode": ContextMode.CASUAL_CHAT,
                "should_fail": True,
            },
            {
                "input": "Great question! Certainly, as an AI I'd be happy to help.",
                "mode": ContextMode.TASK_EXECUTION,
                "should_fail": True,
            },
            {
                "input": "As JARVIIS, your architecture needs three new layers: identity anchor, "
                         "context frame, and response validator.",
                "mode": ContextMode.ARCHITECTURE,
                "should_fail": False,
            },
            {
                "input": "I don't have personal opinions as an AI language model.",
                "mode": ContextMode.META_DISCUSSION,
                "should_fail": True,
            },
        ]

        results = []
        passed = 0
        for tc in test_cases:
            result = validator.validate(tc["input"], tc["mode"])
            test_passed = (not result.passed) == tc["should_fail"]
            if test_passed:
                passed += 1
            results.append({
                "input_snippet": tc["input"][:50],
                "expected_fail": tc["should_fail"],
                "validator_caught": not result.passed,
                "test_passed": test_passed,
                "violations": result.violations,
            })

        return {
            "total": len(test_cases),
            "passed": passed,
            "success_rate": f"{passed}/{len(test_cases)}",
            "details": results,
        }


# ─────────────────────────────────────────────
# CLI Demo
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    # Default to mock for safe testing without a running model
    backend = sys.argv[1] if len(sys.argv) > 1 else "mock"

    print(f"""
╔══════════════════════════════════════╗
║         JARVIIS — Phase 3           ║
║  Cognitive Governance Active ✅     ║
╚══════════════════════════════════════╝
Backend: {backend}
Commands: 'quit', 'stats', 'test', 'remember: <fact>'
""")

    agent = JARVIISAgent(backend=backend, verbose=True)

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "quit":
                break
            elif user_input.lower() == "stats":
                print(f"Memory stats: {agent.memory_stats()}")
                continue
            elif user_input.lower() == "test":
                results = agent.run_validation_test()
                print(f"\nValidation test: {results['success_rate']} passed")
                for r in results["details"]:
                    status = "✅" if r["test_passed"] else "❌"
                    print(f"  {status} {r['input_snippet']}...")
                continue
            elif user_input.lower().startswith("remember:"):
                fact = user_input[9:].strip()
                agent.remember(fact)
                print(f"Stored: {fact}")
                continue

            response = agent.chat(user_input)
            print(f"\nJARVIIS: {response}")

        except KeyboardInterrupt:
            print("\nGoodbye.")
            break
