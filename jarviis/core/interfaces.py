"""
JARVIIS Interface Contracts
Abstract base classes defining contracts for subsystems.

These interfaces establish the API surface that future implementations
must satisfy. The core orchestrator depends ONLY on these abstractions,
never on concrete implementations.

Design Principle: Dependency Inversion
- High-level modules (orchestrator) should not depend on low-level modules
- Both should depend on abstractions (these interfaces)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MemoryInterface(ABC):
    """
    Contract for memory subsystems.
    
    Future implementations might include:
    - Vector databases (ChromaDB, FAISS)
    - Graph memory (Neo4j)
    - Hybrid episodic/semantic stores
    """
    
    @abstractmethod
    def store(self, data: Dict[str, Any]) -> None:
        """
        Store information in memory.
        
        Args:
            data: Arbitrary dictionary of information to persist
        """
        pass
    
    @abstractmethod
    def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories.
        
        Args:
            query: Search query (could be text, embedding, etc.)
            limit: Maximum number of results
            
        Returns:
            List of memory objects, ordered by relevance
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all memory. Use with caution."""
        pass


class ReasoningInterface(ABC):
    """
    Contract for reasoning engines.
    
    Future implementations might include:
    - Local LLMs (Ollama, llama.cpp)
    - Cloud APIs (OpenAI, Anthropic)
    - Hybrid symbolic-neural reasoners
    """
    
    @abstractmethod
    def reason(self, context: Dict[str, Any]) -> str:
        """
        Generate a reasoned response.
        
        Args:
            context: Dictionary containing:
                - 'user_input': str
                - 'memory': Optional[List[Dict]] (retrieved memories)
                - 'history': Optional[List[Dict]] (conversation history)
                
        Returns:
            Reasoned response as string
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if reasoning engine is ready.
        
        Returns:
            True if model is loaded and ready
        """
        pass


class ToolInterface(ABC):
    """
    Contract for tool execution subsystems.
    
    Future implementations might include:
    - Filesystem operations
    - Web search/scraping
    - Code execution sandboxes
    - API integrations
    """
    
    @abstractmethod
    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a named tool with parameters.
        
        Args:
            tool_name: Identifier of the tool to run
            parameters: Tool-specific arguments
            
        Returns:
            Tool execution result (type varies by tool)
        """
        pass
    
    @abstractmethod
    def list_available_tools(self) -> List[str]:
        """
        List all registered tools.
        
        Returns:
            List of tool names
        """
        pass
    
    @abstractmethod
    def validate_tool(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Validate tool exists and parameters are correct.
        
        Args:
            tool_name: Tool to validate
            parameters: Parameters to check
            
        Returns:
            True if tool call is valid
        """
        pass


class LearningInterface(ABC):
    """
    Contract for learning/adaptation subsystems.
    
    Future implementations might include:
    - Few-shot learning from user corrections
    - Preference learning
    - Skill acquisition
    """
    
    @abstractmethod
    def learn_from_feedback(self, interaction: Dict[str, Any]) -> None:
        """
        Update internal models based on user feedback.
        
        Args:
            interaction: Dictionary containing:
                - 'user_input': str
                - 'system_output': str
                - 'feedback': str (e.g., "correct", "incorrect", "better: ...")
        """
        pass
    
    @abstractmethod
    def adapt_behavior(self, pattern: str, adjustment: Any) -> None:
        """
        Modify system behavior based on learned patterns.
        
        Args:
            pattern: Identified behavioral pattern
            adjustment: How to modify behavior
        """
        pass


class ReflectionInterface(ABC):
    """
    Contract for meta-cognitive reflection.
    
    Future implementations might include:
    - Self-evaluation of responses
    - Strategy selection/refinement
    - Error analysis
    """
    
    @abstractmethod
    def evaluate_response(self, context: Dict[str, Any], response: str) -> Dict[str, Any]:
        """
        Evaluate quality of a generated response.
        
        Args:
            context: Original context used for reasoning
            response: Generated response to evaluate
            
        Returns:
            Evaluation metrics (e.g., confidence, coherence, relevance)
        """
        pass
    
    @abstractmethod
    def suggest_improvement(self, evaluation: Dict[str, Any]) -> Optional[str]:
        """
        Suggest response improvements based on evaluation.
        
        Args:
            evaluation: Output from evaluate_response()
            
        Returns:
            Improved response if available, None otherwise
        """
        pass


# Placeholder implementations for testing core without dependencies

class DummyMemory(MemoryInterface):
    """Placeholder memory that does nothing."""
    
    def store(self, data: Dict[str, Any]) -> None:
        pass
    
    def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        return []
    
    def clear(self) -> None:
        pass


class DummyReasoner(ReasoningInterface):
    """Placeholder reasoner that returns canned responses."""
    
    def reason(self, context: Dict[str, Any]) -> str:
        user_input = context.get('user_input', '')
        return f"[PLACEHOLDER] I heard you say: '{user_input}'. Intelligence not yet implemented."
    
    def is_available(self) -> bool:
        return True


class DummyToolExecutor(ToolInterface):
    """Placeholder tool executor with no real tools."""
    
    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        return f"Tool '{tool_name}' executed (placeholder)"
    
    def list_available_tools(self) -> List[str]:
        return []
    
    def validate_tool(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        return False


class DummyLearner(LearningInterface):
    """Placeholder learner that doesn't actually learn."""
    
    def learn_from_feedback(self, interaction: Dict[str, Any]) -> None:
        pass
    
    def adapt_behavior(self, pattern: str, adjustment: Any) -> None:
        pass


class DummyReflector(ReflectionInterface):
    """Placeholder reflector with no real meta-cognition."""
    
    def evaluate_response(self, context: Dict[str, Any], response: str) -> Dict[str, Any]:
        return {"confidence": 0.5, "quality": "unknown"}
    
    def suggest_improvement(self, evaluation: Dict[str, Any]) -> Optional[str]:
        return None
