"""
Heuristic Scoring Engine

Implements rule-based, deterministic scoring for model selection.
All scores and weights are configurable and inspectable.
"""

import re
from typing import Dict, Tuple, Optional, List
from .routing_signals import RoutingSignal, RoutingSignalSet, HeuristicScores
from .config import ModelSelectorConfig


class HeuristicRouter:
    """Deterministic rule-based model router."""

    def __init__(self, config: Optional[ModelSelectorConfig] = None) -> None:
        """
        Initialize heuristic router.

        Args:
            config: ModelSelectorConfig instance (uses defaults if None)
        """
        self.config = config or ModelSelectorConfig()
        self.weights = self.config.heuristic_weights

    def evaluate(self, user_input: str) -> Tuple[HeuristicScores, Optional[RoutingSignal]]:
        """
        Evaluate input and produce routing scores.

        Args:
            user_input: The user's request text

        Returns:
            Tuple of (HeuristicScores, dominant RoutingSignal or None)
        """
        scores = HeuristicScores()

        # PHASE 1: Check for explicit model hints (highest priority)
        explicit_signal = self._check_explicit_hints(user_input)
        if explicit_signal:
            scores.signals.add_signal(explicit_signal)
            if explicit_signal == RoutingSignal.EXPLICIT_HINT_HERMES:
                scores.hermes_score += 10.0  # Override everything
                return scores, explicit_signal
            else:
                scores.mistral_score += 10.0  # Override everything
                return scores, explicit_signal

        # PHASE 2: Classify task type
        task_signals = self._classify_task(user_input)
        for signal in task_signals:
            scores.signals.add_signal(signal)
            self._apply_signal(scores, signal)

        # PHASE 3: Estimate complexity
        complexity_signals = self._estimate_complexity(user_input)
        for signal in complexity_signals:
            scores.signals.add_signal(signal)
            self._apply_signal(scores, signal)

        # PHASE 4: Apply domain-specific rules
        domain_signals = self._apply_domain_rules(user_input)
        for signal in domain_signals:
            scores.signals.add_signal(signal)
            self._apply_signal(scores, signal)

        return scores, None

    def _check_explicit_hints(self, user_input: str) -> Optional[RoutingSignal]:
        """
        Check for explicit model selection hints.

        Supports:
        - @hermes (at start or with space)
        - @mistral (at start or with space)

        Args:
            user_input: User input text

        Returns:
            RoutingSignal if explicit hint found, None otherwise
        """
        lowered = user_input.lower().strip()

        # Check for @hermes
        if lowered.startswith("@hermes") or " @hermes" in lowered:
            return RoutingSignal.EXPLICIT_HINT_HERMES

        # Check for @mistral
        if lowered.startswith("@mistral") or " @mistral" in lowered:
            return RoutingSignal.EXPLICIT_HINT_MISTRAL

        return None

    def _classify_task(self, user_input: str) -> List[RoutingSignal]:
        """
        Classify the task type from user input.

        Returns list of signals based on input characteristics.

        Args:
            user_input: User input text

        Returns:
            List of RoutingSignals
        """
        signals: List[RoutingSignal] = []
        lowered = user_input.lower()

        # Reasoning heavy keywords
        reasoning_keywords = [
            "why",
            "explain",
            "reason",
            "logic",
            "analyze",
            "think through",
            "figure out",
            "solve",
            "proof",
            "deduce",
            "validate",
        ]
        if any(kw in lowered for kw in reasoning_keywords):
            signals.append(RoutingSignal.REASONING_HEAVY)

        # Planning keywords
        planning_keywords = [
            "plan",
            "steps",
            "procedure",
            "how to",
            "strategy",
            "approach",
            "sequence",
            "order",
            "organize",
        ]
        if any(kw in lowered for kw in planning_keywords):
            signals.append(RoutingSignal.PLANNING)

        # Explanation keywords
        explanation_keywords = [
            "explain",
            "describe",
            "what is",
            "definition",
            "concept",
            "tell me about",
            "summarize",
        ]
        if any(kw in lowered for kw in explanation_keywords):
            signals.append(RoutingSignal.EXPLANATION)

        # Coding keywords
        coding_keywords = [
            "code",
            "program",
            "function",
            "class",
            "implement",
            "debug",
            "error",
            "syntax",
            "python",
            "javascript",
            "java",
        ]
        if any(kw in lowered for kw in coding_keywords):
            signals.append(RoutingSignal.CODING)

        # Conversational (absence of specific task indicators)
        if not signals:
            signals.append(RoutingSignal.CONVERSATIONAL)

        return signals

    def _estimate_complexity(self, user_input: str) -> List[RoutingSignal]:
        """
        Estimate complexity of the request.

        Args:
            user_input: User input text

        Returns:
            List of complexity-related RoutingSignals
        """
        signals: List[RoutingSignal] = []

        # Multi-step detection (heuristic: numbered lists or "then" sequences)
        if re.search(r"\d+\.", user_input) or user_input.lower().count(" then ") > 1:
            signals.append(RoutingSignal.MULTI_STEP)

        # Constraint logic (keywords suggesting logical relationships)
        constraint_keywords = [
            "if",
            "unless",
            "constraint",
            "condition",
            "must",
            "required",
            "forbidden",
            "only if",
        ]
        if any(kw in user_input.lower() for kw in constraint_keywords):
            signals.append(RoutingSignal.CONSTRAINT_LOGIC)

        # Complex logic (conjunction of conditions)
        if user_input.lower().count(" and ") > 2:
            signals.append(RoutingSignal.COMPLEX_LOGIC)

        # Long-form (heuristic: >200 tokens)
        token_estimate = len(user_input.split())
        if token_estimate > 200:
            signals.append(RoutingSignal.LONG_FORM)

        return signals

    def _apply_domain_rules(self, user_input: str) -> List[RoutingSignal]:
        """
        Apply domain-specific routing rules.

        Args:
            user_input: User input text

        Returns:
            List of domain-specific RoutingSignals
        """
        signals: List[RoutingSignal] = []

        # Mathematics/logic domain rules
        math_indicators = ["equation", "formula", "calculate", "proof", "theorem"]
        if any(ind in user_input.lower() for ind in math_indicators):
            signals.append(RoutingSignal.COMPLEX_LOGIC)

        # Tool-oriented tasks
        tool_keywords = ["search", "fetch", "retrieve", "find", "lookup"]
        if any(kw in user_input.lower() for kw in tool_keywords):
            signals.append(RoutingSignal.TOOL_ORIENTED)

        return signals

    def _apply_signal(self, scores: HeuristicScores, signal: RoutingSignal) -> None:
        """
        Apply signal-based score adjustments.

        Args:
            scores: HeuristicScores to modify
            signal: RoutingSignal to process
        """
        weight = self.weights.get(signal.value, 0.0)

        if signal in [
            RoutingSignal.REASONING_HEAVY,
            RoutingSignal.PLANNING,
            RoutingSignal.CONSTRAINT_LOGIC,
            RoutingSignal.COMPLEX_LOGIC,
            RoutingSignal.MULTI_STEP,
        ]:
            # Heavy reasoning tasks favor Hermes
            scores.hermes_score += weight

        elif signal in [
            RoutingSignal.EXPLANATION,
            RoutingSignal.CONVERSATIONAL,
            RoutingSignal.TOOL_ORIENTED,
        ]:
            # Direct/simple tasks favor Mistral
            scores.mistral_score += weight

        elif signal == RoutingSignal.CODING:
            # Coding is balanced (both models capable)
            scores.hermes_score += weight * 0.7
            scores.mistral_score += weight * 0.3

        elif signal == RoutingSignal.LONG_FORM:
            # Long form prefers Hermes for depth
            scores.hermes_score += weight

    def score_to_confidence(self, scores: HeuristicScores) -> float:
        """
        Convert raw scores to confidence metric (0.0 to 1.0).

        Args:
            scores: HeuristicScores from evaluation

        Returns:
            Confidence float between 0.0 and 1.0
        """
        if scores.max_score == 0:
            # No signals fired - use default with low confidence
            return 0.3

        # Normalized score difference
        max_score = scores.max_score
        score_diff = scores.score_diff
        normalized_diff = min(score_diff / max_score, 1.0)

        # Signal strength (more signals = higher confidence)
        signal_count = len(scores.signals)
        signal_confidence = min(signal_count / 4.0, 1.0)

        # Combined confidence (weighted average)
        # 60% from score difference, 40% from signal strength
        confidence = (normalized_diff * 0.6) + (signal_confidence * 0.4)

        return min(max(confidence, 0.0), 1.0)

    def get_winner(self, scores: HeuristicScores) -> str:
        """
        Determine winning model from scores.

        Args:
            scores: HeuristicScores

        Returns:
            "mistral" or "hermes"
        """
        if scores.hermes_score > scores.mistral_score:
            return "hermes"
        else:
            return "mistral"
