# Inference Engine Integration Guide

## Overview

The JARVIIS Cognitive Kernel now integrates with **Ollama** as the primary inference backend. This replaces the deterministic MockInferenceEngine with real LLM reasoning while maintaining deterministic kernel behavior.

### Architecture

The S4_INFERENCE stage now supports three backends in priority order:

```
┌─ Ollama HTTP (Preferred) ─────────────────────────────────┐
│  Requires: Ollama service running on localhost:11434      │
│  Easiest to deploy; no C++ toolchain needed               │
│  └─ If unavailable, falls back to:                        │
│                                                             │
│     ┌─ LlamaEngine (Optional, feature-gated) ────────────┐ │
│     │  Requires: cargo build --release --features llama  │ │
│     │  Requires: C++ toolchain + GGUF model file         │ │
│     │  └─ If unavailable, falls back to:                │ │
│     │                                                     │ │
│     │     ┌─ MockInferenceEngine (Fallback) ─────────┐  │ │
│     │     │  Always available; deterministic echo    │  │ │
│     │     │  Suitable for testing FSM pipeline       │  │ │
│     │     └────────────────────────────────────────────┘  │ │
│     └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start: Using Ollama

### 1. Install Ollama

Download and install from: https://ollama.ai

### 2. Pull the Qwen Model

```bash
ollama pull qwen
```

This downloads the Qwen 1.5-1.8B Chat quantized model (~2GB).

### 3. Start Ollama Server

```bash
ollama serve
```

This starts the HTTP API server on `http://localhost:11434`.

### 4. Build and Run JARVIIS

In a new terminal:

```bash
cd C:\Users\asus\Model\jarviis-core
cargo run
```

The kernel will automatically detect Ollama and start using it.

## Configuration

### Default Settings

Edit [src/config.rs](src/config.rs) to customize:

```rust
// Default Ollama configuration
ollama_host: "localhost".to_string(),
ollama_port: 11434,
ollama_model: "qwen".to_string(),
use_ollama: true,  // Enable Ollama backend
```

### Environment-Based Configuration

You can override defaults by setting environment variables before running:

```bash
# Use a remote Ollama server
set OLLAMA_HOST=192.168.1.100
set OLLAMA_PORT=11434

# Use a different model
set OLLAMA_MODEL=mistral

# Disable Ollama and use mock engine
set USE_MOCK=1

cargo run
```

## Available Models

### Pre-Tested with Qwen (Recommended)

- **qwen** — Qwen 1.5-1.8B Chat (Default)
  - RAM: ~2–3 GB
  - Inference time: ~1–3 seconds per response
  - Good for CPU-only inference

### Compatible Models

You can use any model available in Ollama:

```bash
ollama pull mistral         # Mistral 7B
ollama pull phi             # Phi 3 Mini
ollama pull neural-chat     # Neural Chat
ollama pull orca-mini       # Orca Mini
```

Then set in config:

```rust
ollama_model: "mistral".to_string(),
```

## Advanced: Monitoring & Debugging

### Enable Debug Logging

```bash
set RUST_LOG=jarviis_core=debug,warn
cargo run
```

This will log:
- Ollama connection attempts
- Inference timing
- Response parsing details
- FSM state transitions

### HTTP-Level Debugging

```bash
# Manually test the Ollama API
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "prompt": "Hello, how are you?",
    "stream": false
  }'
```

### Check Ollama Status

```bash
# List available models
ollama list

# Check if server is running
curl http://localhost:11434/api/tags
```

## Fallback Behavior

If Ollama is unavailable:

1. The kernel will log a warning
2. Inference automatically falls back to MockInferenceEngine
3. The FSM continues normally with deterministic responses
4. No errors are surfaced to the user

### Testing Fallback

```bash
# Stop Ollama and run the kernel
cargo run
```

You'll see:

```
[INFO] Using MockInferenceEngine (deterministic fallback)
```

## Advanced: llama.cpp Backend (Feature-Gated)

For CPU-optimized inference without a separate server:

### Prerequisites

- C++ compiler (MSVC on Windows, GCC on Linux)
- GGUF model file (e.g., `models/qwen1_5-1_8b-chat-q4_k_m.gguf`)

### Build with llama Feature

```bash
# Download a GGUF model first
# Place in models/qwen1_5-1_8b-chat-q4_k_m.gguf

cargo build --release --features llama
```

