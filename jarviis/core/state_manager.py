"""
JARVIIS State Manager
Finite State Machine implementation for cognitive state control.

This module enforces strict state transitions and ensures the system
is always in a valid, observable state. Invalid transitions raise errors
to prevent undefined behavior.

State Philosophy:
- States represent cognitive phases, not technical statuses
- Transitions must be explicit and validated
- State is always queryable for debugging/monitoring
"""

from enum import Enum
from typing import Dict, Set, Optional
from datetime import datetime


class AgentState(Enum):
    """
    Valid cognitive states for JARVIIS.
    
    Each state represents a distinct phase in the request lifecycle:
    - IDLE: Awaiting input
    - LISTENING: Receiving and parsing input
    - REASONING: Planning response (future: LLM invocation)
    - EXECUTING: Running tools/actions (future: tool execution)
    - LEARNING: Updating memory (future: memory storage)
    - REFLECTING: Self-evaluation (future: meta-cognition)
    """
    IDLE = "idle"
    LISTENING = "listening"
    REASONING = "reasoning"
    EXECUTING = "executing"
    LEARNING = "learning"
    REFLECTING = "reflecting"


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class StateManager:
    """
    Manages agent state with strict FSM rules.
    
    Responsibilities:
    - Track current state
    - Validate state transitions
    - Log state history
    - Provide state observability
    
    Design Notes:
    - Immutable transition rules (defined at class level)
    - Thread-safe (no shared mutable state)
    - Observable (exposes current state and history)
    """
    
    # Valid state transitions (source -> allowed destinations)
    # This is the core FSM logic - modify carefully
    VALID_TRANSITIONS: Dict[AgentState, Set[AgentState]] = {
        AgentState.IDLE: {
            AgentState.LISTENING,  # Start processing input
        },
        AgentState.LISTENING: {
            AgentState.REASONING,  # Input received, start thinking
            AgentState.IDLE,       # Cancel/reset
        },
        AgentState.REASONING: {
            AgentState.EXECUTING,  # Need to use tools
            AgentState.LEARNING,   # Direct to memory update
            AgentState.REFLECTING, # Self-evaluate
            AgentState.IDLE,       # Simple response, done
        },
        AgentState.EXECUTING: {
            AgentState.REASONING,  # Tools done, resume thinking
            AgentState.LEARNING,   # Tools done, store results
            AgentState.IDLE,       # Tools done, complete
        },
        AgentState.LEARNING: {
            AgentState.REFLECTING, # Memory updated, self-evaluate
            AgentState.IDLE,       # Memory updated, complete
        },
        AgentState.REFLECTING: {
            AgentState.REASONING,  # Reflection suggests retry
            AgentState.IDLE,       # Reflection complete
        },
    }
    
    def __init__(self, initial_state: AgentState = AgentState.IDLE):
        """
        Initialize state manager.
        
        Args:
            initial_state: Starting state (default: IDLE)
        """
        self._current_state = initial_state
        self._state_history: list[tuple[AgentState, datetime]] = [
            (initial_state, datetime.now())
        ]
    
    @property
    def current_state(self) -> AgentState:
        """Get current state (read-only)."""
        return self._current_state
    
    def transition_to(self, new_state: AgentState) -> None:
        """
        Transition to a new state with validation.
        
        Args:
            new_state: Target state
            
        Raises:
            InvalidStateTransitionError: If transition is not allowed
        """
        if not self.is_valid_transition(new_state):
            raise InvalidStateTransitionError(
                f"Invalid transition: {self._current_state.value} -> {new_state.value}. "
                f"Allowed transitions from {self._current_state.value}: "
                f"{[s.value for s in self.VALID_TRANSITIONS[self._current_state]]}"
            )
        
        # Record transition
        self._current_state = new_state
        self._state_history.append((new_state, datetime.now()))
    
    def is_valid_transition(self, target_state: AgentState) -> bool:
        """
        Check if a state transition is valid.
        
        Args:
            target_state: Proposed next state
            
        Returns:
            True if transition is allowed
        """
        return target_state in self.VALID_TRANSITIONS.get(self._current_state, set())
    
    def get_allowed_transitions(self) -> Set[AgentState]:
        """
        Get all valid transitions from current state.
        
        Returns:
            Set of allowed target states
        """
        return self.VALID_TRANSITIONS.get(self._current_state, set())
    
    def reset(self) -> None:
        """Reset to IDLE state and clear history."""
        self._current_state = AgentState.IDLE
        self._state_history = [(AgentState.IDLE, datetime.now())]
    
    def get_state_history(self) -> list[tuple[AgentState, datetime]]:
        """
        Get complete state transition history.
        
        Returns:
            List of (state, timestamp) tuples
        """
        return self._state_history.copy()
    
    def get_last_n_states(self, n: int = 5) -> list[AgentState]:
        """
        Get the last N states (for debugging).
        
        Args:
            n: Number of states to retrieve
            
        Returns:
            List of recent states (newest last)
        """
        return [state for state, _ in self._state_history[-n:]]
    
    def is_in_state(self, state: AgentState) -> bool:
        """
        Check if currently in a specific state.
        
        Args:
            state: State to check
            
        Returns:
            True if current state matches
        """
        return self._current_state == state
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"StateManager(current={self._current_state.value}, history_length={len(self._state_history)})"
    
    def __str__(self) -> str:
        """Human-readable state description."""
        return f"Current State: {self._current_state.value}"
