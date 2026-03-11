/// Kernel-wide configuration.
///
/// All fields have hardware-aware defaults targeting:
///   Intel i5 U-Series (low-power), 8 GB RAM, CPU-only inference.
///
/// KEY DEFAULTS (i5-U / 8 GB optimised, v1.3):
///   n_ctx = 1024   — KV cache ≈ 192 MB (was 768 MB at 4096)
///   n_batch = 128  — balanced chunk size for i5-U throughput
///   n_ubatch = 128 — matches n_batch; avoids internal sub-splitting overhead
///   n_threads = auto — detected via available_parallelism(), capped 2–8
///   flash_attn disabled — always off on CPU (no API field; handled in llama.rs)

#[derive(Debug, Clone)]
pub struct KernelConfig {
    // ── Memory subsystem ──────────────────────────────────────────────────
    /// Hard token budget for memory injection.
    /// Reduced to 256 to fit the tighter 1024-token context window.
    pub max_memory_tokens: usize,
    /// Maximum number of memory entries retrieved per cycle.
    pub max_retrieval_entries: usize,
    /// Reinforcement increment applied to retrieved entries' usage_boost.
    pub reinforcement_factor: f64,
    /// Path to the SQLite memory database file.
    pub db_path: String,

    // ── Inference subsystem ───────────────────────────────────────────────
    /// Wall-clock timeout for a single inference call (seconds).
    /// Set to 12 s to enforce the FSM latency cap on i5-U hardware.
    pub inference_timeout_secs: u64,
    /// Path to the GGUF model file (Q4_K_M recommended).
    pub model_path: String,
    /// CPU thread count for llama.cpp inference.
    pub n_threads: u32,
    /// Context window size in tokens.
    /// Reduced to 1024 for i5-U / 8 GB RAM: KV cache drops from ~768 MB to ~192 MB.
    pub n_ctx: u32,
    /// Prompt-processing batch size for llama.cpp (n_batch).
    /// 128 balances throughput and compute-graph size on 8 GB RAM.
    pub n_batch: u32,
    /// Micro-batch size within each llama.cpp decode call (n_ubatch).
    /// Must be ≤ n_batch. Equal to n_batch (128) avoids internal sub-splitting.
    pub n_ubatch: u32,
    // NOTE: flash_attn removed — always disabled; constant passed directly
    // in llama.rs via LLAMA_FLASH_ATTN_DISABLED to avoid the bool→c_int
    // type mismatch that caused the compile error in v1.2.

    // ── Tool subsystem ────────────────────────────────────────────────────
    /// Wall-clock timeout for each Python tool invocation (seconds).
    pub tool_timeout_secs: u64,

    // ── Governance ────────────────────────────────────────────────────────
    /// Maximum allowed input length in characters (proxy for token budget).
    /// Set to 4 chars/token × n_ctx tokens.
    pub max_input_chars: usize,
    /// When `true`, entropy anomalies are logged but do not reject input
    /// unless combined with another violation (non-destructive mode).
    pub entropy_log_only: bool,

    // ── Identity constants ────────────────────────────────────────────────
    pub agent_name:          String,
    pub primary_user:        String,
    pub addressing_protocol: String,
}

impl Default for KernelConfig {
    fn default() -> Self {
        // Auto-detect physical CPU cores for n_threads.
        // Capped between 2 (minimum useful) and 8 (safe ceiling on i5-U).
        // Falls back to 4 if detection is unavailable.
        let auto_threads = std::thread::available_parallelism()
            .map(|n| n.get() as u32)
            .unwrap_or(4)
            .clamp(2, 8);

        Self {
            // Memory — tight budget to fit 1024-token context window
            max_memory_tokens:    256,
            max_retrieval_entries: 2,
            reinforcement_factor:  0.1,
            db_path:              "jarviis_memory.sqlite".to_string(),
            // Inference — optimised for Intel i5-U / 8 GB RAM (v1.3)
            inference_timeout_secs: 30,   // raised from 12 s; first inference may be slow
            model_path:  "models/qwen1_5-1_8b-chat-q4_k_m.gguf".to_string(),
            n_threads:   auto_threads,     // auto-detected physical cores, capped 2–8
            n_ctx:       1024,             // was 4096; KV cache: ~192 MB vs ~768 MB
            n_batch:     128,              // balanced chunk size for i5-U throughput
            n_ubatch:    128,              // equal to n_batch; no internal sub-splitting
            // flash_attn removed — always disabled; see llama.rs LLAMA_FLASH_ATTN_DISABLED
            // Tools
            tool_timeout_secs: 30,
            // Governance — scaled to n_ctx
            max_input_chars:  4 * 1024,
            entropy_log_only: true,
            // Identity (immutable constants)
            agent_name:          "JARVIIS".to_string(),
            primary_user:        "Arun".to_string(),
            addressing_protocol: "Sir".to_string(),
        }
    }
}
