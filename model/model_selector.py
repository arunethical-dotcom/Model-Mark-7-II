"""
Model Selector Interface

Abstract interface for model selection to maintain dependency inversion.
Orchestrator depends only on this interface, not concrete implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .routing_signals import RoutingDecision


class ModelSelectorInterface(ABC):
    """
    Abstract interface for model selection.

    Orchestrator depends on this interface to remain agnostic to
    routing implementation details.
    """

    @abstractmethod
    def select_model(self, user_input: str) -> RoutingDecision:
        """
        Select optimal model for user input.

        Args:
            user_input: User request text

        Returns:
            RoutingDecision with selected model, confidence, and metadata
        """
        pass

    @abstractmethod
    def get_selection_history(self) -> List[Dict[str, Any]]:
        """
        Get history of model selections.

        Returns:
            List of RoutingDecision dictionaries
        """
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get routing statistics.

        Returns:
            Dictionary with selection statistics
        """
        pass

    @abstractmethod
    def clear_history(self) -> None:
        """Clear selection history."""
        pass