### Switch Backend in config.rs

```rust
use_ollama: false,  // Disable Ollama, enable llama.cpp
```

### Run

```bash
cargo run --features llama
```

## Inference Flow

```
S4_INFERENCE Stage
└─ Kernel retrieves formatted prompt (with identity + memory context)
   │
   ├─ OllamaInferenceEngine.infer()
   │  │
   │  ├─ POST http://localhost:11434/api/generate
   │  │  {
   │  │    "model": "qwen",
   │  │    "prompt": "...",
   │  │    "temperature": 0.7
   │  │  }
   │  │
   │  ├─ Parse JSON response
   │  │
   │  └─ Return model output
   │
   │  [On error: HTTP timeout/network/parsing]
   │  └─ Log error and return JarviisError::Inference
   │
   └─ FSM applies identity firewall + sanitization
      └─ S5_IDENTITY_FIREWALL checks for policy violations
         └─ S7_OUTPUT_SANITIZATION ensures safe response
            └─ S8_MEMORY_WRITE stores result for episodic recall
               └─ S9_EMIT_RESPONSE sends to user
```

## Error Handling

### Ollama Connection Failure

**Log Entry:**
```
[ERROR] Ollama HTTP error: connection refused
[ERROR] FSM → S_ERR (failing closed)
```

**User Response:**
```
Sir, I encountered an internal error while processing your request.
```

**Recovery:**
- Start Ollama: `ollama serve`
- Retry the command

### Model Not Found

**Log Entry:**
```
[ERROR] Ollama returned 404: ensure Ollama is running on localhost:11434
```

**Solution:**
```bash
ollama pull qwen
```

### Inference Timeout

**Log Entry:**
```
[ERROR] Ollama HTTP error: request timeout after 20s
```

**Solution:**
- Increase timeout in `config.rs`: `inference_timeout_secs: 30`
- Or use a smaller model

## Performance Tuning

### Latency Optimization

1. **Use Ollama GPU mode** (if NVIDIA GPU available):

   ```bash
   # Ollama will automatically detect and use GPU
   ollama serve
   ```

2. **Reduce context window** in config.rs:

   ```rust
   n_ctx: 2048,  // Instead of 4096
   ```

3. **Lower temperature** for faster convergence:

   See `src/inference/ollama.rs` line ~45

### Memory Optimization

- Qwen 1.8B: ~2–3 GB RAM (default)
- Mistral 7B: ~5–7 GB RAM
- Phi 3 Mini: ~3–4 GB RAM

## Testing

### Unit Tests

```bash
cargo test inference::tests
```

### Integration Testing

```bash
# Start Ollama first
ollama serve

# In another terminal
RUST_LOG=debug cargo run
```

Type test prompts:

```
> What is 2 + 2?
> Tell me a joke
> Explain the FSM
```

## Troubleshooting

| Issue | Symptom | Solution |
|-------|---------|----------|
| "connection refused" | Ollama not running | `ollama serve` |
| Empty model output | Inference failed | Check Ollama logs |
| Slow responses | High latency | Enable GPU, reduce context |
| Memory exhaustion | OOM crash | Use smaller model (phi, orca-mini) |
| Model not found | 404 error | `ollama pull <model_name>` |

## Architecture Files

- **Config:** [src/config.rs](src/config.rs) — Ollama settings
- **Inference trait:** [src/inference/mod.rs](src/inference/mod.rs) — InferenceEngine trait + MockInferenceEngine
- **Ollama backend:** [src/inference/ollama.rs](src/inference/ollama.rs) — HTTP API client
- **FSM integration:** [src/fsm/mod.rs](src/fsm/mod.rs) — S4_INFERENCE stage
- **Error handling:** [src/error.rs](src/error.rs) — JarviisError enum

## Next Steps

1. ✅ Install Ollama and pull a model
2. ✅ Run `cargo build` to verify compilation
3. ✅ Start `ollama serve` in a terminal
4. ✅ Run `cargo run` in another terminal
5. ✅ Test with real LLM prompts

The kernel will now execute real inference via Ollama while maintaining full FSM integrity, identity firewall, and memory coherence.

---

**Last Updated:** February 25, 2026  
**Ollama Version:** 0.1+  
**Qwen Model:** 1.5-1.8B Chat Q4_K_M
