# JARVIIS Model Directory

Place your GGUF model file here.

## Current Model

**Qwen 1.5-1.8B Chat (Q4_K_M)** is available:

| Property       | Value                     |
|----------------|---------------------------|
| Model          | Qwen 1.5-1.8B Chat        |
| Format         | GGUF                      |
| Quantization   | Q4_K_M                    |
| File           | `qwen1_5-1_8b-chat-q4_k_m.gguf` |
| Context Window | ≤ 4096 tokens             |
| RAM footprint  | ~2–3 GB                   |

## Build with real inference

```bash
# Ensure a C++ toolchain is installed (MSVC or MinGW on Windows)
cargo build --release --features llama
```

This will compile against the Qwen model already present in the `models/` directory.

## Custom model setup

To use a different model, either:

1. Replace the GGUF file and update `model_path` in `KernelConfig`:

```rust
// src/config.rs
model_path: "models/your-model-name.gguf".to_string(),
```

2. Or create a symlink to your preferred model:

```bash
# Windows
mklink qwen1_5-1_8b-chat-q4_k_m.gguf path\to\your\model.gguf
```

## Suggested alternative sources

- [Mistral-7B-Instruct-v0.2-Q4_K_M](https://huggingface.co/TheBloke)
- [Phi-3-mini-4k-instruct-Q4_K_M](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)

## Running without a model (mock mode)

Without the `llama` feature, the system runs `MockInferenceEngine`, which
echoes requests back deterministically. This is suitable for testing the
full FSM pipeline, identity, governance, and memory subsystems.

```bash
cargo run
```
