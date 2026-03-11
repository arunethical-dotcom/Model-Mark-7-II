use std::time::Duration;

use serde_json::{json, Value};
use tokio::io::AsyncWriteExt;
use tokio::process::Command;
use tokio::time;
use tracing::{debug, error, warn};

use crate::config::KernelConfig;
use crate::error::{JarviisError, Result};

/// Represents a parsed tool call from an LLM output.
#[derive(Debug, Clone)]
pub struct ToolCall {
    pub name: String,
    pub args: Value,
}

impl ToolCall {
    /// Parse JSON into a ToolCall struct.
    pub fn parse(raw_json: &str) -> Option<Self> {
        let v: Value = serde_json::from_str(raw_json).ok()?;
        let name = v.get("name")?.as_str()?.to_string();
        let args = v
            .get("args")
            .cloned()
            .unwrap_or(Value::Object(Default::default()));
        Some(ToolCall { name, args })
    }
}

/// Python subprocess bridge — JSON-over-STDIO communication.
/// Safe timeout handling + subprocess kill guarantee + no child moves.
pub struct PythonBridge {
    tool_timeout: Duration,
    scripts_dir: String,
    python_exe: String,
}

impl PythonBridge {
    pub fn new(config: &KernelConfig) -> Self {
        Self {
            tool_timeout: Duration::from_secs(config.tool_timeout_secs),
            scripts_dir: "tools/".to_string(),
            python_exe: "python".to_string(),
        }
    }

    /// Execute a Python tool by spawning a subprocess, sending JSON, and reading JSON.
    pub async fn execute(&self, call: &ToolCall) -> Result<Value> {
        let script_path = format!("{}{}.py", self.scripts_dir, call.name);

        let request_json = json!({
            "tool": call.name,
            "args": call.args
        });
        let request_bytes = serde_json::to_vec(&request_json)
            .map_err(|e| JarviisError::Tool(format!("serialization failed: {e}")))?;

        debug!("Spawning Python tool: {}", call.name);

        let mut child = Command::new(&self.python_exe)
            .arg(&script_path)
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .spawn()
            .map_err(|e| JarviisError::Tool(format!("failed to spawn python: {e}")))?;

        // Write JSON into subprocess stdin.
        if let Some(stdin) = child.stdin.as_mut() {
            stdin
                .write_all(&request_bytes)
                .await
                .map_err(|e| JarviisError::Tool(format!("stdin write failed: {e}")))?;
        }

        // Get PID for safe kill on timeout
        let pid = child.id().unwrap_or(0);

        // Use non-moving wait() for timeout checking
        let wait_future = child.wait();

        let timeout = self.tool_timeout;

        let timeout_result = time::timeout(timeout, wait_future).await;

        match timeout_result {
            // Process finished within timeout
            Ok(Ok(_status)) => {
                // NOW safe to call wait_with_output (moves the child)
                let output = child
                    .wait_with_output()
                    .await
                    .map_err(|e| JarviisError::Tool(format!("output read failed: {e}")))?;

                if !output.status.success() {
                    let stderr = String::from_utf8_lossy(&output.stderr);
                    error!("Tool '{}' stderr: {}", call.name, stderr);
                    return Err(JarviisError::Tool(format!(
                        "tool '{}' exited with error code {}",
                        call.name, output.status
                    )));
                }

                let response: Value = serde_json::from_slice(&output.stdout)
                    .map_err(|e| JarviisError::Tool(format!("invalid JSON: {e}")))?;

                // Extract .result field or return whole object
                return Ok(response.get("result").cloned().unwrap_or(response));
            }

            // Tool process returned error before finishing
            Ok(Err(e)) => {
                return Err(JarviisError::Tool(format!("subprocess wait error: {e}")));
            }

            // Timeout fired
            Err(_) => {
                warn!(
                    "Tool '{}' timed out after {}s. Killing PID {}",
                    call.name,
                    timeout.as_secs(),
                    pid
                );

                let _ = child.kill().await;
                let _ = child.wait().await;

                return Err(JarviisError::Tool(format!(
                    "tool '{}' timed out after {}s",
                    call.name,
                    timeout.as_secs()
                )));
            }
        }
    }
}