"""
Governed LLM Backend - Wrapper that applies Cognitive Governance to LLM responses.

This module integrates the Cognitive Governance layer with the standard LLM backend,
ensuring all responses pass through identity validation and safety checks.

FIXED: Properly handles streaming response collection from Ollama
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add governance folder to path if needed
governance_path = Path(__file__).resolve().parent.parent.parent / "governance"
if str(governance_path) not in sys.path:
    sys.path.insert(0, str(governance_path))

# Import the governance orchestrator
try:
    from cognitive_core import CognitiveOrchestrator
    from llm_backends import OllamaBackend as GovOllamaBackend
    GOVERNANCE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"[GOVERNED] Governance layer not available: {e}")
    GOVERNANCE_AVAILABLE = False

logger = logging.getLogger(__name__)


class GovernedLLMBackend:
    """
    LLM Backend with Cognitive Governance integration.
    
    This class wraps standard LLM calls with the governance layer,
    ensuring responses align with JARVIIS identity and safety guidelines.
    """
    
    def __init__(
        self,
        backend_type: str = "ollama",
        base_url: str = "http://localhost:11434",
        model_name: str = "hermes-mistral",
        enable_governance: bool = True,
        verbose: bool = False
    ):
        """
        Initialize governed LLM backend.

        Args:
            backend_type: Type of backend ("ollama" or "mock")
            base_url: Ollama server base URL
            model_name: Model to use for generation
            enable_governance: Whether to enable governance layer
            verbose: Enable verbose logging
        """
        self.backend_type = backend_type
        self.base_url = base_url
        self.model_name = model_name
        self.enable_governance = enable_governance and GOVERNANCE_AVAILABLE
        self.verbose = verbose
        
        logger.info(f"[GOVERNED] Initializing GovernedLLMBackend")
        
        # Initialize governance orchestrator if available
        if self.enable_governance:
            try:
                # Create main reasoning backend
                self.reasoning_llm = GovOllamaBackend(
                    host=base_url,
                    model=model_name
                )
                
                # Create orchestrator
                self.orchestrator = CognitiveOrchestrator(
                    reasoning_backend=self.reasoning_llm
                )
                
                logger.info("[GOVERNED] ✅ Governance layer active")
                
            except Exception as e:
                logger.error(f"[GOVERNED] Failed to initialize governance: {e}", exc_info=True)
                self.enable_governance = False
                logger.warning("[GOVERNED] ⚠️ Falling back to direct backend")
        
        # Fallback: direct backend without governance
        if not self.enable_governance:
            try:
                from llm_backends import OllamaBackend as StandardBackend
                self.direct_backend = StandardBackend(
                    model=model_name,
                    host=base_url
                )
                logger.info("[GOVERNED] Using direct backend (no governance)")
            except Exception as e:
                logger.error(f"[GOVERNED] Failed to initialize direct backend: {e}")
                # We can't actually do much without a backend... 
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate response with optional governance oversight.
        """
        # Capture model override if present
        model_override = kwargs.get('model')
        
        try:
            # Add parameters the orchestrator/backend expects
            memory_snippets = kwargs.get('memory_snippets', [])
            conversation_history = kwargs.get('conversation_history', [])
            
            # Use governance if enabled
            if self.enable_governance:
                response = self.orchestrator.run(
                    user_input=prompt,
                    memory_snippets=memory_snippets,
                    conversation_history=conversation_history,
                    reasoning_backend=self.reasoning_llm,
                    model=model_override  # Pass specific model to orchestrator
                )
            else:
                # Direct call to standard backend
                response = self.direct_backend(
                    messages=[{"role": "user", "content": prompt}],
                    stream=kwargs.get('stream', False)
                )
            
            return response
        
        except Exception as e:
            logger.error(f"[GOVERNED] Generation failed: {e}", exc_info=True)
            return f"I encountered an error: {str(e)}"
    
    def health_check(self) -> bool:
        """Check if backend is available."""
        if self.enable_governance:
            return self.reasoning_llm.health_check()
        return self.direct_backend.health_check()
    
    def get_stats(self) -> dict:
        """Get governance statistics."""
        if self.enable_governance:
             return self.orchestrator.last_stats()
        return {}
