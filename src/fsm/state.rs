/// Canonical FSM state definitions for JARVIIS Cognitive Kernel OS.
///
/// States progress strictly S0 → S9 per the architecture specification.
/// Any failure in any state transitions immediately to S_ERR, which
/// always resolves back to S0 (fail-closed doctrine).

/// All valid states of the JARVIIS FSM kernel.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[allow(clippy::upper_case_acronyms)]
pub enum FsmState {
    /// S0 — IDLE: Initial/waiting state. System ready for input.
    S0Idle,
    /// S1 — INPUT_VALIDATION: Validate length, entropy, restricted patterns.
    S1InputValidation,
    /// S2 — MEMORY_RETRIEVAL: Retrieve bounded high-score entries from SQLite.
    S2MemoryRetrieval,
    /// S3 — IDENTITY_INJECTION: Assemble prompt with immutable identity block.
    S3IdentityInjection,
    /// S4 — INFERENCE: Single inference call via llama.cpp (or mock).
    S4Inference,
    /// S5 — IDENTITY_FIREWALL: Post-inference identity and structural validation.
    S5IdentityFirewall,
    /// S6 — TOOL_EXECUTION: Execute permitted Python tool via subprocess bridge.
    S6ToolExecution,
    /// S7 — OUTPUT_SANITIZATION: Redact sensitive content, validate format.
    S7OutputSanitization,
    /// S8 — MEMORY_WRITE: Persist relevant interaction to SQLite.
    S8MemoryWrite,
    /// S9 — EMIT_RESPONSE: Return sanitized response to caller. Returns to S0.
    S9EmitResponse,
    /// S_ERR — ERROR_RECOVERY: Explicit failure containment state.
    /// Triggered by any failure. Emits controlled error, returns to S0.
    SErr,
}

impl std::fmt::Display for FsmState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let name = match self {
            FsmState::S0Idle => "S0_IDLE",
            FsmState::S1InputValidation => "S1_INPUT_VALIDATION",
            FsmState::S2MemoryRetrieval => "S2_MEMORY_RETRIEVAL",
            FsmState::S3IdentityInjection => "S3_IDENTITY_INJECTION",
            FsmState::S4Inference => "S4_INFERENCE",
            FsmState::S5IdentityFirewall => "S5_IDENTITY_FIREWALL",
            FsmState::S6ToolExecution => "S6_TOOL_EXECUTION",
            FsmState::S7OutputSanitization => "S7_OUTPUT_SANITIZATION",
            FsmState::S8MemoryWrite => "S8_MEMORY_WRITE",
            FsmState::S9EmitResponse => "S9_EMIT_RESPONSE",
            FsmState::SErr => "S_ERR",
        };
        write!(f, "{name}")
    }
}

/// The outcome of a complete FSM cycle.
#[derive(Debug)]
pub enum FsmCycleResult {
    /// Normal completion — contains the sanitized response string.
    Response(String),
    /// Controlled error — the system failed closed; contains the safe error message.
    ControlledError(String),
    /// Input was rejected at S1 — contains the validation rejection message.
    InputRejected(String),
}

impl FsmCycleResult {
    /// Unwrap to a displayable string regardless of variant.
    pub fn into_string(self) -> String {
        match self {
            FsmCycleResult::Response(s) => s,
            FsmCycleResult::ControlledError(s) => s,
            FsmCycleResult::InputRejected(s) => s,
        }
    }
}
