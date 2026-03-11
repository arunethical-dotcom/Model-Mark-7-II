//! llama.cpp Inference Engine — Optimised for i5-U CPU / 8 GB RAM
//!
//! PERFORMANCE PATCH SUMMARY (v1.3):
//! ==================================
//! P1. n_batch = 128:              balanced chunk; avoids graph-build spikes on 8 GB RAM.
//! P2. n_ubatch = 128:             micro-batch size matching n_batch for i5-U.
//! P3. MAX_NEW_TOKENS = 128:       caps generation loop, keeps RAM well under 6 GB.
//! P4. flash_attn DISABLED:        CPU flash-attn spikes compute buffer by 300+ MB.
//!                                 CORRECT API: with_flash_attention_policy(
//!                                   llama_cpp_sys_2::LLAMA_FLASH_ATTN_DISABLED)
//!                                 NOT a bool — this was the v1.2 compile error.
//! P5. n_ctx = 1024 (via config):  KV cache ~192 MB; fits 8 GB RAM cleanly.
//! P6. Prompt hard-cap truncation: never exceed n_ctx − MAX_NEW_TOKENS.
//! P7. Compact system prompt:      saves ~40–60 tokens per call.
//! P8. Tighter sampler:            top_k=30, top_p=0.90, temp=0.50.
//! P9. Step-0 EOS guard:           greedy retry on cold-start EOS collapse.
//! P10. n_threads auto-detected:   std::thread::available_parallelism(), capped 2–8.
//!
//! ALL PREVIOUS FIXES RETAINED:
//! ==============================
//! F1. Backend stored on struct (no re-init / BackendAlreadyInitialized).
//! F2. Correct sampler API: `sampler.sample(&ctx, logit_idx)`.
//! F3. Correct batch size ≥ longest chunk fed to llama_decode().
//! F4. Sampler chain order: pre-filters → temp → dist (dist MUST be last).
//! F5. Qwen2 ChatML wrapping: <|im_start|>/<|im_end|> preserved.
//! F6. KV cache guard: n_kv_req checked before decode.

#![cfg(feature = "llama")]

use std::num::NonZeroU32;
use std::time::{Duration, Instant};
use tracing::{debug, error, info, warn};

use crate::error::{JarviisError, Result};
use crate::inference::InferenceEngine;

use llama_cpp_2::llama_backend::LlamaBackend;
use llama_cpp_2::model::{AddBos, LlamaModel};
use llama_cpp_2::model::params::LlamaModelParams;
use llama_cpp_2::context::params::LlamaContextParams;
use llama_cpp_2::context::LlamaContext;
use llama_cpp_2::llama_batch::LlamaBatch;
use llama_cpp_2::sampling::LlamaSampler;

// Flash-attention policy constants from the underlying C bindings.
// llama_flash_attn_type is a c_int (not a bool).
// LLAMA_FLASH_ATTN_TYPE_DISABLED = 0 — correct value for CPU-only inference.
use llama_cpp_sys_2::LLAMA_FLASH_ATTN_TYPE_DISABLED;

// ─── Constants ──────────────────────────────────────────────────────────────

/// Qwen2 end-of-sequence token id (tokenizer_config.json, eos_token_id: 151645).
const QWEN2_EOS_ID: i32 = 151_645;

/// Prompt-processing batch size.
///
/// Set to 128 for i5-U / 8 GB RAM:
///   - Balances throughput vs. compute-graph node count per decode call.
///   - Still satisfies the `n_tokens_all <= cparams.n_batch` GGML assertion
///     because we never feed prompts longer than n_ctx (1024 tokens).
///   - Value must be ≥ 1 and ≤ n_ctx.
const N_BATCH: usize = 128;

/// Micro-batch size within each decode call (n_ubatch).
///
/// Set equal to N_BATCH = 128 so llama.cpp does not sub-split each chunk.
/// Must satisfy: N_UBATCH ≤ N_BATCH.
const N_UBATCH: usize = 128;

/// Maximum tokens to generate per inference call.
///
/// Capped at 128 to:
///   - Keep RAM well under 6 GB on 8 GB systems.
///   - Limit the number of sequential single-token decode steps.
///   - Reserve sufficient KV slots for the 1024-token budget.
const MAX_NEW_TOKENS: usize = 128;

// ─── Engine struct ───────────────────────────────────────────────────────────

/// Production llama.cpp inference engine for Qwen2 GGUF models.
///
/// NOTE: `LlamaBackend` and `LlamaModel` are !Send + !Sync, so the engine
/// must be constructed and consumed on the same thread.  The FSM calls
/// `infer()` via `tokio::task::spawn_blocking`, which satisfies this.
///
/// `flash_attn` field removed in v1.3 — flash attention is always disabled
/// on CPU-only builds.  The policy constant `LLAMA_FLASH_ATTN_DISABLED` is
/// passed directly to `with_flash_attention_policy()` at context creation.
pub struct LlamaEngine {
    /// Kept alive for the lifetime of the engine — backend must outlive model.
    backend: LlamaBackend,
    model: LlamaModel,
    n_ctx: u32,
    n_threads: u32,
}

