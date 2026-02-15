"""
Test Suite for Hybrid Model Selection System

Tests:
- Heuristic routing accuracy
- Explicit hint detection
- Confidence threshold escalation
- LLM fallback behavior
- Runtime manager load/unload
- Adapter interface compliance
- Invalid output handling
- Integration scenarios
"""

import unittest
from typing import Optional

from config import ModelSelectorConfig
from scoring_engine import HeuristicRouter
from routing_signals import RoutingSignal, RoutingDecision
from base_model_adapter import (
    BaseModelAdapter,
    MistralAdapter,
    HermesAdapter,
    MockModelAdapter,
)
from model_runtime_manager import ModelRuntimeManager
from llm_router import LLMRouter
from hybrid_model_selector import HybridModelSelector
from model_selector import ModelSelectorInterface


class TestHeuristicRouting(unittest.TestCase):
    """Test heuristic routing accuracy."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.router = HeuristicRouter()

    def test_explicit_hint_hermes(self) -> None:
        """Test explicit @hermes hint."""
        scores, signal = self.router.evaluate("@hermes solve this step by step")
        self.assertEqual(signal, RoutingSignal.EXPLICIT_HINT_HERMES)
        self.assertGreater(scores.hermes_score, scores.mistral_score)

    def test_explicit_hint_mistral(self) -> None:
        """Test explicit @mistral hint."""
        scores, signal = self.router.evaluate("@mistral quick answer needed")
        self.assertEqual(signal, RoutingSignal.EXPLICIT_HINT_MISTRAL)
        self.assertGreater(scores.mistral_score, scores.hermes_score)

    def test_reasoning_heavy_task(self) -> None:
        """Test detection of reasoning-heavy tasks."""
        text = "Explain the logical reasoning behind this complex problem"
        scores, _ = self.router.evaluate(text)
        self.assertGreater(scores.hermes_score, 0)
        self.assertIn(RoutingSignal.REASONING_HEAVY, scores.signals.signals)

    def test_planning_task(self) -> None:
        """Test detection of planning tasks."""
        text = "Create a step-by-step plan for implementing this feature"
        scores, _ = self.router.evaluate(text)
        self.assertGreater(scores.hermes_score, scores.mistral_score)
        self.assertIn(RoutingSignal.PLANNING, scores.signals.signals)

    def test_simple_conversational(self) -> None:
        """Test simple conversational queries prefer Mistral."""
        text = "Hello, how are you?"
        scores, _ = self.router.evaluate(text)
        self.assertIn(RoutingSignal.CONVERSATIONAL, scores.signals.signals)

    def test_multi_step_detection(self) -> None:
        """Test multi-step instruction detection."""
        text = "1. First do this. 2. Then do that. 3. Finally do this."
        scores, _ = self.router.evaluate(text)
        self.assertIn(RoutingSignal.MULTI_STEP, scores.signals.signals)

    def test_constraint_logic_detection(self) -> None:
        """Test constraint logic detection."""
        text = "If condition A and condition B unless condition C then do X"
        scores, _ = self.router.evaluate(text)
        self.assertIn(RoutingSignal.CONSTRAINT_LOGIC, scores.signals.signals)


class TestConfidenceScoring(unittest.TestCase):
    """Test confidence score calculation."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.router = HeuristicRouter()

    def test_high_confidence_explicit(self) -> None:
        """Test high confidence with explicit hint."""
        scores, _ = self.router.evaluate("@hermes reasoning task")
        confidence = self.router.score_to_confidence(scores)
        self.assertGreaterEqual(confidence, 0.9)

    def test_low_confidence_no_signals(self) -> None:
        """Test low confidence with no clear signals."""
        scores, _ = self.router.evaluate("xyz abc def")
        confidence = self.router.score_to_confidence(scores)
        self.assertLess(confidence, 0.5)

    def test_confidence_in_range(self) -> None:
        """Test confidence is always in valid range."""
        test_inputs = [
            "reasoning problem",
            "quick question",
            "@hermes deep analysis",
            "random words xyz",
            "plan steps organize approach",
        ]
        for text in test_inputs:
            scores, _ = self.router.evaluate(text)
            confidence = self.router.score_to_confidence(scores)
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)


