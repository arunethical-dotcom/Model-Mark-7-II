# JARVIIS (Just A Rather Very Intelligent Information System)

JARVIIS is a production-grade **Cognitive Operating System** designed to be the foundational nervous system for local agentic AI. Built with architectural discipline, it prioritizes stability, predictability, and extensibility over premature complexity.

## 🚀 Overview

JARVIIS implements a **Finite State Machine (FSM)** driven orchestration layer that coordinates several independent subsystems:
- **Core Orchestrator**: Manages the request lifecycle and subsystem routing.
- **State Manager**: Enforces strict state transitions and provides full observability.
- **Memory Subsystem**: Structured episodic memory with importance-aware retrieval.
- **Reasoning Engine**: Rule-based logic with surgical LLM enhancement via Ollama.
- **Tool System**: Extensible interface for filesystem, web search, and more.

## 🏗️ Architecture Goals

1.  **Clarity > Cleverness**: Pure Python implementation with minimal abstractions.
2.  **Explicit State Control**: Every transition is validated by a formal State Machine.
3.  **Dependency Inversion**: High-level core logic depends on abstract interfaces, not concrete implementations.
4.  **Async-Ready**: Designed for a seamless transition to asynchronous execution (Phase 3).
5.  **Observable by Design**: Full execution traces and state histories are built-in.

---

## 🔧 Setup & Dependencies

JARVIIS is designed to run locally on consumer hardware (e.g., i5 CPU + 8GB RAM).

### 1. Prerequisites
- **Python 3.10+**
- **Ollama** (Optional, for LLM-enhanced reasoning): [Download Ollama](https://ollama.ai)

### 2. Installation
```bash
# Clone the repository
git clone <repository-url>
cd jarviis

# Install dependencies (Zero external dependencies for core!)
pip install -r requirements.txt
```

### 3. Model Setup (Optional)
If using the LLM-enhanced reasoning engine:
```bash
# Pull the recommended models
ollama pull mistral:instruct
ollama pull qwen2.5:0.5b-instruct
```

---

## 💻 How to Run

### Command Line Interface (CLI)
Run the main demonstration script to interact with JARVIIS:
```bash
python main.py
```

### Running Tests
Verify the system integrity with the comprehensive test suite:
```bash
python test_core.py      # Core FSM & Orchestrator tests
python test_memory.py    # Memory subsystem tests
python test_phase2.py    # Integration tests
```

### Examples
Explore how to extend JARVIIS or use specific features:
```bash
python EXTENSION_EXAMPLE.py   # Code-level extension patterns
python example_with_memory.py # Advanced memory interactions
```

---

## 🏛️ System Architecture

### Finite State Machine (FSM)
JARVIIS operates through a set of clearly defined states:
`IDLE` → `LISTENING` → `REASONING` → `EXECUTING` → `LEARNING` → `REFLECTING`

| Phase | Description |
| :--- | :--- |
| **LISTENING** | Parses user input and context. |
| **REASONING** | Decides the type of response or tool needed. |
| **EXECUTING** | Performs external tool actions (Filesystem, Web). |
| **LEARNING** | Persists interaction to structured episodic memory. |

### Memory Strategy
JARVIIS uses a multi-layered approach to memory:
1.  **SQLite Storage**: Pure storage layer for persistence.
2.  **Memory Router**: Decision layer for importance scoring (1-5 scale) and categorization.
3.  **Retrieval**: Combines recent context with the most important historical memories.

---

## 🔮 Roadmap
- **Phase 2 (Current)**: Intelligence integration (LLMs, Vector Memory).
- **Phase 3 (Upcoming)**: Asynchronous execution and streaming responses.
- **Phase 4 (Future)**: Knowledge Graph integration and collective learning.

---

## 📄 License
MIT License - Free for commercial and personal use.