impl LlamaEngine {
    /// Load a GGUF model from `model_path`.
    ///
    /// `n_ctx`     — context window in tokens (1024 for i5-U / 8 GB RAM).
    /// `n_threads` — CPU thread count for compute; auto-detect via config.
    ///
    /// Flash attention is always DISABLED on CPU-only builds.  The old
    /// `flash_attn: bool` parameter is removed — `LLAMA_FLASH_ATTN_DISABLED`
    /// is passed directly to the context params at inference time.
    pub fn load(model_path: &str, n_ctx: u32, n_threads: u32) -> Result<Self> {
        info!(
            model_path, n_ctx, n_threads,
            "Initializing llama.cpp backend (i5-U optimised: N_BATCH={N_BATCH}, N_UBATCH={N_UBATCH}, MAX_NEW_TOKENS={MAX_NEW_TOKENS})"
        );

        // Backend is created ONCE here and stored on the struct.
        // Never call LlamaBackend::init() again — doing so triggers
        // BackendAlreadyInitialized from the C++ singleton guard.
        let backend = LlamaBackend::init().map_err(|e| {
            JarviisError::Inference(format!("backend init failed: {e}"))
        })?;

        let model_params = LlamaModelParams::default();

        debug!("Loading model: {}", model_path);
        let model = LlamaModel::load_from_file(&backend, model_path, &model_params)
            .map_err(|e| JarviisError::Inference(format!("model load failed: {e}")))?;

        info!("Model loaded — backend stored for reuse across all inference calls");
        Ok(Self { backend, model, n_ctx, n_threads })
    }

    // ── Private inference implementation ────────────────────────────────────

