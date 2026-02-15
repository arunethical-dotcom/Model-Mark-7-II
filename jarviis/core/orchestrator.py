"""
Orchestrator - Main coordination engine for JARVIIS.

This module coordinates memory, reasoning, tools, and state management
to execute complete user interactions.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main coordination engine for JARVIIS cognitive system.
    
    Coordinates:
    - State management (FSM)
    - Memory operations
    - Reasoning engine
    - Tool execution
    - Learning and adaptation
    """
    
    def __init__(
        self,
        state_manager,
        memory_router,
        reasoning_engine,
        tool_manager,
        learning_manager=None,
        resource_monitor=None
    ):
        """
        Initialize orchestrator.
        
        Args:
            state_manager: State management (FSM)
            memory_router: Memory routing system
            reasoning_engine: LLM reasoning engine
            tool_manager: Tool execution manager
            learning_manager: Optional learning system
            resource_monitor: Optional resource monitoring
        """
        self.state_manager = state_manager
        self.memory_router = memory_router
        self.reasoning_engine = reasoning_engine
        self.tool_manager = tool_manager
        self.learning_manager = learning_manager
        self.resource_monitor = resource_monitor
        
        self.request_count = 0
        self.start_time = datetime.now()
        
        logger.info("[ORCHESTRATOR] Orchestrator initialized")
    
    def process_request(self, user_input: str) -> str:
        """
        Process a complete user request through the cognitive pipeline.
        
        Pipeline:
        1. LISTENING: Parse and validate input
        2. REASONING: Generate response
        3. LEARNING: Extract and store knowledge
        4. Return to IDLE
        
        Args:
            user_input: User's input text
        
        Returns:
            Assistant's response
        """
        self.request_count += 1
        request_id = self.request_count
        
        logger.info(f"[ORCHESTRATOR] Processing request #{request_id}: '{user_input[:50]}...'")
        
        start_time = datetime.now()
        response = None
        
        try:
            # Phase 1: LISTENING
            self._transition_state('LISTENING')
            self._execute_listening(user_input)
            
            # Phase 2: REASONING
            self._transition_state('REASONING')
            response = self._execute_reasoning(user_input)
            
            # Phase 3: LEARNING
            self._transition_state('LEARNING')
            self._execute_learning(user_input, response)
            
            # Return to IDLE
            self._transition_state('IDLE')
            
            # Calculate latency
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.info(f"[ORCHESTRATOR] Request #{request_id} completed successfully")
            logger.debug(f"[ORCHESTRATOR] Latency: {latency:.2f}ms")
            
            return response
        
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error processing request #{request_id}: {e}", exc_info=True)
            
            # Try to recover state
            try:
                self._transition_state('IDLE')
            except:
                pass
            
            return "I apologize, but I encountered an error processing your request."
    
    def _transition_state(self, new_state: str):
        """
        Transition to new state.
        
        Args:
            new_state: Target state name
        """
        logger.info(f"[ORCHESTRATOR] State transition -> {new_state}")
        
        if self.state_manager:
            try:
                # Map string names back to Enum if necessary for state_manager
                from core.state_manager import AgentState
                state_map = {
                    'IDLE': AgentState.IDLE,
                    'LISTENING': AgentState.LISTENING,
                    'REASONING': AgentState.REASONING,
                    'LEARNING': AgentState.LEARNING,
                    'EXECUTING': AgentState.EXECUTING,
                }
                self.state_manager.transition_to(state_map.get(new_state, new_state))
            except Exception as e:
                logger.warning(f"[ORCHESTRATOR] Failed to transition state via manager: {e}")
    
    def _execute_listening(self, user_input: str):
        """
        Execute LISTENING phase.
        
        Validates input and prepares for reasoning.
        
        Args:
            user_input: User's input
        """
        logger.info("[ORCHESTRATOR] Listening phase: Parsing input")
        
        # Basic validation
        if not user_input or not user_input.strip():
            raise ValueError("Empty input received")
        
        logger.debug(f"[ORCHESTRATOR] Input validated: {len(user_input)} chars")
    
    def _execute_reasoning(self, user_input: str) -> str:
        """
        Execute REASONING phase.
        
        Generates response using LLM reasoning engine with memory context.
        
        Args:
            user_input: User's input
        
        Returns:
            Generated response
        """
        logger.info("[ORCHESTRATOR] Reasoning phase: Generating response")
        
        try:
            # Retrieve relevant memories
            logger.debug("[ORCHESTRATOR] Retrieving relevant memories")
            memories = self._get_relevant_memories(user_input)
            
            # Build context
            context = self._build_reasoning_context(user_input, memories)
            
            # Call reasoning engine
            logger.debug("[ORCHESTRATOR] Calling reasoning engine")
            raw_response = self.reasoning_engine.reason(user_input, context)
            
            # CRITICAL FIX: Properly extract and validate response
            response_text = self._extract_and_validate_response(raw_response)
            
            logger.debug(f"[ORCHESTRATOR] Generated response: {response_text[:100]}...")
            
            return response_text
        
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Reasoning failed: {type(e).__name__}: {str(e)}", exc_info=True)
            raise
    
    def _extract_and_validate_response(self, raw_response) -> str:
        """
        Extract and validate response from reasoning engine.
        
        Handles multiple response formats and ensures clean output.
        
        Args:
            raw_response: Raw response from reasoning engine
        
        Returns:
            Clean, validated response text
        """
        # Handle different response types
        if isinstance(raw_response, str):
            response_text = raw_response
        
        elif isinstance(raw_response, dict):
            # Try common response keys
            response_text = raw_response.get('response', '')
            if not response_text:
                response_text = raw_response.get('text', '')
            if not response_text:
                response_text = raw_response.get('content', '')
            if not response_text:
                # Last resort: convert to string
                response_text = str(raw_response)
        
        elif hasattr(raw_response, '__iter__') and not isinstance(raw_response, str):
            # Might be a generator that wasn't consumed
            logger.warning("[ORCHESTRATOR] Response appears to be unconsumed iterator")
            try:
                # Try to consume it
                parts = []
                for chunk in raw_response:
                    if isinstance(chunk, str):
                        parts.append(chunk)
                    elif isinstance(chunk, dict):
                        parts.append(chunk.get('response', ''))
                response_text = ''.join(parts)
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] Failed to consume iterator: {e}")
                response_text = str(raw_response)
        
        else:
            logger.warning(f"[ORCHESTRATOR] Unexpected response type: {type(raw_response)}")
            response_text = str(raw_response)
        
        # Clean up the response
        response_text = response_text.strip()
        
        # Remove common markers/artifacts
        markers_to_remove = [
            '[JARVIIS]',
            '<response>',
            '</response>',
            '[RESPONSE]',
            '[/RESPONSE]',
            '```',
        ]
        
        for marker in markers_to_remove:
            if marker in response_text:
                # Take the part before the marker
                parts = response_text.split(marker)
                response_text = parts[0].strip()
        
        # Validate we got actual content
        if not response_text or len(response_text) < 2:
            logger.error(f"[ORCHESTRATOR] Response too short or empty: '{response_text}'")
            raise ValueError("Generated response is empty or too short")
        
        # Check for error messages in response
        error_indicators = [
            'governance backend unavailable',
            'governance error',
            'failed to generate',
        ]
        
        response_lower = response_text.lower()
        for indicator in error_indicators:
            if indicator in response_lower:
                logger.error(f"[ORCHESTRATOR] Error indicator in response: '{indicator}'")
                # We skip raising if its just historical context, but here it's the ACTUAL response
                raise RuntimeError(f"Response contains error: {indicator}")
        
        return response_text
    
    def _get_relevant_memories(self, user_input: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for context.
        
        Args:
            user_input: User's input
            limit: Maximum memories to retrieve
        
        Returns:
            List of relevant memory items
        """
        try:
            if self.memory_router:
                # Adapt based on MemoryRouter interface
                if hasattr(self.memory_router, 'retrieve_relevant_memories'):
                    memories = self.memory_router.retrieve_relevant_memories(
                        query=user_input,
                        limit=limit
                    )
                else:
                    # Fallback to existing JARVIIS interface
                    memories = self.memory_router.retrieve(user_input, limit=limit)
                
                logger.debug(f"[ORCHESTRATOR] Retrieved {len(memories)} memories")
                return memories
            else:
                logger.debug("[ORCHESTRATOR] No memory router available")
                return []
        
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Memory retrieval failed: {e}")
            return []
    
    def _build_reasoning_context(
        self,
        user_input: str,
        memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build context for reasoning engine.
        
        Args:
            user_input: User's input
            memories: Retrieved memories
        
        Returns:
            Context dictionary
        """
        context = {
            'user_input': user_input,
            'memories': memories,
            'timestamp': datetime.now().isoformat(),
            'request_id': self.request_count,
        }
        
        # Add current state
        if self.state_manager:
            context['current_state'] = getattr(self.state_manager, 'current_state', 'unknown')
        
        # Add available tools
        if self.tool_manager:
            context['available_tools'] = self.tool_manager.list_available_tools()
        
        return context
    
    def _execute_learning(self, user_input: str, response: str):
        """
        Execute LEARNING phase.
        
        Extracts knowledge from interaction and stores in memory.
        
        Args:
            user_input: User's input
            response: Assistant's response
        """
        logger.info("[ORCHESTRATOR] Learning phase: Storing interaction")
        
        try:
            # Store interaction in memory
            if self.memory_router:
                interaction_data = {
                    'user_input': user_input,
                    'system_response': response,
                    'timestamp': datetime.now().isoformat(),
                    'request_id': self.request_count,
                }
                
                if hasattr(self.memory_router, 'store_interaction'):
                    memory_id = self.memory_router.store_interaction(interaction_data)
                else:
                    memory_id = self.memory_router.store_conversation_turn(user_input, response)
                logger.debug(f"[ORCHESTRATOR] Stored interaction with ID: {memory_id}")
            
            # Extract facts if learning manager available
            if self.learning_manager:
                if hasattr(self.learning_manager, 'extract_and_store_facts'):
                    self.learning_manager.extract_and_store_facts(user_input, response)
                else:
                    self.learning_manager.learn(user_input, response)
        
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Learning failed: {e}", exc_info=True)
            # Don't fail the request if learning fails
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get orchestrator statistics.
        
        Returns:
            Statistics dictionary
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        stats = {
            'request_count': self.request_count,
            'uptime_seconds': uptime,
            'current_state': getattr(self.state_manager, 'current_state', 'unknown') if self.state_manager else 'unknown',
        }
        
        # Add memory stats if available
        if self.memory_router:
            try:
                if hasattr(self.memory_router, 'get_memory_count'):
                    stats['memory_count'] = self.memory_router.get_memory_count()
                else:
                    stats['memory_count'] = self.memory_router.get_stats().get('active_memories', 0)
            except:
                pass
        
        # Add resource stats if available
        if self.resource_monitor:
            try:
                stats['resources'] = self.resource_monitor.get_current_stats()
            except:
                pass
        
        return stats
