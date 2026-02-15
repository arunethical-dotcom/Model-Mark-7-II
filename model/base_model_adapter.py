"""
Model Adapter Layer

Provides unified interface for different LLM models.
Adapters abstract model-specific details from core orchestrator.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseModelAdapter(ABC):
    """
    Abstract base class for all model adapters.

    All models must implement this interface to be compatible with the
    model runtime manager.
    """

    def __init__(self, model_name: str) -> None:
        """
        Initialize adapter.

        Args:
            model_name: Human-readable model identifier
        """
        self.model_name = model_name
        self.is_loaded = False

    @abstractmethod
    def load(self) -> None:
        """
        Load model into memory.

        This should handle initialization, weight loading, etc.
        Must be idempotent (safe to call multiple times).

        Raises:
            RuntimeError: If model fails to load
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """
        Unload model from memory.

        This should release all resources associated with the model.
        Must be idempotent.
        """
        pass

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        Generate response from prompt.

        This is the primary interface used by the orchestrator.

        Args:
            prompt: Input text prompt
            **kwargs: Optional generation parameters

        Returns:
            Generated text response

        Raises:
            RuntimeError: If model not loaded
            ValueError: If prompt is invalid
        """
        pass

    def is_available(self) -> bool:
        """
        Check if model is available for use.

        Returns:
            True if model is loaded and ready
        """
        return self.is_loaded

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get metadata about the model.

        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "is_loaded": self.is_loaded,
            "adapter_type": self.__class__.__name__,
        }


class MistralAdapter(BaseModelAdapter):
    """
    Adapter for Mistral-7B-Instruct model via llama.cpp.

    Backend: llama.cpp server on port 8080
    Model: Mistral-7B-Instruct-v0.2-Q4_K_M.gguf
    Purpose: Deep reasoning, high-quality answers
    """

    def __init__(self, model_name: str = "mistral_7b") -> None:
        """
        Initialize Mistral adapter.

        Args:
            model_name: Model identifier (mistral_7b)
        """
        super().__init__(model_name)
        self._model_instance: Optional[Any] = None
        self._context: Optional[Dict[str, Any]] = None
        self._governed_backend: Optional[Any] = None
        self._port = 8080  # Mistral-7B on port 8080

    def load(self) -> None:
        """Load Mistral model."""
        if self.is_loaded:
            return  # Already loaded

        # Model loaded via governed backend
        self._model_instance = f"GovernedMistralModel({self.model_name})"
        self._context = {}
        self.is_loaded = True
    
    def set_governed_backend(self, backend) -> None:
        """Set governed backend for LLM calls."""
        self._governed_backend = backend

    def unload(self) -> None:
        """Unload Mistral model from memory."""
        if not self.is_loaded:
            return  # Already unloaded

        self._model_instance = None
        self._context = None
        self.is_loaded = False

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        Generate response using Mistral through governance layer.

        Args:
            prompt: Input prompt
            **kwargs: Generation parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text

        Raises:
            RuntimeError: If model not loaded
        """
        if not self.is_loaded:
            raise RuntimeError(
                f"Mistral model {self.model_name} not loaded. Call load() first."
            )

        if not prompt or not isinstance(prompt, str):
            raise ValueError("Prompt must be a non-empty string")
        
        # Use governed backend if available
        if self._governed_backend:
            return self._governed_backend.generate(prompt)
        
        # Fallback to mock response
        return f"[Mistral Response to: {prompt[:50]}...]"

    def get_model_info(self) -> Dict[str, Any]:
        """Get Mistral-specific metadata."""
        info = super().get_model_info()
        info.update(
            {
                "family": "Mistral",
                "parameters": "7B",
                "optimization": "Fast inference, low compute",
            }
        )
        return info


class HermesAdapter(BaseModelAdapter):
    """
    Adapter for deep reasoning via llama.cpp.

    Backend: llama.cpp server on port 8080
    Model: Mistral-7B-Instruct-v0.2-Q4_K_M.gguf
    Purpose: Multi-step reasoning, complex planning, deep analysis
    """

    def __init__(self, model_name: str = "mistral_7b") -> None:
        """
        Initialize Hermes adapter (uses same backend as Mistral).

        Args:
            model_name: Model identifier (mistral_7b)
        """
        super().__init__(model_name)
        self._model_instance: Optional[Any] = None
        self._context: Optional[Dict[str, Any]] = None
        self._governed_backend: Optional[Any] = None
        self._port = 8080  # Deep reasoning on port 8080

    def load(self) -> None:
        """Load Hermes model."""
        if self.is_loaded:
            return  # Already loaded

        # Model loaded via governed backend
        self._model_instance = f"GovernedHermesModel({self.model_name})"
        self._context = {}
        self.is_loaded = True
    
    def set_governed_backend(self, backend) -> None:
        """Set governed backend for LLM calls."""
        self._governed_backend = backend

    def unload(self) -> None:
        """Unload Hermes model from memory."""
        if not self.is_loaded:
            return  # Already unloaded

        self._model_instance = None
        self._context = None
        self.is_loaded = False

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        Generate response using Hermes through governance layer.

        Args:
            prompt: Input prompt
            **kwargs: Generation parameters

        Returns:
            Generated text

        Raises:
            RuntimeError: If model not loaded
        """
        if not self.is_loaded:
            raise RuntimeError(
                f"Hermes model {self.model_name} not loaded. Call load() first."
            )

        if not prompt or not isinstance(prompt, str):
            raise ValueError("Prompt must be a non-empty string")
        
        # Use governed backend if available
        if self._governed_backend:
            return self._governed_backend.generate(prompt)
        
        # Fallback to mock response
        return f"[Hermes Response to: {prompt[:50]}...]"

    def get_model_info(self) -> Dict[str, Any]:
        """Get Hermes-specific metadata."""
        info = super().get_model_info()
        info.update(
            {
                "family": "Hermes-2-Pro-Mistral",
                "parameters": "7B",
                "optimization": "Deep reasoning, planning, analysis",
            }
        )
        return info


class MockModelAdapter(BaseModelAdapter):
    """
    Mock adapter for testing and development.

    Useful for testing routing logic without actual model inference.
    """

    def __init__(self, model_name: str = "mock-model") -> None:
        """Initialize mock adapter."""
        super().__init__(model_name)

    def load(self) -> None:
        """Load mock model (no-op)."""
        self.is_loaded = True

    def unload(self) -> None:
        """Unload mock model (no-op)."""
        self.is_loaded = False

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate mock response."""
        if not self.is_loaded:
            raise RuntimeError("Mock model not loaded")
        return f"Mock response for: {prompt[:50]}..."

    def get_model_info(self) -> Dict[str, Any]:
        """Get mock model info."""
        return {
            "model_name": self.model_name,
            "is_loaded": self.is_loaded,
            "adapter_type": "MockModelAdapter",
            "note": "For testing only",
        }
