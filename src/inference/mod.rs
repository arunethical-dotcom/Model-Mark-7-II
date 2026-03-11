/// Inference Engine Module — Unified trait for llama.cpp backend
///
/// Loads and runs GGUF models directly using llama-cpp-2 FFI bindings.
/// Falls back to MockInferenceEngine for testing without a model file.

#[cfg(feature = "llama")]
pub mod llama;

use std::time::Duration;
use tracing::info;

use crate::error::Result;

// ─── Shared trait ────────────────────────────────────────────────────────────

/// Trait representing any inference backend.
///
/// Implementations must be Send + Sync so they can be used from a
/// `spawn_blocking` context issued by the async FSM kernel.
pub trait InferenceEngine: Send + Sync {
    /// Run inference on `prompt`, respecting the given wall-clock `timeout`.
    ///
    /// Returns the raw model output string, or a `JarviisError::Inference` /
    /// `JarviisError::Internal` on failure or timeout.
    fn infer(&self, prompt: String, timeout: Duration) -> Result<String>;
}

// ─── Mock engine (fallback for testing without model) ─────────────────────────

/// A deterministic mock that echoes the user's request back safely.
///
/// This satisfies the full FSM contract for testing purposes.
/// Used when GGUF model is unavailable.
pub struct MockInferenceEngine;

impl MockInferenceEngine {
    pub fn new() -> Self {
        Self
    }
}

impl Default for MockInferenceEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl InferenceEngine for MockInferenceEngine {
    fn infer(&self, prompt: String, _timeout: Duration) -> Result<String> {
        // Extract only the USER INPUT section so we don't echo system context.
        let user_input = prompt
            .split("### USER INPUT")
            .nth(1)
            .unwrap_or("")
            .lines()
            .next()
            .unwrap_or("")
            .trim();

        let reply = if user_input.is_empty() {
            "Sir, I am online and ready to assist within the current deterministic kernel."
                .to_string()
        } else {
            format!(
                "Sir, I have received your request: \"{user_input}\". \
                 The cognitive kernel is operational."
            )
        };

        Ok(reply)
    }
}

// ─── Factory function for boot-time engine selection ────────────────────────

/// Select the best available inference backend based on configuration.
///
/// Priority:
///   1. Try LlamaEngine (loads GGUF model from disk) if `llama` feature enabled
///   2. Fall back to MockInferenceEngine if model file unavailable or feature disabled
pub fn select_inference_engine(
    _config: &crate::config::KernelConfig,
) -> Box<dyn InferenceEngine> {
    // Try llama.cpp first (if feature enabled)
    #[cfg(feature = "llama")]
    {
        match llama::LlamaEngine::load(
            &_config.model_path,
            _config.n_ctx,
            _config.n_threads,
        ) {
            Ok(engine) => {
                info!(
                    model_path = %_config.model_path,
                    n_ctx = _config.n_ctx,
                    n_threads = _config.n_threads,
                    n_batch = _config.n_batch,
                    n_ubatch = _config.n_ubatch,
                    "Successfully loaded GGUF model via llama.cpp FFI"
                );
                return Box::new(engine);
            }
            Err(e) => {
                eprintln!("Failed to load GGUF model from {}: {}", _config.model_path, e);
                eprintln!("Falling back to mock inference engine");
            }
        }
    }

    #[cfg(not(feature = "llama"))]
    {
        eprintln!("JARVIIS was not built with the `llama` feature.");
        eprintln!("Rebuild with: cargo build --release --features llama");
        eprintln!("Falling back to mock inference engine");
    }

    // Fallback to mock
    info!("Using MockInferenceEngine (deterministic fallback)");
    Box::new(MockInferenceEngine::new())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mock_engine() {
        let engine = MockInferenceEngine::new();
        let result = engine.infer("Hello".to_string(), Duration::from_secs(5));
        assert!(result.is_ok());
        let output = result.unwrap();
        assert!(!output.is_empty());
    }
}

