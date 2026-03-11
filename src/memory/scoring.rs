/// Memory Importance Scoring — reinforced decay formula.
///
/// Implements:
///   effective_score = (base_score + usage_boost) × e^(−decay_rate × age_hours)
///
/// Memory classes:
///   A — Core User Profile   (score 1.0, no decay)
///   B — Long-Term Strategic (score 0.8, slow decay)
///   C — Operational Context (score 0.5, medium decay)
///   D — Ephemeral           (score 0.2, fast decay)

use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MemoryClass {
    A, // Core User Profile — permanent
    B, // Long-Term Strategic
    C, // Operational Context
    D, // Ephemeral Interaction
}

impl MemoryClass {
    pub fn base_score(self) -> f64 {
        match self {
            MemoryClass::A => 1.0,
            MemoryClass::B => 0.8,
            MemoryClass::C => 0.5,
            MemoryClass::D => 0.2,
        }
    }

    /// Decay rate (per hour). Class A never decays.
    pub fn decay_rate(self) -> f64 {
        match self {
            MemoryClass::A => 0.0,
            MemoryClass::B => 0.02,
            MemoryClass::C => 0.05,
            MemoryClass::D => 0.10,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            MemoryClass::A => "A",
            MemoryClass::B => "B",
            MemoryClass::C => "C",
            MemoryClass::D => "D",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "A" => Some(MemoryClass::A),
            "B" => Some(MemoryClass::B),
            "C" => Some(MemoryClass::C),
            "D" => Some(MemoryClass::D),
            _ => None,
        }
    }
}

/// A single memory entry loaded from SQLite.
#[derive(Debug, Clone)]
pub struct MemoryEntry {
    pub id: i64,
    pub class: MemoryClass,
    pub base_score: f64,
    pub usage_boost: f64,
    pub decay_rate: f64,
    pub created_at: i64,  // Unix seconds
    pub last_used_at: i64,
    pub content: String,
}

impl MemoryEntry {
    /// Compute the effective importance score at the given Unix timestamp.
    ///
    /// effective_score = (base_score + usage_boost) × e^(−decay_rate × age_hours)
    pub fn effective_score(&self, now_secs: i64) -> f64 {
        let age_secs = (now_secs - self.created_at).max(0) as f64;
        let age_hours = age_secs / 3600.0;
        let factor = (-self.decay_rate * age_hours).exp();
        (self.base_score + self.usage_boost).max(0.0) * factor
    }
}

/// Return the current Unix timestamp in seconds.
pub fn now_secs() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64
}

/// Maximum cap on usage_boost to prevent runaway dominance by a single entry.
pub const USAGE_BOOST_CAP: f64 = 2.0;

/// Apply a reinforcement increment to `current_boost`, respecting the cap.
pub fn reinforce(current_boost: f64, reinforcement_factor: f64) -> f64 {
    (current_boost + reinforcement_factor).min(USAGE_BOOST_CAP)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn class_a_no_decay() {
        let entry = MemoryEntry {
            id: 1,
            class: MemoryClass::A,
            base_score: MemoryClass::A.base_score(),
            usage_boost: 0.0,
            decay_rate: MemoryClass::A.decay_rate(),
            created_at: 0,
            last_used_at: 0,
            content: "user is Arun".to_string(),
        };
        let now = 365 * 24 * 3600; // one year later
        assert!((entry.effective_score(now) - 1.0).abs() < 1e-9);
    }

    #[test]
    fn class_d_decays() {
        let entry = MemoryEntry {
            id: 2,
            class: MemoryClass::D,
            base_score: MemoryClass::D.base_score(),
            usage_boost: 0.0,
            decay_rate: MemoryClass::D.decay_rate(),
            created_at: 0,
            last_used_at: 0,
            content: "temporary note".to_string(),
        };
        let after_1h = 3600i64;
        let score = entry.effective_score(after_1h);
        assert!(score < MemoryClass::D.base_score()); // must have decayed
    }

    #[test]
    fn reinforce_capped() {
        let boosted = reinforce(1.9, 0.5); // would exceed cap of 2.0
        assert!((boosted - USAGE_BOOST_CAP).abs() < 1e-9);
    }
}
