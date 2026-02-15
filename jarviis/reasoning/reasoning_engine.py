"""
JARVIIS Reasoning Engine
Decision-object based reasoning with optional LLM integration.

Architecture Choice: Decision-Object Pattern
------------------------------------------
Evaluated:
- Rule-based reasoning → Too rigid
- Template reasoning → Not extensible
- LLM-style reasoning → Phase 3
- Decision-object reasoning → ✅ CHOSEN

Why Decision-Object?
- Returns structured decision (not just string)
- Separates "what to do" from "how to respond"
- Enables tool dispatch without string parsing
- Easy to test and debug
- Ready for LLM drop-in replacement

Design Principle:
- Reasoning produces decisions, orchestrator executes them
- No state mutation
- Deterministic behavior
- LLMs augment responses, not decisions

LLM Integration (Phase 3):
- Rules decide WHAT to do (decision type)
- LLMs decide HOW to respond (response text)
- Fallback to rules if LLM unavailable
"""

from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime
import subprocess
import json

# Import governed LLM backend
try:
    from .governed_llm_backend import GovernedLLMBackend
    GOVERNANCE_AVAILABLE = True
    print("[REASONING] ✅ Governance layer imported successfully")
except ImportError as e:
    print(f"[REASONING] ❌ Governance import failed: {e}")
    import traceback
    traceback.print_exc()
    GOVERNANCE_AVAILABLE = False


class DecisionType(Enum):
    """Types of decisions the reasoning engine can make."""
    SIMPLE_REPLY = "simple_reply"      # Direct response, no tools
    TOOL_REQUIRED = "tool_required"    # Need to execute tool(s)
    LEARNING_ONLY = "learning_only"    # Store but don't respond
    CLARIFICATION = "clarification"    # Need more info from user
    ERROR = "error"                    # Something went wrong


class ReasoningDecision:
    """
    Structured decision object returned by reasoning engine.
    
    This object tells the orchestrator WHAT to do,
    not HOW to do it (orchestrator decides execution).
    """
    
    def __init__(
        self,
        decision_type: DecisionType,
        response: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize reasoning decision.
        
        Args:
            decision_type: Type of decision made
            response: Text response to user
            tool_calls: List of tools to execute (if TOOL_REQUIRED)
            confidence: Confidence in decision (0.0-1.0)
            metadata: Additional context
        """
        self.decision_type = decision_type
        self.response = response
        self.tool_calls = tool_calls or []
        self.confidence = confidence
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
    
    def requires_tools(self) -> bool:
        """Check if decision requires tool execution."""
        return self.decision_type == DecisionType.TOOL_REQUIRED
    
    def is_error(self) -> bool:
        """Check if decision represents an error."""
        return self.decision_type == DecisionType.ERROR
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'decision_type': self.decision_type.value,
            'response': self.response,
            'tool_calls': self.tool_calls,
            'confidence': self.confidence,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }


class ReasoningEngine:
    """
    Hybrid reasoning engine with optional LLM integration.
    
    Responsibilities:
    - Analyze user input + memory context
    - Decide response type (rule-based)
    - Generate response text (LLM or rules)
    - Return structured decision
    
    Does NOT:
    - Execute tools (orchestrator's job)
    - Write to memory (learning manager's job)
    - Maintain state (stateless)
    - Let LLMs make decisions (rules decide, LLMs speak)
    
    Philosophy: Rules decide, models speak.
    """
    
    def __init__(self, enable_llm: bool = True, use_governance: bool = True):
        """
        Initialize reasoning engine.
        
        Args:
            enable_llm: Enable Ollama LLM integration (default: True)
            use_governance: Use governance layer for LLM calls (default: True)
        """
        self._decision_count = 0
        
        # LLM Configuration
        self.enable_llm = enable_llm and GOVERNANCE_AVAILABLE
        self.use_governance = use_governance and GOVERNANCE_AVAILABLE
        self.fast_model = "smollm2"  # Lightweight for simple responses
        self.deep_model = "hermes-mistral"  # Deeper reasoning for questions
        self.llm_timeout = 30  # seconds
        
        # Initialize governed backend if available
        self.governed_backend = None
        if self.use_governance and GOVERNANCE_AVAILABLE:
            try:
                print("[REASONING] Attempting to initialize GovernedLLMBackend...")
                self.governed_backend = GovernedLLMBackend(
                    backend_type="ollama",
                    verbose=False
                )
                print("[REASONING] ✅ Governance layer active")
            except Exception as e:
                print(f"[REASONING] ❌ Governance init failed: {e}")
                import traceback
                traceback.print_exc()
                self.use_governance = False
        else:
            if not GOVERNANCE_AVAILABLE:
                print("[REASONING] ❌ GOVERNANCE_AVAILABLE is False - imports failed")
            if not self.use_governance:
                print("[REASONING] ⚠️ use_governance is False - governance disabled")
        
    def reason(self, user_input: str, context: Dict[str, Any]) -> str:
        """Pure passthrough - all intelligence in CognitiveOrchestrator."""
        
        # Direct passthrough to backend
        if self.governed_backend:
             # Ensure history is in correct format (List[Dict])
             raw_history = context.get('history', [])
             formatted_history = []
             
             for item in raw_history:
                 if isinstance(item, dict) and 'role' in item and 'content' in item:
                     formatted_history.append(item)
                 elif isinstance(item, str):
                     formatted_history.append({"role": "user", "content": f"[History] {item}"})
             
             response = self.governed_backend.generate(
                prompt=user_input,
                memory_snippets=context.get('memories', []),
                conversation_history=formatted_history,
                model=self._select_model(user_input)  # Dynamic model selection
             )
        else:
             response = "Governance backend unavailable."

        return response

    def _select_model(self, user_input: str) -> str:
        """
        Dynamically select model based on query complexity.
        
        Strategy:
        - Short, simple queries -> qwen-local (Fast)
        - Complex, analytical queries -> hermes-local (Smart)
        """
        # 1. Complexity Keywords
        complexity_keywords = [
            "explain", "analyze", "why", "how", "detail", "compare", 
            "design", "architect", "code", "debug", "plan", "strategy",
            "write", "script", "create", "generate"
        ]
        
        # 2. Length Heuristic
        word_count = len(user_input.split())
        
        # Check heuristics
        is_complex = any(keyword in user_input.lower() for keyword in complexity_keywords)
        is_long = word_count > 10
        
        if is_complex or is_long:
            return self.deep_model  # hermes-local
        
        return self.fast_model  # qwen-local

    def reason_with_decision(self, context: Dict[str, Any]) -> ReasoningDecision:
        """
        Advanced reasoning that returns structured decision.
        """
        response = self.reason(context)
        
        return ReasoningDecision(
            decision_type=DecisionType.SIMPLE_REPLY,
            response=response,
            confidence=1.0
        )

    def is_available(self) -> bool:
        """Check if reasoning engine is ready."""
        return True
