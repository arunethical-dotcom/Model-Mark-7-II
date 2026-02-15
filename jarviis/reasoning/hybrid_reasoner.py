"""
Hybrid Reasoner
Integration adapter connecting Hybrid Model Selection subsystem to JARVIIS core.
"""

from typing import Dict, Any
from core.interfaces import ReasoningInterface
from model.hybrid_model_selector import HybridModelSelector
from model.model_runtime_manager import ModelRuntimeManager
from model.base_model_adapter import MistralAdapter, HermesAdapter

# Import governed backend
import sys
from pathlib import Path
governance_path = Path(__file__).parent.parent.parent / "governance"
sys.path.insert(0, str(governance_path))

try:
    from .governed_llm_backend import GovernedLLMBackend
    GOVERNANCE_AVAILABLE = True
except ImportError as e:
    print(f"[HYBRID] Governance import failed: {e}")
    GOVERNANCE_AVAILABLE = False


class HybridReasoner(ReasoningInterface):
    """
    Reasoning engine powered by Hybrid Model Selection subsystem.
    
    Integrates:
    - HybridModelSelector for intelligent model routing
    - ModelRuntimeManager for lifecycle management
    - MistralAdapter and HermesAdapter for model execution
    - GovernedLLMBackend for identity anchoring and validation
    """

    def __init__(self, use_governance: bool = True):
        """
        Initialize hybrid reasoner with model selection subsystem.
        
        Args:
            use_governance: Enable governance layer (default: True)
        """
        self.model_selector = HybridModelSelector()
        self.runtime_manager = ModelRuntimeManager()
        self.use_governance = use_governance and GOVERNANCE_AVAILABLE
        
        # Initialize governed backend if available
        self.governed_backend = None
        if self.use_governance:
            try:
                self.governed_backend = GovernedLLMBackend(
                    backend_type="ollama",
                    verbose=False
                )
            except Exception as e:
                print(f"[HYBRID] Governance init failed: {e}")
                self.use_governance = False
        
        # Register models (with governance integration)
        mistral = MistralAdapter()
        hermes = HermesAdapter()
        
        # Pass governed backend to adapters
        if self.governed_backend:
            mistral.set_governed_backend(self.governed_backend)
            hermes.set_governed_backend(self.governed_backend)
        
        self.runtime_manager.register_model("mistral", mistral)
        self.runtime_manager.register_model("hermes", hermes)

    def reason(self, context: Dict[str, Any]) -> str:
        """
        Generate reasoned response using hybrid model selection.
        
        Args:
            context: Dictionary containing 'user_input' and optional metadata
            
        Returns:
            Generated response string
        """
        user_input = context.get('user_input', '')
        
        # Select optimal model
        decision = self.model_selector.select_model(user_input)
        
        # Load selected model
        adapter = self.runtime_manager.load_model(decision.model)
        
        # Generate response (adapter uses governed backend if available)
        response = adapter.generate(user_input)
        
        return response

    def is_available(self) -> bool:
        """
        Check if reasoning engine is ready.
        
        Returns:
            True if engine is available
        """
        return True

