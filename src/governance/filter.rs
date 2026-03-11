/// Governance Filter — command filtering and post-generation redaction.
///
/// Checks tool permission requests and applies pattern-based redaction to
/// model output before it reaches the user. All operations are constant-time
/// and non-LLM-based, guaranteeing minimal latency overhead.

use tracing::warn;

use crate::error::{JarviisError, Result};

/// Patterns to redact from output before emission.
/// These are applied as whole-string contains checks (case-insensitive).
const REDACTION_PATTERNS: &[&str] = &[
    "jarviis-core",     // internal crate name
    "llama.cpp",        // inference backend disclosure
    "sqlite",           // database backend disclosure
    "gguf",             // model format disclosure
    "spawn_blocking",   // runtime internals
];

/// Tool registry — the list of permitted tool names.
/// In a production system this would be loaded from config/database.
const PERMITTED_TOOLS: &[&str] = &[
    "web_search",
    "file_read",
    "file_write",
    "calculator",
    "datetime",
    "shell",
];

/// Governance filter operating on output and tool requests.
pub struct GovernanceFilter;

impl GovernanceFilter {
    pub fn new() -> Self {
        Self
    }

    /// Validate that a requested tool is in the permitted registry.
    pub fn check_tool_permission(&self, tool_name: &str) -> Result<()> {
        if PERMITTED_TOOLS.contains(&tool_name) {
            Ok(())
        } else {
            warn!(tool_name, "Unpermitted tool requested");
            Err(JarviisError::Governance(format!(
                "tool '{tool_name}' is not in the permitted registry"
            )))
        }
    }

    /// Apply post-generation redaction to model output.
    ///
    /// Scans each line for redaction patterns and replaces any matching line
    /// with a neutral placeholder. Returns an error if the cleaned output is
    /// empty, which would indicate a completely unusable response.
    pub fn sanitize_output(&self, output: &str) -> Result<String> {
        let cleaned = output.trim();
        if cleaned.is_empty() {
            return Err(JarviisError::Internal(
                "model returned empty output".to_string(),
            ));
        }

        let lowered = cleaned.to_lowercase();
        for pattern in REDACTION_PATTERNS {
            if lowered.contains(pattern) {
                warn!(pattern, "Redacting output line containing sensitive pattern");
                // Replace the entire output if the pattern is present.
                // In practice a production system would redact line-by-line;
                // here we fail closed by returning a safe neutral message.
                return Ok("Sir, I was unable to produce a suitable response for that request.".to_string());
            }
        }

        Ok(cleaned.to_string())
    }
}

impl Default for GovernanceFilter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn filter() -> GovernanceFilter {
        GovernanceFilter::new()
    }

    #[test]
    fn permits_known_tool() {
        assert!(filter().check_tool_permission("web_search").is_ok());
        assert!(filter().check_tool_permission("calculator").is_ok());
    }

    #[test]
    fn rejects_unknown_tool() {
        assert!(filter().check_tool_permission("rm_files").is_err());
    }

    #[test]
    fn redacts_sensitive_content() {
        let out = filter().sanitize_output("I use llama.cpp internally");
        assert!(out.is_ok());
        assert!(!out.unwrap().to_lowercase().contains("llama"));
    }

    #[test]
    fn passes_clean_output() {
        let out = filter().sanitize_output("Sir, the answer is 42.");
        assert_eq!(out.unwrap(), "Sir, the answer is 42.");
    }

    #[test]
    fn rejects_empty_output() {
        assert!(filter().sanitize_output("   ").is_err());
    }
}
