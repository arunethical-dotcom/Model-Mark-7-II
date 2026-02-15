"""
Model Selection Configuration

Centralized configuration for routing thresholds, weights, and parameters.
Allows tuning without modifying core routing logic.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ModelSelectorConfig:
    """Configuration for hybrid model selector system."""

    # Confidence escalation threshold
    # If heuristic confidence < this, route to LLM meta-router
    confidence_threshold: float = 0.70

    # Heuristic routing weights
    heuristic_weights: Dict[str, float] = field(default_factory=dict)

    # LLM router model name (always use lightweight model for routing)
    router_model_name: str = "smollm2"

    # Target model names
    available_models: Dict[str, str] = field(default_factory=dict)

    # Enable LLM routing (can be disabled for testing)
    enable_llm_routing: bool = True

    # Maximum retries for invalid LLM output
    llm_output_retries: int = 2

    # Cache routing decisions for identical inputs (optional optimization)
    enable_routing_cache: bool = False

    def __post_init__(self) -> None:
        """Initialize default weights if not provided."""
        if not self.heuristic_weights:
            self.heuristic_weights = {
                "explicit_hint": 1.0,
                "reasoning_heavy": 0.8,
                "planning": 0.7,
                "explanation": 0.6,
                "complexity_high": 0.5,
                "multi_step": 0.6,
                "constraint_logic": 0.7,
                "conversational": 0.3,
                "coding": 0.5,
                "tool_oriented": 0.4,
                "long_form": 0.6,
            }

        if not self.available_models:
            self.available_models = {
                "mistral": "hermes-mistral",
                "hermes": "hermes-mistral",
                "smollm2": "smollm2",     # SmolLM2-1.7B for governance/routing
            }

    def get_weight(self, signal_name: str, default: float = 0.0) -> float:
        """
        Get weight for a signal.

        Args:
            signal_name: Name of signal
            default: Default weight if not found

        Returns:
            Weight value
        """
        return self.heuristic_weights.get(signal_name, default)


# Global default configuration
DEFAULT_CONFIG = ModelSelectorConfig()