class TestRuntimeManager(unittest.TestCase):
    """Test model runtime manager."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.manager = ModelRuntimeManager()
        self.mistral = MockModelAdapter("mistral")
        self.hermes = MockModelAdapter("hermes")
        self.manager.register_model("mistral", self.mistral)
        self.manager.register_model("hermes", self.hermes)

    def test_register_model(self) -> None:
        """Test model registration."""
        self.assertIn("mistral", self.manager.get_registered_models())
        self.assertIn("hermes", self.manager.get_registered_models())

    def test_register_duplicate_fails(self) -> None:
        """Test duplicate registration fails."""
        with self.assertRaises(ValueError):
            self.manager.register_model("mistral", MockModelAdapter("mistral"))

    def test_load_model(self) -> None:
        """Test loading a model."""
        adapter = self.manager.load_model("mistral")
        self.assertTrue(adapter.is_available())
        self.assertEqual(self.manager.get_active_model_id(), "mistral")

    def test_single_active_model(self) -> None:
        """Test only one model active at a time."""
        self.manager.load_model("mistral")
        self.assertTrue(self.mistral.is_available())
        self.assertFalse(self.hermes.is_available())

        # Load hermes
        self.manager.load_model("hermes")
        self.assertFalse(self.mistral.is_available())
        self.assertTrue(self.hermes.is_available())

    def test_load_already_active(self) -> None:
        """Test loading already-active model is no-op."""
        self.manager.load_model("mistral")
        load_count_1 = len(self.manager._load_history)

        # Load same model again
        self.manager.load_model("mistral")
        load_count_2 = len(self.manager._load_history)

        # Should increment
        self.assertEqual(load_count_1 + 1, load_count_2)

    def test_unload_model(self) -> None:
        """Test unloading a model."""
        self.manager.load_model("mistral")
        self.manager.unload_model("mistral")
        self.assertFalse(self.mistral.is_available())
        self.assertIsNone(self.manager.get_active_model_id())

    def test_get_active_model_none(self) -> None:
        """Test get_active_model when nothing loaded."""
        self.assertIsNone(self.manager.get_active_model())

    def test_unload_all(self) -> None:
        """Test unloading all models."""
        self.manager.load_model("mistral")
        self.manager.unload_all()
        self.assertFalse(self.mistral.is_available())
        self.assertIsNone(self.manager.get_active_model_id())


class TestModelAdapters(unittest.TestCase):
    """Test model adapter interface compliance."""

    def test_mistral_adapter_interface(self) -> None:
        """Test Mistral adapter complies with interface."""
        adapter = MistralAdapter()
        self.assertFalse(adapter.is_available())

        adapter.load()
        self.assertTrue(adapter.is_available())

        response = adapter.generate("test prompt")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

        adapter.unload()
        self.assertFalse(adapter.is_available())

    def test_hermes_adapter_interface(self) -> None:
        """Test Hermes adapter complies with interface."""
        adapter = HermesAdapter()
        adapter.load()
        self.assertTrue(adapter.is_available())

        response = adapter.generate("test prompt")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

        adapter.unload()
        self.assertFalse(adapter.is_available())

    def test_adapter_idempotent_load(self) -> None:
        """Test loading twice is safe."""
        adapter = MistralAdapter()
        adapter.load()
        adapter.load()  # Should not error
        self.assertTrue(adapter.is_available())
        adapter.unload()

    def test_adapter_idempotent_unload(self) -> None:
        """Test unloading twice is safe."""
        adapter = MistralAdapter()
        adapter.load()
        adapter.unload()
        adapter.unload()  # Should not error
        self.assertFalse(adapter.is_available())

    def test_adapter_generate_requires_load(self) -> None:
        """Test generate fails if not loaded."""
        adapter = MistralAdapter()
        with self.assertRaises(RuntimeError):
            adapter.generate("test")

    def test_adapter_get_model_info(self) -> None:
        """Test get_model_info returns valid data."""
        adapter = MistralAdapter()
        info = adapter.get_model_info()
        self.assertIn("model_name", info)
        self.assertIn("adapter_type", info)
        self.assertIn("is_loaded", info)


class TestConfidenceEscalation(unittest.TestCase):
    """Test confidence threshold escalation."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = ModelSelectorConfig(confidence_threshold=0.70)
        self.heuristic = HeuristicRouter(self.config)

    def test_threshold_comparison(self) -> None:
        """Test confidence vs threshold."""
        # High confidence case
        scores, _ = self.heuristic.evaluate("@hermes complex reasoning")
        conf = self.heuristic.score_to_confidence(scores)
        self.assertGreaterEqual(conf, self.config.confidence_threshold)

        # Low confidence case
        scores, _ = self.heuristic.evaluate("xyz random text")
        conf = self.heuristic.score_to_confidence(scores)
        self.assertLess(conf, self.config.confidence_threshold)

    def test_configurable_threshold(self) -> None:
        """Test threshold is configurable."""
        config_low = ModelSelectorConfig(confidence_threshold=0.3)
        config_high = ModelSelectorConfig(confidence_threshold=0.9)

        self.assertEqual(config_low.confidence_threshold, 0.3)
        self.assertEqual(config_high.confidence_threshold, 0.9)


