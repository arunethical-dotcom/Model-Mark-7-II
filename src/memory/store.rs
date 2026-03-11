/// Memory Store — SQLite-backed episodic memory I/O.
///
/// Implements:
///   - Schema initialisation with Class A user-profile seed
///   - Bounded retrieval with reinforcement (usage_boost update on access)
///   - Hard token budget enforcement (drop lowest-ranked entries)
///   - Interaction persistence as Class D ephemeral entries

use rusqlite::{params, Connection};
use tracing::{debug, info};

use crate::config::KernelConfig;
use crate::error::{JarviisError, Result};
use crate::memory::scoring::{now_secs, reinforce, MemoryClass, MemoryEntry, USAGE_BOOST_CAP};

pub struct MemoryStore {
    db_path: String,
    max_retrieval_entries: usize,
    reinforcement_factor: f64,
    #[allow(dead_code)]
    max_memory_tokens: usize,
}

impl MemoryStore {
    pub fn new(config: &KernelConfig) -> Result<Self> {
        let store = Self {
            db_path: config.db_path.clone(),
            max_retrieval_entries: config.max_retrieval_entries,
            reinforcement_factor: config.reinforcement_factor,
            max_memory_tokens: config.max_memory_tokens,
        };
        store.init_schema()?;
        store.seed_class_a_profile(config)?;
        Ok(store)
    }

    fn open(&self) -> Result<Connection> {
        Connection::open(&self.db_path)
            .map_err(|e| JarviisError::Memory(format!("failed to open sqlite: {e}")))
    }

    /// Create the memories table if it doesn't exist.
    fn init_schema(&self) -> Result<()> {
        let conn = self.open()?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS memories (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                class         TEXT    NOT NULL,
                base_score    REAL    NOT NULL,
                usage_boost   REAL    NOT NULL DEFAULT 0.0,
                decay_rate    REAL    NOT NULL,
                created_at    INTEGER NOT NULL,
                last_used_at  INTEGER NOT NULL,
                content       TEXT    NOT NULL
            );",
        )
        .map_err(|e| JarviisError::Memory(format!("schema init failed: {e}")))?;
        Ok(())
    }

    /// On first run, insert the immutable Class A user profile seed entry
    /// so the identity is always available in memory retrieval contexts.
    fn seed_class_a_profile(&self, config: &KernelConfig) -> Result<()> {
        let conn = self.open()?;
        let count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM memories WHERE class = 'A'",
                [],
                |row| row.get(0),
            )
            .map_err(|e| JarviisError::Memory(format!("seed check failed: {e}")))?;

        if count == 0 {
            let now = now_secs();
            let content = format!(
                "Primary user: {}. Addressing protocol: \"{}\". Agent: {} — identity immutable.",
                config.primary_user, config.addressing_protocol, config.agent_name
            );
            conn.execute(
                "INSERT INTO memories (class, base_score, usage_boost, decay_rate, created_at, last_used_at, content)
                 VALUES ('A', 1.0, 0.0, 0.0, ?1, ?2, ?3)",
                params![now, now, content],
            )
            .map_err(|e| JarviisError::Memory(format!("seed insert failed: {e}")))?;
            info!("Seeded Class A user profile memory entry");
        }

        Ok(())
    }

    /// Retrieve up to `max_retrieval_entries` high-scoring memories within the
    /// hard token budget. Each retrieved entry has its `usage_boost` incremented
    /// (reinforcement logic). Class A entries are never removed by budget pruning.
    pub fn retrieve_relevant(&self, _query: &str, max_tokens: usize) -> Result<Vec<MemoryEntry>> {
        let conn = self.open()?;

        let mut stmt = conn
            .prepare(
                "SELECT id, class, base_score, usage_boost, decay_rate,
                        created_at, last_used_at, content
                 FROM memories",
            )
            .map_err(|e| JarviisError::Memory(format!("prepare failed: {e}")))?;

        let all: Vec<MemoryEntry> = stmt
            .query_map([], |row| {
                let class_str: String = row.get(1)?;
                let class = MemoryClass::from_str(&class_str).unwrap_or(MemoryClass::D);
                Ok(MemoryEntry {
                    id: row.get(0)?,
                    class,
                    base_score: row.get(2)?,
                    usage_boost: row.get(3)?,
                    decay_rate: row.get(4)?,
                    created_at: row.get(5)?,
                    last_used_at: row.get(6)?,
                    content: row.get(7)?,
                })
            })
            .map_err(|e| JarviisError::Memory(format!("query failed: {e}")))?
            .filter_map(|r| r.ok())
            .collect();

        // Sort by effective score descending.
        let now = now_secs();
        let mut sorted = all;
        sorted.sort_by(|a, b| {
            b.effective_score(now)
                .partial_cmp(&a.effective_score(now))
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        // Hard token budget: approximate 4 characters per token.
        let char_budget = max_tokens.saturating_mul(4);
        let mut result = Vec::new();
        let mut used_chars = 0usize;

        for entry in sorted.into_iter().take(self.max_retrieval_entries) {
            let len = entry.content.chars().count();
            if used_chars + len > char_budget {
                break;
            }
            used_chars += len;
            result.push(entry);
        }

        debug!(
            entries = result.len(),
            used_chars,
            char_budget,
            "Memory retrieval complete"
        );

        // Reinforcement: increment usage_boost for each retrieved entry.
        for entry in &result {
            let new_boost = reinforce(entry.usage_boost, self.reinforcement_factor);
            // Only write if boost actually changed (cap protection).
            if (new_boost - entry.usage_boost).abs() > 1e-9 {
                let _ = conn.execute(
                    "UPDATE memories SET usage_boost = ?1, last_used_at = ?2 WHERE id = ?3",
                    params![new_boost.min(USAGE_BOOST_CAP), now, entry.id],
                );
            }
        }

        Ok(result)
    }

    /// Persist a completed interaction as a Class D ephemeral memory entry.
    /// Only the model response is stored (not the raw user input).
    pub fn persist_interaction(&self, _user_input: &str, response: &str) -> Result<()> {
        let conn = self.open()?;
        let class = MemoryClass::D;
        let now = now_secs();

        conn.execute(
            "INSERT INTO memories (class, base_score, usage_boost, decay_rate,
                                   created_at, last_used_at, content)
             VALUES (?1, ?2, 0.0, ?3, ?4, ?5, ?6)",
            params![
                class.as_str(),
                class.base_score(),
                class.decay_rate(),
                now,
                now,
                response,
            ],
        )
        .map_err(|e| JarviisError::Memory(format!("persist failed: {e}")))?;

        Ok(())
    }
}
