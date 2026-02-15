"""
Hybrid Autonomous Model Selection Subsystem for JARVIIS Core

A production-ready model selection layer that intelligently routes requests
between multiple LLM models using a hybrid approach combining:
- Fast deterministic heuristics (Layer 1)
- Configurable confidence escalation (Layer 2)
- LLM meta-router fallback (Layer 3)
- Robust validation and fallback (Layer 4)

Version: 1.0.0
Status: Production Ready
Python: 3.10+
Dependencies: None (pure Python)
"""

from .config import ModelSelectorConfig, DEFAULT_CONFIG
from .routing_signals import (
    RoutingSignal,
    RoutingSignalSet,
    HeuristicScores,
    RoutingDecision,
)
from .scoring_engine import HeuristicRouter
from .llm_router import LLMRouter
from .model_runtime_manager import ModelRuntimeManager
from .base_model_adapter import (
    BaseModelAdapter,
    MistralAdapter,
    HermesAdapter,
    MockModelAdapter,
)
from .model_selector import ModelSelectorInterface
from .hybrid_model_selector import HybridModelSelector

__version__ = "1.0.0"
__all__ = [
    "ModelSelectorConfig",
    "DEFAULT_CONFIG",
    "RoutingSignal",
    "RoutingSignalSet",
    "HeuristicScores",
    "RoutingDecision",
    "HeuristicRouter",
    "LLMRouter",
    "ModelRuntimeManager",
    "BaseModelAdapter",
    "MistralAdapter",
    "HermesAdapter",
    "MockModelAdapter",
    "ModelSelectorInterface",
    "HybridModelSelector",
]