class TestLLMRouterValidation(unittest.TestCase):
    """Test LLM router output validation."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_adapter = MockModelAdapter("mistral")
        self.mock_adapter.load()

    def test_valid_json_parsing(self) -> None:
        """Test valid JSON parsing."""
        router = LLMRouter(self.mock_adapter)
        fallback = RoutingDecision("mistral", 0.5, "heuristic")

        # Test with valid JSON
        valid_json = '{"model": "hermes", "confidence": 0.85, "reason": "test"}'
        decision = router._parse_routing_response(valid_json)

        self.assertIsNotNone(decision)
        self.assertEqual(decision.model, "hermes")
        self.assertEqual(decision.confidence, 0.85)

    def test_invalid_json_fallback(self) -> None:
        """Test invalid JSON triggers fallback."""
        router = LLMRouter(self.mock_adapter)
        fallback = RoutingDecision("mistral", 0.5, "heuristic")

        # Test with invalid JSON
        invalid_json = "this is not json at all"
        decision = router._parse_routing_response(invalid_json)

        self.assertIsNone(decision)

    def test_json_extraction_from_text(self) -> None:
        """Test extracting JSON from surrounding text."""
        router = LLMRouter(self.mock_adapter)

        # JSON embedded in text
        text_with_json = (
            'The best choice is {"model": "hermes", "confidence": 0.9, "reason": "test"} for this'
        )
        decision = router._parse_routing_response(text_with_json)

        self.assertIsNotNone(decision)
        self.assertEqual(decision.model, "hermes")

    def test_confidence_validation(self) -> None:
        """Test confidence value validation."""
        router = LLMRouter(self.mock_adapter)

        # Invalid confidence (>1.0)
        invalid_high = '{"model": "hermes", "confidence": 1.5, "reason": "test"}'
        decision = router._parse_routing_response(invalid_high)
        self.assertIsNone(decision)

        # Invalid confidence (<0.0)
        invalid_low = '{"model": "hermes", "confidence": -0.5, "reason": "test"}'
        decision = router._parse_routing_response(invalid_low)
        self.assertIsNone(decision)

    def test_model_validation(self) -> None:
        """Test model field validation."""
        router = LLMRouter(self.mock_adapter)

        # Invalid model
        invalid_model = '{"model": "gpt4", "confidence": 0.8, "reason": "test"}'
        decision = router._parse_routing_response(invalid_model)
        self.assertIsNone(decision)


class TestHybridSelector(unittest.TestCase):
    """Test hybrid model selector integration."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = ModelSelectorConfig(confidence_threshold=0.70)
        self.heuristic = HeuristicRouter(self.config)
        self.mock_adapter = MockModelAdapter("mistral")
        self.mock_adapter.load()
        self.llm_router = LLMRouter(self.mock_adapter, self.config)
        self.selector = HybridModelSelector(
            self.heuristic, self.llm_router, self.config
        )

    def test_explicit_hint_priority(self) -> None:
        """Test explicit hints have highest priority."""
        decision = self.selector.select_model("@hermes solve this")
        self.assertEqual(decision.model, "hermes")
        self.assertEqual(decision.source, "heuristic")

    def test_high_confidence_no_llm(self) -> None:
        """Test high confidence doesn't trigger LLM routing."""
        decision = self.selector.select_model("@mistral quick answer")
        self.assertEqual(decision.source, "heuristic")

    def test_selection_history(self) -> None:
        """Test selection history tracking."""
        self.selector.select_model("@hermes task 1")
        self.selector.select_model("@mistral task 2")
        history = self.selector.get_selection_history()

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["model"], "hermes")
        self.assertEqual(history[1]["model"], "mistral")

    def test_statistics(self) -> None:
        """Test routing statistics."""
        self.selector.select_model("@hermes reasoning")
        self.selector.select_model("@mistral quick")
        self.selector.select_model("@hermes analysis")

        stats = self.selector.get_statistics()
        self.assertEqual(stats["total_selections"], 3)
        self.assertEqual(stats["hermes_selected"], 2)
        self.assertEqual(stats["mistral_selected"], 1)


def run_tests() -> None:
    """Run all tests."""
    unittest.main(argv=[""], exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()
