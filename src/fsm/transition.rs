/// Transition helpers for the JARVIIS FSM kernel.
///
/// All transitions are logged with structured tracing entries so that
/// FSM cycle times can be measured for latency monitoring against the
/// ≤12 second hardware cap.

use std::time::{Duration, Instant};

use tracing::{error, info, warn};

use crate::error::JarviisError;
use crate::fsm::state::FsmState;

/// A timing guard that records when a state was entered and logs the
/// elapsed time when the transition to the next state is performed.
pub struct StateTimer {
    state: FsmState,
    entered_at: Instant,
}

impl StateTimer {
    /// Begin timing the given state.
    pub fn enter(state: FsmState) -> Self {
        info!(state = %state, "FSM enter state");
        Self {
            state,
            entered_at: Instant::now(),
        }
    }

    /// Record a normal transition to `next` and return the elapsed duration.
    pub fn transition(self, next: FsmState) -> Duration {
        let elapsed = self.entered_at.elapsed();
        info!(
            from  = %self.state,
            to    = %next,
            elapsed_ms = elapsed.as_millis(),
            "FSM transition"
        );
        elapsed
    }

    /// Record a transition to S_ERR (failure path) and return elapsed duration.
    pub fn fail(self, next: FsmState, err: &JarviisError) -> Duration {
        let elapsed = self.entered_at.elapsed();
        error!(
            from       = %self.state,
            to         = %next,
            elapsed_ms = elapsed.as_millis(),
            error      = %err,
            "FSM S_ERR transition — failing closed"
        );
        elapsed
    }
}

/// Aggregate timing across the full FSM cycle (S0 → S9 or S_ERR).
pub struct CycleTimer {
    started_at: Instant,
}

impl CycleTimer {
    pub fn start() -> Self {
        Self {
            started_at: Instant::now(),
        }
    }

    /// Log the total cycle time and warn if it exceeds the hardware latency cap.
    pub fn finish(&self) {
        let total = self.started_at.elapsed();
        let ms = total.as_millis();
        if ms > 12_000 {
            warn!(
                total_ms = ms,
                cap_ms   = 12_000,
                "FSM cycle exceeded ≤12 s hardware latency cap"
            );
        } else {
            info!(total_ms = ms, "FSM cycle complete");
        }
    }
}

/// Detect a structured tool call marker in model output.
///
/// Expected format injected by the prompt template:
///   TOOL_CALL: {"name": "<tool>", "args": {...}}
///
/// Returns `Some(raw_json_str)` if a tool call is present.
pub fn detect_tool_call(output: &str) -> Option<&str> {
    const MARKER: &str = "TOOL_CALL:";
    output
        .lines()
        .find_map(|line| {
            let trimmed = line.trim();
            if trimmed.starts_with(MARKER) {
                Some(trimmed[MARKER.len()..].trim())
            } else {
                None
            }
        })
}
