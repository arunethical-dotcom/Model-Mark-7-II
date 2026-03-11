/// Ollama HTTP API Backend — Async LLM Inference
///
/// Connects to a running Ollama server (http://localhost:11434/api/generate)
/// to perform actual model inference. Falls back to mock if unavailable.

use std::time::Duration;
use serde_json::{json, Value};
use tracing::{debug, warn, error};

use crate::error::{JarviisError, Result};

// ─── Ollama response types ────────────────────────────────────────────────────

/// Ollama /api/generate response structure (streaming).
#[derive(Debug, serde::Deserialize)]
pub struct OllamaResponse {
    /// The generated text chunk.
    pub response: String,
    /// Whether this is the final chunk (stream completed).
    pub done: bool,
}

// ─── Ollama inference engine ──────────────────────────────────────────────────

/// HTTP-based inference engine backed by Ollama.
///
/// Maintains a reqwest::Client for connection pooling and timeout enforcement.
pub struct OllamaEngine {
    client: reqwest::Client,
    base_url: String,
    model_name: String,
    timeout: Duration,
}

impl OllamaEngine {
    /// Create a new Ollama inference engine.
    ///
    /// # Arguments
    /// - `host`: Ollama server hostname (e.g., "localhost")
    /// - `port`: Ollama server port (e.g., 11434)
    /// - `model_name`: Model name in Ollama registry (e.g., "qwen")
    /// - `timeout`: Request timeout duration (e.g., Duration::from_secs(20))
    pub fn new(host: &str, port: u16, model_name: &str, timeout: Duration) -> Self {
        let base_url = format!("http://{}:{}", host, port);
        let client = reqwest::Client::new();
        
        Self {
            client,
            base_url,
            model_name: model_name.to_string(),
            timeout,
        }
    }

    /// Perform inference by calling the Ollama API synchronously.
    ///
    /// Returns the full generated response, or a JarviisError on network/timeout failure.
    pub fn infer_sync(&self, prompt: String) -> Result<String> {
        // Build the request body
        let request_body = json!({
            "model": self.model_name,
            "prompt": prompt,
            "stream": false,
            "temperature": 0.7,
        });

        debug!(
            model = %self.model_name,
            url = %self.base_url,
            "Ollama inference request"
        );

        // Execute the blocking HTTP request
        let response = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            tokio::task::block_in_place(|| {
                tokio::runtime::Handle::current().block_on(async {
                    self.client
                        .post(format!("{}/api/generate", self.base_url))
                        .json(&request_body)
                        .timeout(self.timeout)
                        .send()
                        .await
                })
            })
        })).map_err(|_| JarviisError::Inference("inference panic".to_string()))?;

        let response = response.map_err(|e| {
            error!(error = %e, "Ollama HTTP error");
            JarviisError::Inference(format!("Ollama HTTP error: {}", e))
        })?;

        if !response.status().is_success() {
            let status = response.status();
            error!(status = ?status, "Ollama returned error status");
            return Err(JarviisError::Inference(format!(
                "Ollama returned {}: ensure Ollama is running on {}:{}",
                status, self.base_url, self.model_name
            )));
        }

        // Parse the response
        let body_text = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            tokio::task::block_in_place(|| {
                tokio::runtime::Handle::current().block_on(async {
                    response.text().await
                })
            })
        })).map_err(|_| JarviisError::Inference("response panic".to_string()))?;

        let body_text = body_text.map_err(|e| {
            error!(error = %e, "Failed to read response body");
            JarviisError::Inference(format!("Failed to read response: {}", e))
        })?;

        // For non-streaming responses, Ollama returns a single JSON object
        let parsed: Value = serde_json::from_str(&body_text).map_err(|e| {
            error!(error = %e, body = %body_text, "Failed to parse Ollama response");
            JarviisError::Inference(format!("Failed to parse Ollama JSON: {}", e))
        })?;

        let generated_text = parsed
            .get("response")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        if generated_text.is_empty() {
            warn!("Ollama returned empty response");
            return Err(JarviisError::Inference(
                "Ollama model produced empty output".to_string(),
            ));
        }

        debug!(response_len = %generated_text.len(), "Ollama inference succeeded");
        Ok(generated_text)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ollama_engine_creation() {
        let engine = OllamaEngine::new("localhost", 11434, "qwen", Duration::from_secs(20));
        assert_eq!(engine.base_url, "http://localhost:11434");
        assert_eq!(engine.model_name, "qwen");
    }
}
