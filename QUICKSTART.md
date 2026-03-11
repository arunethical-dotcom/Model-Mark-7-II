# 🚀 JARVIIS Inference Engine — Quick Start

## 5-Minute Setup

### Step 1: Install Ollama (2 min)

Download and install from: **https://ollama.ai**

### Step 2: Download the Model (1 min)

```bash
ollama pull qwen
```

This downloads the Qwen 1.5-1.8B Chat model (~2GB).

### Step 3: Start Ollama Server

Open a terminal and run:

```bash
ollama serve
```

You should see:

```
✓ Listening on http://127.0.0.1:11434
```

**Keep this terminal open.** Do NOT close it.

### Step 4: Build the Kernel

Open a **new terminal** in the project directory:

```bash
cd C:\Users\asus\Model\jarviis-core
cargo build
```

Should complete with: `Finished dev profile [unoptimized + debuginfo]`

### Step 5: Run the Kernel

In that same terminal:

```bash
cargo run
```

You should see:

```
╔══════════════════════════════════════════╗
║  JARVIIS Cognitive Kernel OS  v1.1       ║
║  Deterministic Local Runtime — Ready     ║
╚══════════════════════════════════════════╝
JARVIIS online. Awaiting input, Sir.

  (type 'exit' or 'quit' to shut down)

> _
```

### Step 6: Test Real Inference

Type a prompt:

```
> What is 2 plus 2?
```

**Expected output** (from real Ollama inference):

```
Sir, the answer to 2 plus 2 is 4.

> _
```

**NOT** the mock response:

```
Sir, I have received your request: "What is 2 plus 2?". Start Ollama...
```

## ✅ You're Done!

The kernel is now connected to real LLM inference via Ollama.

---

## Testing Various Prompts

```
> Tell me a joke
[Real response from Qwen model]

> Explain quantum computing
[Real response from Qwen model]

> What's the capital of France?
[Real response from Qwen model]

> exit
Goodbye, Sir.
```

## Troubleshooting

### "Connection refused"

**Problem:** Terminal shows error like `connection refused`

**Solution:**
1. Check that Ollama terminal is still running
2. If not, restart it: `ollama serve`

### "Model not found" (404 error)

**Problem:** `Ollama returned 404`

**Solution:**
```bash
ollama pull qwen
```

### Slow Responses

**Normal:** First inference takes ~3-5 seconds. Subsequent ones are ~1-3 seconds.

**If extremely slow (>10s):**
- Check CPU usage (should be 100% on one core)
- Close other applications
- Use a smaller model: `ollama pull phi`

### Kernel Still Shows Mock Responses

**Check logs:**
```bash
set RUST_LOG=debug
cargo run
```

Look for: `[INFO] Using Ollama HTTP backend` or `[ERROR] connection refused`

---

## Next Steps

### Learn More About Configuration

See: [INFERENCE_INTEGRATION.md](INFERENCE_INTEGRATION.md)

### View Detailed Implementation

See: [IMPLEMENTATION_DETAILS.md](IMPLEMENTATION_DETAILS.md)

### See All Changes Made

See: [CHANGES.md](CHANGES.md)

---

## What Was Fixed

| Before | After |
|--------|-------|
| ❌ 0ms fallback response | ✅ Real inference from Ollama |
| ❌ Model never loaded | ✅ Model actively called |
| ❌ No error handling | ✅ Proper error logging |
| ❌ Silent failures | ✅ Visible logs for debugging |
| ❌ Mock-only responses | ✅ Real LLM reasoning |

---

## Available Models

Default: **qwen** (recommended)

Other options:
```bash
ollama pull mistral      # Mistral 7B (larger, slower)
ollama pull phi          # Phi 3 Mini (smaller, faster)
ollama pull neural-chat  # Neural Chat
ollama pull orca-mini    # Orca Mini
```

Then update `src/config.rs`:

```rust
ollama_model: "mistral".to_string(),
```

And rebuild:

```bash
cargo build && cargo run
```

---

## Architecture Quick Reference

```
User Input
    ↓
S1_INPUT_VALIDATION
    ↓
S2_MEMORY_RETRIEVAL (fetch relevant context)
    ↓
S3_IDENTITY_INJECTION (assemble prompt with system context)
    ↓
S4_INFERENCE ← ← ← NOW WITH OLLAMA! ← ← ←
    │
    └─ POST http://localhost:11434/api/generate
       ├─ Model: "qwen"
       ├─ Prompt: "System instructions\n...\nUser: [user input]"
       └─ Get real LLM response
    ↓
S5_IDENTITY_FIREWALL (validate response integrity)
    ↓
S7_OUTPUT_SANITIZATION (ensure safe output)
    ↓
S8_MEMORY_WRITE (store in episodic memory)
    ↓
S9_EMIT_RESPONSE → User
```

---

## Files to Know

| File | Purpose |
|------|---------|
| `src/config.rs` | Ollama connection settings |
| `src/inference/ollama.rs` | HTTP API client (NEW) |
| `src/inference/mod.rs` | Backend selection logic (REWRITTEN) |
| `src/main.rs` | Boot-time engine selection (UPDATED) |
| `src/fsm/mod.rs` | S4_INFERENCE integration (UPDATED) |

---

## Build & Run Commands Cheat Sheet

```bash
# Build the project
cargo build

# Build release (optimized)
cargo build --release

# Run with debug logging
set RUST_LOG=debug
cargo run

# Run with info logging (default)
cargo run

# Run the llama.cpp backend (requires C++ toolchain + GGUF)
cargo build --release --features llama
cargo run --release --features llama

# Run tests
cargo test

# Clean build artifacts
cargo clean
```

---

## That's It!

Your JARVIIS kernel is now fully operational with real language model inference. 

Enjoy! 🎉

---

**Last Updated:** February 25, 2026  
**Ollama Version:** 0.1+  
**Model:** Qwen 1.5-1.8B Chat
