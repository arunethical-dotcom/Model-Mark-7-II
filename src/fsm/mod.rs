pub mod state;
pub mod transition;

use std::sync::Arc;
use std::time::Duration;

use tokio::task;
use tracing::{error, warn};

use crate::config::KernelConfig;
use crate::error::JarviisError;
use crate::governance::GovernanceSubsystem;
use crate::identity::IdentitySubsystem;
use crate::inference::InferenceEngine;
use crate::memory::MemorySubsystem;
use crate::tools::ToolSubsystem;

use self::state::{FsmCycleResult, FsmState};
use self::transition::{detect_tool_call, CycleTimer, StateTimer};

/// Format a list of memory entries into the snippet injected into the prompt.
fn memory_to_context(entries: &[crate::memory::scoring::MemoryEntry]) -> String {
    if entries.is_empty() {
        return String::new();
    }
    let mut s = String::from("Relevant context:\n");
    for e in entries {
        s.push_str("- ");
        s.push_str(&e.content);
        s.push('\n');
    }
    s
}

/// Emit the canonical S_ERR response and log the failure.
fn fail_closed(state: FsmState, error: JarviisError) -> FsmCycleResult {
    error!(state = %state, err = %error, "FSM → S_ERR (failing closed)");
    FsmCycleResult::ControlledError(
        "Sir, I encountered an internal error while processing your request.".to_string(),
    )
}

// ─── FsmKernel ────────────────────────────────────────────────────────────────

pub struct FsmKernel {
    config:     KernelConfig,
    identity:   Arc<IdentitySubsystem>,
    governance: Arc<GovernanceSubsystem>,
    memory:     Arc<MemorySubsystem>,
    inference:  Arc<dyn InferenceEngine>,
    tools:      Arc<ToolSubsystem>,
}

impl FsmKernel {
    pub fn new(
        config:     KernelConfig,
        identity:   IdentitySubsystem,
        governance: GovernanceSubsystem,
        memory:     MemorySubsystem,
        inference:  Box<dyn InferenceEngine>,
        tools:      ToolSubsystem,
    ) -> Self {
        Self {
            config,
            identity:   Arc::new(identity),
            governance: Arc::new(governance),
            memory:     Arc::new(memory),
            inference:  Arc::from(inference),
            tools:      Arc::new(tools),
        }
    }

