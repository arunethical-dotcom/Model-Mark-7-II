pub mod scoring;
pub mod store;

use crate::config::KernelConfig;
use crate::error::Result;

pub use scoring::{MemoryClass, MemoryEntry};
pub use store::MemoryStore;

/// Combined memory subsystem — store + scoring exposed to the FSM.
pub struct MemorySubsystem {
    store: MemoryStore,
}

impl MemorySubsystem {
    pub fn new(config: &KernelConfig) -> Result<Self> {
        Ok(Self {
            store: MemoryStore::new(config)?,
        })
    }

    /// Retrieve relevant memories within the hard token budget (S2).
    pub fn retrieve_relevant(&self, query: &str, max_tokens: usize) -> Result<Vec<MemoryEntry>> {
        self.store.retrieve_relevant(query, max_tokens)
    }

    /// Persist a completed interaction as Class D ephemeral memory (S8).
    pub fn persist_interaction(&self, user_input: &str, response: &str) -> Result<()> {
        self.store.persist_interaction(user_input, response)
    }
}
