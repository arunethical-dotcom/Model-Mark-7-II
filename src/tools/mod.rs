pub mod bridge;

use crate::config::KernelConfig;
use crate::error::{JarviisError, Result};

use self::bridge::{PythonBridge, ToolCall};

/// Tool subsystem — permission-gated Python subprocess bridge.
pub struct ToolSubsystem {
    bridge: PythonBridge,
}

impl ToolSubsystem {
    pub fn new(config: &KernelConfig) -> Self {
        Self {
            bridge: PythonBridge::new(config),
        }
    }

    /// Parse a raw TOOL_CALL JSON string, validate, and execute via the bridge.
    ///
    /// Called at S6. Returns the tool result as a JSON string, or an error
    /// that the FSM will route to S_ERR.
    pub async fn execute_tool_call(&self, raw_json: &str) -> Result<String> {
        let call = ToolCall::parse(raw_json).ok_or_else(|| {
            JarviisError::Tool(format!("failed to parse TOOL_CALL JSON: '{raw_json}'"))
        })?;

        let result = self.bridge.execute(&call).await?;
        serde_json::to_string(&result)
            .map_err(|e| JarviisError::Tool(format!("failed to serialize tool result: {e}")))
    }
}
