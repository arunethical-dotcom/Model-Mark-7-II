"""
Model Runtime Manager

Manages model lifecycle: loading, unloading, and switching.
Enforces single-active-model guarantee.
"""

from typing import Dict, Optional, List, Any
from .base_model_adapter import BaseModelAdapter


class ModelRuntimeManager:
    """
    Manages model lifecycle and enforces single-active-model guarantee.

    Responsibilities:
    - Track available models
    - Load/unload models
    - Prevent dual-model loading
    - Provide current model access
    """

    def __init__(self) -> None:
        """Initialize runtime manager."""
        self._models: Dict[str, BaseModelAdapter] = {}
        self._active_model: Optional[str] = None
        self._load_history: List[str] = []

    def register_model(self, model_id: str, adapter: BaseModelAdapter) -> None:
        """
        Register a model with a given adapter.

        Args:
            model_id: Identifier for the model (e.g., "mistral", "hermes")
            adapter: BaseModelAdapter instance

        Raises:
            ValueError: If model_id already registered
        """
        if model_id in self._models:
            raise ValueError(f"Model '{model_id}' already registered")

        self._models[model_id] = adapter

    def load_model(self, model_id: str) -> BaseModelAdapter:
        """
        Load a model, unloading any previously active model.

        Enforces single-active-model guarantee.

        Args:
            model_id: ID of model to load

        Returns:
            Loaded BaseModelAdapter instance

        Raises:
            KeyError: If model_id not registered
            RuntimeError: If load fails
        """
        if model_id not in self._models:
            raise KeyError(f"Model '{model_id}' not registered")

        # Check if already active
        if self._active_model == model_id:
            return self._models[model_id]

        # Unload previous model if exists
        if self._active_model is not None:
            self._unload_active_model()

        # Load new model
        adapter = self._models[model_id]
        try:
            adapter.load()
            self._active_model = model_id
            self._load_history.append(model_id)
            return adapter
        except Exception as e:
            self._active_model = None
            raise RuntimeError(f"Failed to load model '{model_id}': {e}") from e

    def unload_model(self, model_id: Optional[str] = None) -> None:
        """
        Unload a specific model or active model.

        Args:
            model_id: Model to unload (if None, unload active)

        Raises:
            KeyError: If model_id not registered
        """
        if model_id is None:
            self._unload_active_model()
        else:
            if model_id not in self._models:
                raise KeyError(f"Model '{model_id}' not registered")
            if self._active_model == model_id:
                self._unload_active_model()
            else:
                self._models[model_id].unload()

    def _unload_active_model(self) -> None:
        """Unload the currently active model."""
        if self._active_model is not None:
            try:
                self._models[self._active_model].unload()
            except Exception as e:
                # Log but don't crash - best effort unload
                print(f"Warning: Failed to unload {self._active_model}: {e}")
            finally:
                self._active_model = None

    def get_active_model(self) -> Optional[BaseModelAdapter]:
        """
        Get the currently active model adapter.

        Returns:
            Active model adapter or None if no model loaded
        """
        if self._active_model is None:
            return None
        return self._models[self._active_model]

    def get_active_model_id(self) -> Optional[str]:
        """
        Get the ID of the currently active model.

        Returns:
            Active model ID or None
        """
        return self._active_model

    def is_model_loaded(self, model_id: str) -> bool:
        """
        Check if a specific model is loaded.

        Args:
            model_id: Model ID to check

        Returns:
            True if model is loaded
        """
        if model_id not in self._models:
            return False
        return self._models[model_id].is_available()

    def get_registered_models(self) -> List[str]:
        """
        Get list of all registered model IDs.

        Returns:
            List of model IDs
        """
        return list(self._models.keys())

    def get_status(self) -> Dict[str, Any]:
        """
        Get runtime status information.

        Returns:
            Dictionary with status details
        """
        return {
            "active_model": self._active_model,
            "registered_models": self.get_registered_models(),
            "load_history": self._load_history,
            "model_states": {
                model_id: adapter.get_model_info()
                for model_id, adapter in self._models.items()
            },
        }

    def unload_all(self) -> None:
        """Unload all models."""
        for model_id in list(self._models.keys()):
            self.unload_model(model_id)
        self._active_model = None
