"""
JARVIIS Memory Router
Decision layer that sits between orchestrator and storage.

Responsibilities:
- Receive structured interaction data
- Compute importance scores (rule-based heuristics)
- Decide what to store and what to skip
- Route read requests appropriately
- Implement MemoryInterface contract

Does NOT contain:
- SQL queries (delegates to SQLiteStore)
- FSM logic (orchestrator's job)
- Embeddings or ML (Phase 3+)
- Async operations (synchronous only)

Philosophy:
- Deterministic and testable
- Fail gracefully (never crash system)
- Explainable decisions
- Separation of concerns
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from memory.sqlite_store import SQLiteStore


class MemoryRouter:
    """
    Intelligence-free routing layer for memory operations.
    
    This class makes decisions about WHAT to store and HOW to retrieve,
    but delegates the actual storage to SQLiteStore.
    
    Design: Rules-based heuristics, no machine learning.
    """
    
    # Importance scoring constants (explainable, tunable)
    IMPORTANCE_BASE = 1
    IMPORTANCE_REPETITION = 1      # User repeats information
    IMPORTANCE_PREFERENCE = 1      # User expresses preference
    IMPORTANCE_ERROR = 2           # Error or correction occurred
    IMPORTANCE_EXPLICIT = 3        # User says "remember this"
    IMPORTANCE_QUESTION = 1        # User asks a question
    
    # Storage thresholds
    MIN_IMPORTANCE_TO_STORE = 1    # Store everything by default (filter on retrieval)
    DEFAULT_RETRIEVAL_LIMIT = 5    # Max memories to return
    
    def __init__(self, db_path: str = "jarviis_memory.db"):
        """
        Initialize memory router.
        
        Args:
            db_path: Path to SQLite database
        """
        self.storage = SQLiteStore(db_path)
        self._interaction_count = 0
    
    # ========================================================================
    # Public API - Implements MemoryInterface
    # ========================================================================
    
    def store(self, data: Dict[str, Any]) -> None:
        """
        Store information in memory (called during LEARNING phase).
        
        Decision logic:
        1. Compute importance score
        2. If importance >= threshold, store
        3. Otherwise, skip (log if needed)
        
        Args:
            data: Dictionary containing interaction data
                Expected keys: user_input, system_response, timestamp
        """
        try:
            # Extract data
            user_input = data.get('user_input', '')
            system_response = data.get('system_response', '')
            timestamp = data.get('timestamp', datetime.now().isoformat())
            
            # Compute importance
            importance = self._compute_importance(user_input, system_response, data)
            
            # Determine memory type
            memory_type = self._classify_memory_type(user_input, system_response, data)
            
            # Generate summary
            summary = self._generate_summary(user_input, system_response)
            
            # Decision: Store or skip?
            if importance >= self.MIN_IMPORTANCE_TO_STORE:
                # Prepare metadata
                metadata = json.dumps({
                    'interaction_count': self._interaction_count,
                    'raw_data': {k: v for k, v in data.items() 
                                if k not in ['user_input', 'system_response', 'timestamp']}
                })
                
                # Store via SQLite layer
                memory_id = self.storage.insert_memory(
                    memory_type=memory_type,
                    summary=summary,
                    importance_score=importance,
                    user_input=user_input,
                    system_response=system_response,
                    metadata=metadata,
                    created_at=timestamp
                )
                
                if memory_id:
                    print(f"[MEMORY] Stored interaction (ID={memory_id}, importance={importance})")
                else:
                    print(f"[MEMORY] Failed to store interaction")
            else:
                # Skip trivial interactions
                print(f"[MEMORY] Skipped low-importance interaction (score={importance})")
            
            self._interaction_count += 1
            
        except Exception as e:
            # Fail gracefully - memory failure shouldn't crash system
            print(f"[ERROR] Memory storage failed: {e}")
            # Don't re-raise - FSM safety over memory completeness
    
    def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories (called during REASONING phase).
        
        Strategy (Phase 2A - no embeddings):
        1. Get recent memories (temporal relevance)
        2. Get important memories (importance-based)
        3. Merge and deduplicate
        4. Return top N
        
        Args:
            query: Search query (currently unused - no semantic search yet)
            limit: Maximum memories to return
            
        Returns:
            List of relevant memory dictionaries
        """
        try:
            # Strategy: Combine recent + important
            # Phase 3 will add semantic search via embeddings
            
            recent_memories = self.storage.fetch_recent_memories(limit=limit)
            important_memories = self.storage.fetch_important_memories(
                min_importance=2,
                limit=limit
            )
            
            # Merge and deduplicate by ID
            seen_ids = set()
            merged = []
            
            # Prioritize important memories first
            for mem in important_memories:
                if mem['id'] not in seen_ids:
                    merged.append(mem)
                    seen_ids.add(mem['id'])
            
            # Fill remaining slots with recent memories
            for mem in recent_memories:
                if mem['id'] not in seen_ids and len(merged) < limit:
                    merged.append(mem)
                    seen_ids.add(mem['id'])
            
            # Reinforce retrieved memories (they proved useful)
            for mem in merged:
                self.storage.reinforce_memory(mem['id'])
            
            return merged[:limit]
            
        except Exception as e:
            print(f"[ERROR] Memory retrieval failed: {e}")
            return []  # Return empty list on failure
    
    def clear(self) -> None:
        """
        Clear all memories.
        
        USE WITH CAUTION - typically for testing only.
        """
        try:
            success = self.storage.clear_all_memories()
            if success:
                print("[MEMORY] All memories cleared")
                self._interaction_count = 0
            else:
                print("[MEMORY] Failed to clear memories")
        except Exception as e:
            print(f"[ERROR] Memory clear failed: {e}")
    
    def store_conversation_turn(self, user_input: str, assistant_response: str) -> Optional[int]:
        """
        Convenience method to store a conversation turn.
        
        This is a wrapper around store() for backward compatibility
        with orchestrator and other components.
        
        Args:
            user_input: User's message
            assistant_response: Assistant's response
            
        Returns:
            Memory ID if stored successfully, None otherwise
        """
        try:
            data = {
                'user_input': user_input,
                'system_response': assistant_response,
                'timestamp': datetime.now().isoformat()
            }
            
            # Call the main store method
            self.store(data)
            
            # Return the last inserted ID (approximation)
            # In a production system, we'd modify store() to return the ID
            return self._interaction_count
            
        except Exception as e:
            print(f"[ERROR] Failed to store conversation turn: {e}")
            return None
    
    # ========================================================================
    # Additional Retrieval Methods (Beyond Interface)
    # ========================================================================
    
    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent memories without importance filtering."""
        return self.storage.fetch_recent_memories(limit=limit)
    
    def get_important(self, min_importance: int = 2, limit: int = 10) -> List[Dict[str, Any]]:
        """Get memories above importance threshold."""
        return self.storage.fetch_important_memories(min_importance, limit)
    
    def get_by_type(self, memory_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get memories of a specific type."""
        return self.storage.fetch_by_type_and_importance(memory_type, min_importance=1, limit=limit)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        stats = self.storage.get_stats()
        stats['interaction_count'] = self._interaction_count
        return stats
    
    # ========================================================================
    # Internal Decision Logic (Explainable Heuristics)
    # ========================================================================
    
    def _compute_importance(
        self,
        user_input: str,
        system_response: str,
        data: Dict[str, Any]
    ) -> int:
        """
        Compute importance score using rule-based heuristics.
        
        Scoring rules (explainable):
        - Base score: 1
        - +1 if user repeats information
        - +1 if user expresses preference (like/dislike/prefer)
        - +2 if error or correction mentioned
        - +3 if explicit "remember" instruction
        - +1 if user asks a question
        
        Args:
            user_input: User's message
            system_response: System's response
            data: Additional context
            
        Returns:
            Integer importance score (1-10 typical range)
        """
        score = self.IMPORTANCE_BASE
        
        if not user_input:
            return score
        
        user_lower = user_input.lower()
        
        # Explicit memory instruction
        if any(keyword in user_lower for keyword in ['remember', 'don\'t forget', 'note that']):
            score += self.IMPORTANCE_EXPLICIT
        
        # Error or correction
        if any(keyword in user_lower for keyword in ['wrong', 'error', 'mistake', 'actually', 'correction']):
            score += self.IMPORTANCE_ERROR
        
        # Preference expression
        if any(keyword in user_lower for keyword in ['i like', 'i prefer', 'i dislike', 'i love', 'i hate']):
            score += self.IMPORTANCE_PREFERENCE
        
        # Question (user seeking information)
        if '?' in user_input or user_lower.startswith(('what', 'why', 'how', 'when', 'where', 'who')):
            score += self.IMPORTANCE_QUESTION
        
        # Repetition detection (simple: check if similar to recent memories)
        # Phase 3 will use embeddings for better similarity
        recent = self.storage.fetch_recent_memories(limit=3)
        for mem in recent:
            if mem.get('user_input') and self._is_similar(user_input, mem['user_input']):
                score += self.IMPORTANCE_REPETITION
                break
        
        return min(score, 10)  # Cap at 10 for consistency
    
    def _classify_memory_type(
        self,
        user_input: str,
        system_response: str,
        data: Dict[str, Any]
    ) -> str:
        """
        Classify memory type based on content.
        
        Types: interaction / fact / preference / error / system
        
        Args:
            user_input: User's message
            system_response: System's response
            data: Additional context
            
        Returns:
            Memory type string
        """
        if not user_input:
            return 'system'
        
        user_lower = user_input.lower()
        
        # Error/correction
        if any(keyword in user_lower for keyword in ['wrong', 'error', 'mistake', 'correction']):
            return 'error'
        
        # Preference
        if any(keyword in user_lower for keyword in ['i like', 'i prefer', 'i dislike', 'my favorite']):
            return 'preference'
        
        # Fact (user teaching system)
        if any(keyword in user_lower for keyword in ['remember that', 'note that', 'fyi', 'for your information']):
            return 'fact'
        
        # Default: interaction
        return 'interaction'
    
    def _generate_summary(self, user_input: str, system_response: str) -> str:
        """
        Generate human-readable summary of interaction.
        
        Args:
            user_input: User's message
            system_response: System's response
            
        Returns:
            Short summary string
        """
        # Simple truncation for now
        # Phase 3 can use LLM for better summarization
        max_len = 100
        
        if user_input:
            summary = f"User: {user_input[:max_len]}"
            if len(user_input) > max_len:
                summary += "..."
        else:
            summary = "System event"
        
        return summary
    
    def _is_similar(self, text1: str, text2: str) -> bool:
        """
        Check if two texts are similar (simple string matching).
        
        Phase 3 will use embeddings for semantic similarity.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            True if similar (>70% word overlap)
        """
        if not text1 or not text2:
            return False
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1 & words2)
        union = len(words1 | words2)
        
        similarity = overlap / union if union > 0 else 0
        
        return similarity > 0.7
