pub mod filter;
pub mod validator;

use crate::config::KernelConfig;
use crate::error::Result;

pub use filter::GovernanceFilter;
pub use validator::InputValidator;

/// Combined governance subsystem — input validation + output filtering.
pub struct GovernanceSubsystem {
    validator: InputValidator,
    filter:    GovernanceFilter,
}

impl GovernanceSubsystem {
    pub fn new(config: &KernelConfig) -> Self {
        Self {
            validator: InputValidator::new(config),
            filter:    GovernanceFilter::new(),
        }
    }

    /// Validate raw user input (S1).
    pub fn validate_input(&self, input: &str) -> Result<()> {
        self.validator.validate(input)
    }

    /// Post-generation output sanitization (S7).
    pub fn sanitize_output(&self, output: &str) -> Result<String> {
        self.filter.sanitize_output(output)
    }

    /// Tool permission check (used from ToolSubsystem at S6).
    pub fn check_tool_permission(&self, tool_name: &str) -> Result<()> {
        self.filter.check_tool_permission(tool_name)
    }
}
