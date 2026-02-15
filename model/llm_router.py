"""
LLM Meta-Router

Uses Mistral as a semantic routing model when heuristic confidence is low.
Handles JSON parsing and fallback validation.
"""

import json
from typing import Optional, Tuple, Dict, Any
from .base_model_adapter import BaseModelAdapter
from .routing_signals import RoutingDecision
from .config import ModelSelectorConfig


class LLMRouter:
    """
    LLM-based meta-reasoning router.

    Uses Mistral to evaluate ambiguous routing decisions
    when heuristic confidence is too low.
    """

    ROUTING_PROMPT_TEMPLATE = """You are a model selection router for an agentic AI system.

Your task is to select the OPTIMAL model for the given user request.

Available models:

Model A - Hermes (Hermes-2-Pro-Mistral-7B):
Strengths: Deep reasoning, multi-step planning, complex logical analysis, constraint solving
Use for: Tasks requiring extensive thinking, planning, detailed explanations, logical proofs

Model B - Mistral (mistral-7b-instruct-v0.1):
Strengths: Fast inference, direct instruction following, conversational fluency, quick answers
Use for: Direct questions, conversational tasks, quick lookups, simple instructions

User Request:
{user_input}

Respond ONLY with a valid JSON object, no other text:
{{
  "model": "hermes" or "mistral",
  "confidence": <float between 0.0 and 1.0>,
  "reason": "<brief explanation of why this model was chosen>"
}}

Confidence: 0.0-0.5 means uncertain, 0.5-0.8 means moderately confident, 0.8-1.0 means very confident."""

    def __init__(
        self,
        router_model: BaseModelAdapter,
        config: Optional[ModelSelectorConfig] = None,
    ) -> None:
        """
        Initialize LLM router.

        Args:
            router_model: Mistral adapter instance (must be pre-loaded)
            config: ModelSelectorConfig
        """
        self.router_model = router_model
        self.config = config or ModelSelectorConfig()
        self.execution_count = 0

    def route(
        self, user_input: str, heuristic_fallback: RoutingDecision
    ) -> Tuple[RoutingDecision, bool]:
        """
        Route using LLM meta-reasoning with fallback.

        Args:
            user_input: The user's request
            heuristic_fallback: Fallback decision if LLM routing fails

        Returns:
            Tuple of (RoutingDecision, success_flag)
            If success_flag is False, returned decision is the fallback
        """
        self.execution_count += 1

        # Prevent recursive routing (execute at most once per request)
        if self.execution_count > 1:
            return heuristic_fallback, False

        try:
            # Generate routing decision from LLM
            raw_response = self._generate_routing_decision(user_input)

            # Parse and validate JSON
            decision = self._parse_routing_response(raw_response)

            if decision is not None:
                return decision, True
            else:
                # Parsing failed, use fallback
                return heuristic_fallback, False

        except Exception as e:
            # Any error falls back to heuristic
            print(f"LLM routing error: {e}")
            return heuristic_fallback, False

    def _generate_routing_decision(self, user_input: str) -> str:
        """
        Generate raw LLM routing response.

        Args:
            user_input: User request text

        Returns:
            Raw text response from router model

        Raises:
            RuntimeError: If router model not available
        """
        if not self.router_model.is_available():
            raise RuntimeError("Router model not loaded")

        prompt = self.ROUTING_PROMPT_TEMPLATE.format(user_input=user_input)
        response = self.router_model.generate(prompt)

        return response

    def _parse_routing_response(self, raw_response: str) -> Optional[RoutingDecision]:
        """
        Parse and validate LLM routing response.

        Args:
            raw_response: Raw text from router model

        Returns:
            RoutingDecision if valid, None otherwise
        """
        try:
            # Try direct JSON parse first
            data = json.loads(raw_response)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            data = self._extract_json_from_text(raw_response)

            if data is None:
                return None

        # Validate required fields
        if not isinstance(data, dict):
            return None

        model = data.get("model", "").lower()
        confidence = data.get("confidence")
        reason = data.get("reason", "")

        # Validate model selection
        if model not in ["mistral", "hermes"]:
            return None

        # Validate confidence
        if not isinstance(confidence, (int, float)):
            return None
        confidence = float(confidence)
        if not (0.0 <= confidence <= 1.0):
            return None

        return RoutingDecision(
            model=model,
            confidence=confidence,
            source="llm",
            reason=reason,
            signals=["llm_routing"],
        )

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to extract JSON object from text.

        Args:
            text: Text potentially containing JSON

        Returns:
            Parsed JSON dict or None
        """
        # Find first { and last }
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or start >= end:
            return None

        try:
            json_str = text[start : end + 1]
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def reset_execution_count(self) -> None:
        """Reset execution counter for next request."""
        self.execution_count = 0