    /// Run a single deterministic FSM cycle from S0 → S9 (or S_ERR → S0).
    ///
    /// All internal failures converge to `fail_closed()` which returns the
    /// canonical S_ERR controlled error message without exposing internals.
    pub async fn run_cycle(&self, user_input: String) -> String {
        let cycle_timer = CycleTimer::start();

        // ── S1: INPUT_VALIDATION ────────────────────────────────────────────
        let t = StateTimer::enter(FsmState::S1InputValidation);
        if let Err(e) = self.governance.validate_input(&user_input) {
            warn!(error = %e, "Input rejected at S1");
            t.fail(FsmState::S9EmitResponse, &e);
            cycle_timer.finish();
            return format!("Sir, I cannot process that request: {e}");
        }
        t.transition(FsmState::S2MemoryRetrieval);

        // ── S2: MEMORY_RETRIEVAL ────────────────────────────────────────────
        let t = StateTimer::enter(FsmState::S2MemoryRetrieval);
        let memory_entries = {
            let mem = self.memory.clone();
            let input_clone = user_input.clone();
            let max_tokens = self.config.max_memory_tokens;
            let handle = task::spawn_blocking(move || mem.retrieve_relevant(&input_clone, max_tokens));
            match handle.await
                .map_err(|e| JarviisError::Internal(format!("join error: {e}")))
                .and_then(|r| r)
            {
                Ok(v)  => { t.transition(FsmState::S3IdentityInjection); v }
                Err(e) => { t.fail(FsmState::SErr, &e); cycle_timer.finish(); return fail_closed(FsmState::S2MemoryRetrieval, e).into_string(); }
            }
        };
        let memory_context = memory_to_context(&memory_entries);

        // ── S3: IDENTITY_INJECTION ──────────────────────────────────────────
        let t = StateTimer::enter(FsmState::S3IdentityInjection);
        let prompt = self.identity.assemble_prompt(&user_input, &memory_context);
        t.transition(FsmState::S4Inference);

        // ── S4: INFERENCE ───────────────────────────────────────────────────
        let t = StateTimer::enter(FsmState::S4Inference);
        let raw_output = {
            let engine = self.inference.clone();
            let prompt_clone = prompt.clone();
            let timeout = Duration::from_secs(self.config.inference_timeout_secs);
            let handle = task::spawn_blocking(move || engine.infer(prompt_clone, timeout));
            match handle.await
                .map_err(|e| JarviisError::Internal(format!("join error: {e}")))
                .and_then(|r| r)
            {
                Ok(v)  => { t.transition(FsmState::S5IdentityFirewall); v }
                Err(e) => { t.fail(FsmState::SErr, &e); cycle_timer.finish(); return fail_closed(FsmState::S4Inference, e).into_string(); }
            }
        };

        // ── S5: IDENTITY_FIREWALL (with one regeneration attempt) ───────────
        let t = StateTimer::enter(FsmState::S5IdentityFirewall);
        let (firewalled_output, needs_tool) =
            match self.identity.check_firewall(&raw_output)
        {
            crate::identity::FirewallVerdict::Clean(s) | crate::identity::FirewallVerdict::Patched(s) => {
                let has_tool = detect_tool_call(&s).is_some();
                t.transition(if has_tool { FsmState::S6ToolExecution } else { FsmState::S7OutputSanitization });
                (s, has_tool)
            }
            crate::identity::FirewallVerdict::Regenerate => {
                // One regeneration attempt.
                warn!("S5: firewall requested regeneration — retrying inference");
                let engine = self.inference.clone();
                let prompt_clone = prompt.clone();
                let timeout = Duration::from_secs(self.config.inference_timeout_secs);
                let handle = task::spawn_blocking(move || engine.infer(prompt_clone, timeout));
                let regen = match handle.await
                    .map_err(|e| JarviisError::Internal(format!("join error: {e}")))
                    .and_then(|r| r)
                {
                    Ok(v)  => v,
                    Err(e) => { t.fail(FsmState::SErr, &e); cycle_timer.finish(); return fail_closed(FsmState::S5IdentityFirewall, e).into_string(); }
                };
                // Second pass must succeed cleanly.
                match self.identity.enforce_strict(&regen) {
                    Ok(s) => {
                        let has_tool = detect_tool_call(&s).is_some();
                        t.transition(if has_tool { FsmState::S6ToolExecution } else { FsmState::S7OutputSanitization });
                        (s, has_tool)
                    }
                    Err(e) => { t.fail(FsmState::SErr, &e); cycle_timer.finish(); return fail_closed(FsmState::S5IdentityFirewall, e).into_string(); }
                }
            }
            crate::identity::FirewallVerdict::HardViolation(e) => {
                t.fail(FsmState::SErr, &e); cycle_timer.finish();
                return fail_closed(FsmState::S5IdentityFirewall, e).into_string();
            }
        };

        // ── S6: TOOL_EXECUTION (conditional) ───────────────────────────────
        let post_tool_output = if needs_tool {
            let t6 = StateTimer::enter(FsmState::S6ToolExecution);
            let tool_json = detect_tool_call(&firewalled_output).unwrap_or("").to_string();

            let result = self.tools.execute_tool_call(&tool_json).await;
            match result {
                Ok(tool_result) => {
                    t6.transition(FsmState::S7OutputSanitization);
                    // Append tool result to output for sanitization.
                    format!("{firewalled_output}\n[TOOL RESULT: {tool_result}]")
                }
                Err(e) => {
                    t6.fail(FsmState::SErr, &e);
                    cycle_timer.finish();
                    return fail_closed(FsmState::S6ToolExecution, e).into_string();
                }
            }
        } else {
            firewalled_output
        };

        // ── S7: OUTPUT_SANITIZATION ─────────────────────────────────────────
        let t = StateTimer::enter(FsmState::S7OutputSanitization);
        let final_output = match self.governance.sanitize_output(&post_tool_output) {
            Ok(v)  => { t.transition(FsmState::S8MemoryWrite); v }
            Err(e) => { t.fail(FsmState::SErr, &e); cycle_timer.finish(); return fail_closed(FsmState::S7OutputSanitization, e).into_string(); }
        };

        // ── S8: MEMORY_WRITE ────────────────────────────────────────────────
        let t = StateTimer::enter(FsmState::S8MemoryWrite);
        {
            let mem = self.memory.clone();
            let input_clone  = user_input.clone();
            let output_clone = final_output.clone();
            let handle = task::spawn_blocking(move || mem.persist_interaction(&input_clone, &output_clone));
            match handle.await
                .map_err(|e| JarviisError::Internal(format!("join error: {e}")))
                .and_then(|r| r)
            {
                Ok(_)  => { t.transition(FsmState::S9EmitResponse); }
                Err(e) => { t.fail(FsmState::SErr, &e); cycle_timer.finish(); return fail_closed(FsmState::S8MemoryWrite, e).into_string(); }
            }
        }

        // ── S9: EMIT_RESPONSE ───────────────────────────────────────────────
        let _t = StateTimer::enter(FsmState::S9EmitResponse);
        cycle_timer.finish();
        final_output
    }
}
