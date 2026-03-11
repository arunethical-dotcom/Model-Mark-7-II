use thiserror::Error;

/// Unified error type for the JARVIIS Cognitive Kernel OS.
///
/// Every variant maps to a specific FSM failure domain, allowing fine-grained
/// S_ERR logging without exposing internal details to the user.
#[derive(Debug, Error)]
pub enum JarviisError {
    #[error("input validation failed: {0}")]
    InputValidation(String),

    #[error("inference error: {0}")]
    Inference(String),

    #[error("inference timeout: {0}")]
    Timeout(String),

    #[error("tool error: {0}")]
    Tool(String),

    #[error("memory error: {0}")]
    Memory(String),

    #[error("identity violation: {0}")]
    IdentityViolation(String),

    #[error("governance violation: {0}")]
    Governance(String),

    #[error("internal error: {0}")]
    Internal(String),
}

pub type Result<T> = std::result::Result<T, JarviisError>;
