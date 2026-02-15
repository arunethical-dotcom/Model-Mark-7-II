"""
Routing Signals Module

Defines data structures for routing decisions, signals, and evaluation results.
These are the "lingua franca" between routing layers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class RoutingSignal(Enum):
    """Enumeration of routing decision signals."""

    # Explicit hints
    EXPLICIT_HINT_HERMES = "explicit_hint_hermes"
    EXPLICIT_HINT_MISTRAL = "explicit_hint_mistral"

    # Task classification
    REASONING_HEAVY = "reasoning_heavy"
    PLANNING = "planning"
    EXPLANATION = "explanation"
    CONVERSATIONAL = "conversational"
    CODING = "coding"
    TOOL_ORIENTED = "tool_oriented"

    # Complexity indicators
    COMPLEX_LOGIC = "complex_logic"
    MULTI_STEP = "multi_step"
    CONSTRAINT_LOGIC = "constraint_logic"
    LONG_FORM = "long_form"

    # Fallback
    DEFAULT_MISTRAL = "default_mistral"


@dataclass
class RoutingSignalSet:
    """Collection of signals fired during heuristic evaluation."""

    signals: List[RoutingSignal] = field(default_factory=list)

    def add_signal(self, signal: RoutingSignal) -> None:
        """Add a signal to the set."""
        if signal not in self.signals:
            self.signals.append(signal)

    def has_signal(self, signal: RoutingSignal) -> bool:
        """Check if a signal is present."""
        return signal in self.signals

    def __len__(self) -> int:
        """Return number of signals."""
        return len(self.signals)

    def to_list(self) -> List[str]:
        """Convert signals to string representation."""
        return [s.value for s in self.signals]


@dataclass
class RoutingDecision:
    """Final routing decision output."""

    model: str  # "mistral" or "hermes"
    confidence: float  # 0.0 to 1.0
    source: str  # "heuristic" or "llm"
    reason: Optional[str] = None
    signals: Optional[List[str]] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def is_high_confidence(self, threshold: float = 0.70) -> bool:
        """Check if confidence meets threshold."""
        return self.confidence >= threshold

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model": self.model,
            "confidence": self.confidence,
            "source": self.source,
            "reason": self.reason,
            "signals": self.signals,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class HeuristicScores:
    """Scoring breakdown from heuristic router."""

    mistral_score: float = 0.0
    hermes_score: float = 0.0
    signals: RoutingSignalSet = field(default_factory=RoutingSignalSet)

    @property
    def total_mistral(self) -> float:
        """Get normalized mistral score."""
        return self.mistral_score

    @property
    def total_hermes(self) -> float:
        """Get normalized hermes score."""
        return self.hermes_score

    @property
    def max_score(self) -> float:
        """Get maximum score."""
        return max(self.mistral_score, self.hermes_score)

    @property
    def score_diff(self) -> float:
        """Get absolute difference between scores."""
        return abs(self.mistral_score - self.hermes_score)

    def normalize(self) -> Dict[str, float]:
        """Normalize scores to 0-1 range based on max."""
        total = max(self.max_score, 0.01)  # Avoid division by zero
        return {
            "mistral": self.mistral_score / total,
            "hermes": self.hermes_score / total,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "mistral_score": self.mistral_score,
            "hermes_score": self.hermes_score,
            "normalized": self.normalize(),
            "signals": self.signals.to_list(),
        }
