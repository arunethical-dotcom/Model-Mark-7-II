"""
Hybrid Model Selector

Main orchestrator for layered model selection:
1. Heuristic routing (fast, deterministic)
2. Confidence escalation gate
3. LLM meta-routing fallback (semantic)
4. Output validation and fallback
"""

from typing import Optional, Dict, Any, List
from .scoring_engine import HeuristicRouter
from .llm_router import LLMRouter
from .routing_signals import RoutingDecision, RoutingSignal, HeuristicScores
from .config import ModelSelectorConfig
from .model_selector import ModelSelectorInterface


class HybridModelSelector(ModelSelectorInterface):
    """
    Layered hybrid model selector.

    LAYER 1: Heuristic (deterministic, fast)
    LAYER 2: Confidence escalation gate
    LAYER 3: LLM meta-router (semantic fallback)
    LAYER 4: Validation and fallback handling
    """

    def __init__(
        self,
        heuristic_router: Optional[HeuristicRouter] = None,
        llm_router: Optional[LLMRouter] = None,
        config: Optional[ModelSelectorConfig] = None,
    ) -> None:
        """
        Initialize hybrid selector.

        Args:
            heuristic_router: HeuristicRouter instance (created if None)
            llm_router: LLMRouter instance (optional, required for LLM routing)
            config: ModelSelectorConfig
        """
        self.config = config or ModelSelectorConfig()
        self.heuristic_router = heuristic_router or HeuristicRouter(self.config)
        self.llm_router = llm_router
        self.selection_history: List[Dict[str, Any]] = []

    def select_model(self, user_input: str) -> RoutingDecision:
        """
        Select optimal model for user input.

        Implements full layered routing pipeline:
        1. Heuristic evaluation
        2. Confidence check
        3. LLM escalation if needed
        4. Validation and fallback

        Args:
            user_input: User request text

        Returns:
            RoutingDecision with selected model and confidence
        """
        # LAYER 1: Heuristic routing (always runs first)
        scores, explicit_signal = self.heuristic_router.evaluate(user_input)
        confidence = self.heuristic_router.score_to_confidence(scores)
        winner = self.heuristic_router.get_winner(scores)

        heuristic_decision = RoutingDecision(
            model=winner,
            confidence=confidence,
            source="heuristic",
            signals=scores.signals.to_list(),
        )

        # Early exit if heuristic has explicit hint (highest priority)
        if explicit_signal is not None:
            self.selection_history.append(heuristic_decision.to_dict())
            return heuristic_decision

        # LAYER 2: Confidence escalation gate
        if confidence >= self.config.confidence_threshold:
            # High confidence - use heuristic result
            self.selection_history.append(heuristic_decision.to_dict())
            return heuristic_decision

        # LAYER 3: LLM meta-routing fallback
        if not self.config.enable_llm_routing or self.llm_router is None:
            # LLM routing disabled - return heuristic with low confidence
            self.selection_history.append(heuristic_decision.to_dict())
            return heuristic_decision

        # Route to LLM meta-reasoner
        llm_decision, llm_success = self.llm_router.route(
            user_input, heuristic_decision
        )
        self.llm_router.reset_execution_count()

        if llm_success:
            # LLM routing succeeded
            self.selection_history.append(llm_decision.to_dict())
            return llm_decision
        else:
            # LLM routing failed, use heuristic fallback
            self.selection_history.append(heuristic_decision.to_dict())
            return heuristic_decision

    def get_detailed_routing_info(self, user_input: str) -> Dict[str, Any]:
        """
        Get detailed routing information for debugging.

        Args:
            user_input: User request text

        Returns:
            Dictionary with routing details
        """
        # Get heuristic scores
        scores, explicit_signal = self.heuristic_router.evaluate(user_input)
        confidence = self.heuristic_router.score_to_confidence(scores)

        info: Dict[str, Any] = {
            "user_input": user_input[:100],  # Truncate for readability
            "heuristic_scores": scores.to_dict(),
            "confidence": confidence,
            "threshold": self.config.confidence_threshold,
            "meets_threshold": confidence >= self.config.confidence_threshold,
            "signals": scores.signals.to_list(),
        }

        # Add LLM routing info if enabled
        if self.config.enable_llm_routing and self.llm_router is not None:
            heuristic_decision = RoutingDecision(
                model=self.heuristic_router.get_winner(scores),
                confidence=confidence,
                source="heuristic",
                signals=scores.signals.to_list(),
            )

            llm_decision, llm_success = self.llm_router.route(
                user_input, heuristic_decision
            )
            self.llm_router.reset_execution_count()

            info["llm_routing"] = {
                "enabled": True,
                "attempted": confidence < self.config.confidence_threshold,
                "success": llm_success,
                "decision": llm_decision.to_dict() if llm_success else None,
            }

        return info

    def get_selection_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all model selections.

        Returns:
            List of routing decisions
        """
        return self.selection_history.copy()

    def clear_history(self) -> None:
        """Clear selection history."""
        self.selection_history = []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about model selections.

        Returns:
            Dictionary with routing statistics
        """
        if not self.selection_history:
            return {"total_selections": 0}

        mistral_count = sum(
            1 for d in self.selection_history if d["model"] == "mistral"
        )
        hermes_count = sum(
            1 for d in self.selection_history if d["model"] == "hermes"
        )
        heuristic_count = sum(
            1 for d in self.selection_history if d["source"] == "heuristic"
        )
        llm_count = sum(1 for d in self.selection_history if d["source"] == "llm")

        avg_confidence = sum(d["confidence"] for d in self.selection_history) / len(
            self.selection_history
        )

        return {
            "total_selections": len(self.selection_history),
            "mistral_selected": mistral_count,
            "hermes_selected": hermes_count,
            "heuristic_routed": heuristic_count,
            "llm_routed": llm_count,
            "average_confidence": avg_confidence,
            "mistral_percentage": mistral_count / len(self.selection_history),
            "hermes_percentage": hermes_count / len(self.selection_history),
        }
