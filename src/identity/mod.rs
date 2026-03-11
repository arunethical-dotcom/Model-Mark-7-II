pub mod firewall;
pub mod injector;

use crate::config::KernelConfig;
use crate::error::Result;

pub use firewall::{FirewallVerdict, IdentityFirewall};
pub use injector::IdentityInjector;

/// The combined identity subsystem exposed to the FSM.
///
/// Wraps the injector (prompt assembly) and the firewall (post-inference
/// validation) behind a single owned struct for ease of Arc<> sharing.
pub struct IdentitySubsystem {
    injector: IdentityInjector,
    firewall: IdentityFirewall,
}

impl IdentitySubsystem {
    pub fn new(config: &KernelConfig) -> Self {
        Self {
            injector: IdentityInjector::new(config),
            firewall: IdentityFirewall::new(config),
        }
    }

    /// Assemble the full inference prompt (S3).
    pub fn assemble_prompt(&self, user_input: &str, memory_context: &str) -> String {
        self.injector.assemble_prompt(user_input, memory_context)
    }

    /// Run the firewall check (S5) — returns a `FirewallVerdict`.
    pub fn check_firewall(&self, raw_output: &str) -> FirewallVerdict {
        self.firewall.check(raw_output)
    }

    /// Strict enforcement used for the *second* regeneration pass.
    /// Clean/Patched → Ok(); anything else → Err.
    pub fn enforce_strict(&self, output: &str) -> Result<String> {
        self.firewall.enforce_strict(output)
    }
}
