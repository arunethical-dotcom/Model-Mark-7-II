"""
JARVIIS Learning Manager
Coordination bridge between orchestrator and memory.

Architecture Choice: Coordination Bridge
---------------------------------------
Evaluated:
- Passive logging → Too simple
- Event-based learning → Too complex for Phase 2
- Memory consolidation orchestration → Too early
- Learning as coordination → ✅ CHOSEN

Why Coordination Bridge?
- Delegates to MemoryRouter (separation of concerns)
- Enforces learning happens only in LEARNING state
- No intelligence, just routing
- Prepares for Phase 4 meta-learning

Design Principle:
- Learning manager coordinates, memory stores
- No business logic
- No state
- Just a clean bridge
"""

from typing import Dict, Any, Optional
from datetime import datetime


class LearningManager:
    """
    Learning coordination layer.
    
    Responsibilities:
    - Receive interaction summaries from orchestrator
    - Route to MemoryRouter with proper structure
    - Enforce learning happens only in correct state
    - Track learning events
    
    Does NOT:
    - Decide what to learn (memory router does that)
    - Access database directly (memory router does that)
    - Perform reasoning (reasoning engine does that)
    - Modify behavior (reflection does that)
    
    Philosophy: A bridge, not a brain.
    """
    
    def __init__(self, memory_router=None):
        """
        Initialize learning manager.
        
        Args:
            memory_router: MemoryRouter instance (optional)
        """
        self.memory_router = memory_router
        self._learning_event_count = 0
    
    def learn_from_feedback(self, interaction: Dict[str, Any]) -> None:
        """
        Learn from user feedback (implements LearningInterface).
        
        This is called during LEARNING state by orchestrator.
        
        Args:
            interaction: Dictionary containing:
                - 'user_input': str
                - 'system_output': str
                - 'feedback': str (optional)
                - 'timestamp': str (optional)
        """
        try:
            # Validate interaction data
            if not self._validate_interaction(interaction):
                print("[LEARNING] Invalid interaction data, skipping")
                return
            
            # Route to memory if available
            if self.memory_router:
                # Structure data for memory storage
                memory_data = {
                    'user_input': interaction.get('user_input', ''),
                    'system_response': interaction.get('system_output', ''),
                    'timestamp': interaction.get('timestamp', datetime.now().isoformat()),
                    'feedback': interaction.get('feedback'),  # Optional
                }
                
                # Delegate to memory router
                self.memory_router.store(memory_data)
                
                self._learning_event_count += 1
                
                print(f"[LEARNING] Stored interaction (event #{self._learning_event_count})")
            else:
                print("[LEARNING] No memory router configured, skipping storage")
                
        except Exception as e:
            # Fail gracefully - learning failure shouldn't crash system
            print(f"[LEARNING] ERROR: {e}")
            # Don't re-raise - FSM safety over learning completeness
    
    def adapt_behavior(self, pattern: str, adjustment: Any) -> None:
        """
        Adapt system behavior based on patterns.
        
        Phase 4 feature - not implemented in Phase 2.
        
        Args:
            pattern: Identified behavioral pattern
            adjustment: How to modify behavior
        """
        print(f"[LEARNING] Behavior adaptation requested: {pattern}")
        print(f"[LEARNING] Adaptation is a Phase 4 feature (not implemented yet)")
        # Phase 4: Update reasoning parameters, tool preferences, etc.
    
    def record_interaction(
        self,
        user_input: str,
        system_response: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Simplified interaction recording.
        
        This is a convenience method that wraps learn_from_feedback
        with a cleaner API for the orchestrator.
        
        Args:
            user_input: User's input
            system_response: System's response
            timestamp: ISO timestamp (optional)
            metadata: Additional context (optional)
        """
        interaction = {
            'user_input': user_input,
            'system_output': system_response,
            'timestamp': timestamp or datetime.now().isoformat(),
        }
        
        if metadata:
            interaction['metadata'] = metadata
        
        self.learn_from_feedback(interaction)
    
    def learn(self, user_input: str, assistant_response: str) -> None:
        """
        Simplified learning method for backward compatibility.
        
        This is an alias for record_interaction() to maintain compatibility
        with orchestrator and other components that call learn().
        
        Args:
            user_input: User's input
            assistant_response: Assistant's response
        """
        self.record_interaction(user_input, assistant_response)
    
    def _validate_interaction(self, interaction: Dict[str, Any]) -> bool:
        """
        Validate interaction data structure and content safety.
        
        Args:
            interaction: Interaction dictionary to validate
            
        Returns:
            True if valid and safe
        """
        # Must have user_input or system_output
        has_input = bool(interaction.get('user_input'))
        has_output = bool(interaction.get('system_output'))
        
        if not (has_input or has_output):
            return False
        
        # Must be a dict
        if not isinstance(interaction, dict):
            return False

        # MEMORY FIREWALL: Check for identity leaks in system output
        if has_output:
            response = interaction.get('system_output', '')
            if not self._is_safe_to_store(response):
                print("[LEARNING] 🛡️ Memory Firewall blocked unsafe content")
                return False
        
        return True

    def _is_safe_to_store(self, content: str) -> bool:
        """
        Check if content is safe to store in memory.
        Blocks identity statements, role declarations, and hallucinations.
        """
        unsafe_patterns = [
            "I am", "I'm a", "my creator", "created by", "my purpose",
            "as an AI", "language model", "JARVIIS identity"
        ]
        lower_content = content.lower()
        for pattern in unsafe_patterns:
            if pattern in lower_content:
                return False
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning manager statistics."""
        return {
            'learning_event_count': self._learning_event_count,
            'memory_router_configured': self.memory_router is not None,
            'phase': 'Phase 2 (coordination only)'
        }
