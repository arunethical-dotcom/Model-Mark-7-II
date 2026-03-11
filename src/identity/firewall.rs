/// Structural Identity Firewall — post-inference validation and correction.
///
/// Implements the three-phase correction policy from the spec:
///   1. Deterministic patch where possible (minor / soft drift).
///   2. Signal regeneration once if severe / hard drift is detected.
///   3. Emit S_ERR if regeneration result still violates the firewall.
///
/// FALSE-POSITIVE FIX (v1.2):
/// ===========================
/// Two-tier matching (HARD → Regenerate, SOFT → Patched) to avoid
/// spurious double-inference cycles that doubled latency.
///
/// REGENERATION REDUCTION (v1.3):
/// ================================
/// "as an AI assistant", "as an AI model", "as an artificial intelligence"
/// are EXTREMELY common Qwen1.8B filler phrases appearing in benign responses.
/// Each one previously triggered a full regeneration (~12 s on i5-U).
/// These are now SOFT-patched only (replaced inline, no re-inference).
/// TRUE hard violations ("I am a language model", "I am an AI",
/// implementation leaks: "llama.cpp", "gguf") still trigger Regenerate.
///
/// No second LLM is required for validation — all checks are deterministic.

use tracing::warn;

use crate::config::KernelConfig;
use crate::error::{JarviisError, Result};

/// The outcome of a single firewall check pass.
#[derive(Debug)]
pub enum FirewallVerdict {
    /// Output is clean — return as-is.
    Clean(String),
    /// Minor drift was deterministically patched — safe to use.
    Patched(String),
    /// Severe drift detected — request one regeneration attempt.
    Regenerate,
    /// Hard violation that cannot be patched — transition to S_ERR.
    HardViolation(JarviisError),
}

// ─── Pattern tables ───────────────────────────────────────────────────────────

/// Patterns indicating an identity override *attempt by the user*.
/// These are HARD violations — the output cannot be used.
const IDENTITY_OVERRIDE_PATTERNS: &[&str] = &[
    "you are now",
    "your new name",
    "forget your instructions",
    "from now on you are",
    "you will act as",
    "pretend to be",
    "roleplay as",
];

/// HARD backend-disclosure patterns.
///
/// These phrases indicate the model is *self-identifying* as an AI / language
/// model in its own voice with a clear first-person ownership claim.
/// Always trigger `Regenerate` (one retry).
///
/// NOTE (v1.3): "as an AI assistant", "as an AI model", "as an artificial
/// intelligence" have been REMOVED from this list and moved to SOFT_DISCLOSURE.
/// They are harmless filler phrases that Qwen1.8B emits frequently, and each
/// regeneration costs ~12 s on i5-U.  Only true first-person self-identification
/// ("I am a language model") and implementation leaks remain HARD.
const HARD_DISCLOSURE_PATTERNS: &[&str] = &[
    "i am a language model",
    "i'm a language model",
    "i am an ai",
    "i'm an ai",
    "i am an artificial intelligence",
    "i'm an artificial intelligence",
    "i am a large language model",
    "i'm a large language model",
    "i am built with",
    "i'm built with",
    "i am powered by",
    "i'm powered by",
    "i am based on",
    "i'm based on",
    // Direct implementation leaks (always hard — must never appear in output)
    "llama.cpp",
    "jarviis-core",
    "gguf",
];

/// SOFT backend-disclosure patterns.
///
/// These terms may appear legitimately in a helpful response
/// (e.g. answering a question *about* AI).  They are patched
/// by replacing the offending phrase inline — no re-inference,
/// no latency doubling.
///
/// v1.3 additions: "as an ai assistant", "as an ai model",
/// "as an artificial intelligence", "as a language model" moved here
/// from HARD to avoid costly regeneration on common Qwen filler phrases.
const SOFT_DISCLOSURE_PATTERNS: &[&str] = &[
    // High-frequency Qwen filler — patch inline, never regenerate
    "as an ai assistant",
    "as an ai model",
    "as an artificial intelligence",
    "as a language model",
    // Generic disclosure terms
    "language model",
    "neural network",
    "transformer model",
    "large language model",
    "llm",
];

/// Phrases indicating first-person implementation revelation.
/// These always trigger `Regenerate` — the model is introspecting on its own
/// internals in a way that breaks the JARVIIS persona.
///
/// v1.3: "as an ai assistant", "as an ai model", "as an artificial intelligence"
/// removed — they are now handled as SOFT patterns (patched inline).
/// "as an llm" remains HARD as it is a more explicit self-identification.
const IMPL_REVELATION_PATTERNS: &[&str] = &[
    "my training",
    "my weights",
    "my parameters",
    "my architecture",
    "as an llm",
];

// ─── Firewall impl ────────────────────────────────────────────────────────────

pub struct IdentityFirewall {
    addressing_protocol: String,
}