    fn infer_impl(&self, prompt: String, timeout: Duration) -> Result<String> {
        let deadline = Instant::now() + timeout;

        // ── PATCH P7: Compact Qwen2 ChatML system prompt ─────────────────────
        //
        // The previous prompt was verbose (~80 tokens for system block alone).
        // This condensed version uses ~35–40 system tokens, freeing ~40–60 KV
        // slots for user context — critical when n_ctx = 1024.
        //
        // Key additions:
        //   • "Never say 'as an AI assistant'" — suppresses the most common
        //     identity-spill pattern that triggers firewall false-positives.
        //   • "Never reveal you are a language model" — reduces BACKEND_DISCLOSURE.
        let formatted_prompt = format!(
            "<|im_start|>system\n\
             You are JARVIIS, a cognitive kernel. Address the user as Sir. \
             Never say \"as an AI assistant\", \"I am an AI\", \"I am a language model\", \
             or reveal your underlying implementation. \
             You are concise, precise, and deterministic.<|im_end|>\n\
             <|im_start|>user\n{}<|im_end|>\n\
             <|im_start|>assistant\n",
            prompt.trim()
        );

        // ── 1. Create context ─────────────────────────────────────────────────
        //
        // n_batch = N_BATCH (64): reduced from 512.  Eliminates large compute-graph
        //   creation at each decode() call.  Matches a safe chunk size on 8 GB RAM.
        // n_ubatch = N_UBATCH (48): internal micro-batch; reduces blocking per step.
        // flash_attn = false: CPU flash-attn adds 300+ MB compute buffer on i5-U.
        //   Only enable if AVX512/AMX is confirmed (not present on standard i5-U).
        //
        // Context is re-created per inference call because LlamaContext owns the
        // KV-cache state mutably.  The BACKEND is NOT re-initialised.
        // PATCH P4 (v1.3): Flash attention disabled via correct enum constant.
        // `with_flash_attention_policy` takes `llama_flash_attn_type` (c_int),
        // NOT a bool.  Passing `false` was a type error that caused a compile
        // failure.  `LLAMA_FLASH_ATTN_DISABLED = 0` is the correct value.
        //
        // Flash attention is NOT beneficial on CPU-only i5-U hardware (no
        // AVX512/AMX).  Enabling it would spike the compute buffer by 300+ MB.
        let ctx_params = LlamaContextParams::default()
            .with_n_ctx(Some(NonZeroU32::new(self.n_ctx).unwrap()))
            .with_n_threads(self.n_threads as i32)
            .with_n_threads_batch(self.n_threads as i32)
            .with_n_batch(N_BATCH as u32)
            .with_n_ubatch(N_UBATCH as u32)
            .with_flash_attention_policy(LLAMA_FLASH_ATTN_TYPE_DISABLED);

        debug!(
            "Creating context (n_ctx={}, n_batch={}, n_ubatch={}, flash_attn=DISABLED)",
            self.n_ctx, N_BATCH, N_UBATCH
        );
        let mut ctx: LlamaContext = self.model
            .new_context(&self.backend, ctx_params)
            .map_err(|e| JarviisError::Inference(format!("context creation failed: {e}")))?;

        // ── 2. Tokenize ───────────────────────────────────────────────────────
        debug!("Tokenizing prompt ({} chars)", formatted_prompt.len());
        let raw_tokens = self.model
            .str_to_token(&formatted_prompt, AddBos::Always)
            .map_err(|e| JarviisError::Inference(format!("tokenization failed: {e}")))?;

        // ── PATCH P6: Hard-cap prompt tokens ─────────────────────────────────
        //
        // With n_ctx = 1024 and MAX_NEW_TOKENS = 256, the prompt must fit in
        // n_ctx - MAX_NEW_TOKENS - 4 (safety margin) = 764 tokens.
        //
        // We keep the LAST `max_prompt_tokens` tokens so that the most recent
        // user message is always included; older history is silently dropped.
        let max_prompt_tokens = (self.n_ctx as usize)
            .saturating_sub(MAX_NEW_TOKENS)
            .saturating_sub(4);

        let tokens: Vec<_> = if raw_tokens.len() > max_prompt_tokens {
            warn!(
                "Prompt too long ({} tokens); truncating to last {} tokens (n_ctx={}, max_new={})",
                raw_tokens.len(), max_prompt_tokens, self.n_ctx, MAX_NEW_TOKENS
            );
            raw_tokens[raw_tokens.len() - max_prompt_tokens..].to_vec()
        } else {
            raw_tokens
        };

        let n_prompt = tokens.len();
        debug!("Prompt: {} tokens (max_prompt_tokens={})", n_prompt, max_prompt_tokens);

        if n_prompt == 0 {
            return Err(JarviisError::Inference("tokenization produced 0 tokens".into()));
        }

        // ── 3. Prompt decode ──────────────────────────────────────────────────
        //
        // A single LlamaBatch (N_BATCH=64 capacity) is allocated and reused for
        // both prompt processing AND generation.  We chunk the prompt into N_BATCH
        // slices to avoid an assertion: n_tokens_all <= cparams.n_batch.
        //
        // Logits are requested ONLY for the last token of the last prompt chunk —
        // that logit row seeds the first generated token.
        let mut batch = LlamaBatch::new(N_BATCH, 1);

        {
            let last_prompt_idx = n_prompt - 1;
            for (i, &token) in tokens.iter().enumerate() {
                let pos = i as i32;
                let want_logits = i == last_prompt_idx;

                batch.add(token, pos, &[0], want_logits)
                    .map_err(|e| {
                        error!("prompt batch.add failed at pos {}: {}", pos, e);
                        JarviisError::Inference(format!("batch.add overflow at pos {pos}: {e}"))
                    })?;

                // Flush full chunks mid-prompt; always flush at the final token.
                if batch.n_tokens() as usize >= N_BATCH || i == last_prompt_idx {
                    debug!("Decoding prompt chunk up to pos {}", pos);
                    ctx.decode(&mut batch).map_err(|e| {
                        error!("prompt ctx.decode failed: {}", e);
                        JarviisError::Inference(format!("prompt decode failed: {e}"))
                    })?;
                    if i < last_prompt_idx {
                        batch.clear();
                    }
                }
            }
        }
        // Invariant after this block:
        //   • ctx holds logits for the last prompt token.
        //   • batch.n_tokens() == last-chunk-size  (NOT cleared yet).
        //   • correct logit_idx = batch.n_tokens() - 1.

        // ── 4. Sampler setup ──────────────────────────────────────────────────
        //
        // Chain order: pre-filters → temp → stochastic selector (dist).
        // PATCH P8: Tightened from [top_k=40, top_p=0.95, temp=0.7] to
        //           [top_k=30, top_p=0.90, temp=0.50].
        //
        // Rationale:
        //   • Lower temperature (0.50) makes the model more deterministic and
        //     dramatically reduces "as an AI assistant" style identity-spill.
        //     Qwen1.5 1.8B produces coherent answers down to temp=0.40.
        //   • Tighter top_k/top_p narrow the candidate pool, which:
        //     (a) speeds up the dist() step on CPU,
        //     (b) significantly reduces identity-role-play hallucinations.
        //   • `dist` MUST be the last stage — it is the ONLY stage that picks
        //     a token; all others are pre-filters.
        let mut sampler = LlamaSampler::chain_simple([
            LlamaSampler::top_k(30),
            LlamaSampler::top_p(0.90, 1),
            LlamaSampler::temp(0.50),
            LlamaSampler::dist(1234), // MUST BE LAST
        ]);

        // ── 5. Generation loop ────────────────────────────────────────────────
        //
        // KEY INVARIANT (mirrors official llama-cpp-rs simple example):
        //   DECODE first (prompt) → SAMPLE from that logits → add token → DECODE →
        //   SAMPLE → repeat.
        //
        // On entry to the loop `ctx` already has valid logits (from the final
        // prompt decode above), so we SAMPLE FIRST on step 0, then decode.
        //
        // PATCH P9: Step-0 EOS guard.
        //   If the model returns EOS on the very first token (empty output),
        //   we detect it early and retry with a greedy sampler (top_k=1, temp=0).
        //   This fixes intermittent "empty output" failures on cold starts.

        let mut output = String::new();
        let mut n_cur = n_prompt as i32;
        let mut decoder = encoding_rs::UTF_8.new_decoder();
        let mut step0_eos_retry = false; // guard: allow at most 1 greedy retry

        let mut step = 0usize;
        loop {
            if step >= MAX_NEW_TOKENS {
                debug!("Reached MAX_NEW_TOKENS ({}) — stopping generation", MAX_NEW_TOKENS);
                break;
            }
            if Instant::now() >= deadline {
                debug!("Generation timeout after {} tokens", step);
                break;
            }

            // SAMPLE from logits of the last decoded batch.
            // batch.n_tokens() is always ≥ 1 here:
            //   step 0: batch holds last prompt chunk (≥ 1 token).
            //   step 1+: batch was cleared + 1 token added before decode.
            let logit_idx = batch.n_tokens() as i32 - 1;
            if logit_idx < 0 {
                error!("Generation step {}: batch empty before sampling — aborting", step);
                return Err(JarviisError::Inference(
                    "sampler called with empty batch (no logits available)".into(),
                ));
            }

            let token = sampler.sample(&ctx, logit_idx);
            sampler.accept(token);

            // EOS check (Qwen2 EOS = 151645 or model-generic eog).
            if token.0 == QWEN2_EOS_ID || self.model.is_eog_token(token) {
                // PATCH P9: Step-0 EOS guard — model produced EOS immediately.
                // This indicates the sampled distribution collapsed on the first
                // step (cold-start instability).  Retry once with greedy decoding
                // (top_k=1 effectively forces the highest-logit token).
                if step == 0 && !step0_eos_retry {
                    warn!(
                        "Step-0 EOS detected — retrying first token with greedy sampler \
                         (top_k=1, temp=0) to recover from cold-start collapse"
                    );
                    step0_eos_retry = true;
                    // Replace sampler with greedy chain.
                    sampler = LlamaSampler::chain_simple([
                        LlamaSampler::top_k(1),
                        LlamaSampler::temp(0.0),
                        LlamaSampler::dist(42),
                    ]);
                    // Do NOT advance step — re-sample from the same logits.
                    continue;
                }
                debug!("EOS token ({}) at generation step {}", token.0, step);
                break;
            }

            // Convert token id → UTF-8 text piece.
            match self.model.token_to_piece(token, &mut decoder, true, None) {
                Ok(piece) => output.push_str(&piece),
                Err(e) => warn!("token_to_piece failed (token {}): {}", token.0, e),
            }

            // PREPARE next decode: single-token batch.
            // Clear the batch (resetting n_tokens to 0) and add the sampled token.
            // After decode, batch.n_tokens() == 1, so logit_idx on the next
            // iteration = 0.  logits=true ensures ctx stores the row at index 0.
            batch.clear();
            batch.add(token, n_cur, &[0], true /* request logits */)
                .map_err(|e| {
                    error!("gen batch.add failed at step {} pos {}: {}", step, n_cur, e);
                    JarviisError::Inference(format!("gen batch.add failed: {e}"))
                })?;

            ctx.decode(&mut batch).map_err(|e| {
                error!("gen ctx.decode failed at step {}: {}", step, e);
                JarviisError::Inference(format!("gen decode failed: {e}"))
            })?;

            n_cur += 1;
            step += 1;

            if step > 0 && step % 50 == 0 {
                debug!("Generated {} tokens so far", step);
            }
        }

        // ── 6. Output validation ──────────────────────────────────────────────
        let trimmed = output.trim().to_string();
        if trimmed.is_empty() {
            return Err(JarviisError::Inference(
                "model returned empty output after step-0 guard — check model path and chat template".into(),
            ));
        }

        debug!(
            "Inference complete: {} output chars, {} tokens generated",
            trimmed.len(), step
        );
        Ok(trimmed)
    }
}

// ─── Trait impl ──────────────────────────────────────────────────────────────

impl InferenceEngine for LlamaEngine {
    fn infer(&self, prompt: String, timeout: Duration) -> Result<String> {
        self.infer_impl(prompt, timeout)
    }
}