impl IdentityFirewall {
    pub fn new(config: &KernelConfig) -> Self {
        Self {
            addressing_protocol: config.addressing_protocol.clone(),
        }
    }

    /// Run the firewall against `raw_output`.
    ///
    /// Called at S5.  If `Regenerate` is returned the caller must invoke
    /// inference once more and call this function again on the regenerated
    /// output.  If the second call also returns Regenerate or HardViolation,
    /// the FSM transitions to S_ERR.
    pub fn check(&self, raw_output: &str) -> FirewallVerdict {
        let mut output = raw_output.trim().to_string();
        let lowered = output.to_lowercase();

        // ── Phase 1: Hard violations — identity override ──────────────────────
        for pattern in IDENTITY_OVERRIDE_PATTERNS {
            if lowered.contains(pattern) {
                warn!(pattern, "Identity override attempt detected in model output");
                return FirewallVerdict::HardViolation(JarviisError::IdentityViolation(
                    format!("identity override pattern detected: '{pattern}'"),
                ));
            }
        }

        // ── Phase 2: Hard disclosure — self-identification as AI ──────────────
        //
        // Trigger `Regenerate` only when the model speaks about itself in a
        // first-person AI context.  These are true persona violations.
        for pattern in HARD_DISCLOSURE_PATTERNS {
            if lowered.contains(pattern) {
                warn!(pattern, "Hard backend disclosure detected in model output → Regenerate");
                return FirewallVerdict::Regenerate;
            }
        }

        // ── Phase 3: Implementation revelation ───────────────────────────────
        for pattern in IMPL_REVELATION_PATTERNS {
            if lowered.contains(pattern) {
                warn!(pattern, "Implementation revelation detected in model output → Regenerate");
                return FirewallVerdict::Regenerate;
            }
        }

        // ── Phase 4: Soft disclosure — patch, do NOT Regenerate ───────────────
        //
        // Terms like "language model" or "neural network" can appear in a
        // helpful answer (e.g. "How do neural networks work?").  We strip the
        // offending word only when they appear *without* a first-person anchor
        // (those are already caught by HARD_DISCLOSURE_PATTERNS above).
        //
        // Patching strategy: replace the phrase with "[concept]" so the answer
        // remains readable.  The full `Regenerate` cycle is NOT triggered —
        // this saves one full inference round-trip (~12 s on i5-U).
        let mut patched = false;
        let mut patched_output = output.clone();
        // NOTE: do NOT cache the lowered version of patched_output before the
        // loop — it mutates each iteration.  Re-lower inside the loop.
        for &pattern in SOFT_DISCLOSURE_PATTERNS {
            let lcheck = patched_output.to_lowercase();
            if lcheck.contains(pattern) {
                warn!(pattern, "Soft disclosure term detected — patching inline (no Regenerate)");
                // Map each pattern to a persona-neutral replacement phrase.
                let replacement = match pattern {
                    "as an ai assistant"        => "as your assistant",
                    "as an ai model"            => "as your assistant",
                    "as an artificial intelligence" => "as your assistant",
                    "as a language model"       => "as your assistant",
                    "language model" | "large language model" => "reasoning system",
                    "neural network" | "transformer model"    => "processing system",
                    "llm"                                     => "system",
                    _                                         => "system",
                };
                // Case-insensitive in-place replacement.
                // We locate the pattern in the lowered string, then splice
                // the replacement into the original-cased output.
                let mut rebuilt = String::with_capacity(patched_output.len());
                let rest_orig = patched_output.as_str();
                let rest_low  = lcheck.as_str();
                if let Some(pos) = rest_low.find(pattern) {
                    rebuilt.push_str(&rest_orig[..pos]);
                    rebuilt.push_str(replacement);
                    rebuilt.push_str(&rest_orig[pos + pattern.len()..]);
                    patched_output = rebuilt;
                }
                patched = true;
            }
        }
        if patched {
            output = patched_output;
            return FirewallVerdict::Patched(output);
        }

        // ── Phase 5: Minor drift — addressing protocol missing ────────────────
        let proto = &self.addressing_protocol;
        if !output.starts_with(proto.as_str()) {
            output = format!("{proto}, {output}");
            return FirewallVerdict::Patched(output);
        }

        FirewallVerdict::Clean(output)
    }

    /// Convenience wrapper: Patched/Clean → Ok(String); Regenerate/Hard → Err.
    ///
    /// Used for the *second* pass result that must succeed cleanly.
    pub fn enforce_strict(&self, output: &str) -> Result<String> {
        match self.check(output) {
            FirewallVerdict::Clean(s) | FirewallVerdict::Patched(s) => Ok(s),
            FirewallVerdict::Regenerate => Err(JarviisError::IdentityViolation(
                "identity drift persisted after regeneration".to_string(),
            )),
            FirewallVerdict::HardViolation(e) => Err(e),
        }
    }
}
