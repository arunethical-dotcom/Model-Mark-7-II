# JARVIIS (Just A Rather Very Intelligent Integrated System) : Is currently on Development

JARVIIS is a lightweight, production-grade **Cognitive Operating System Kernel**. It provides a deterministic, stateful foundation for running local agentic AI, prioritizing architectural discipline and reliability.

## 🎯 Scope
**Project Goal:** Agent OS Kernel
JARVIIS is not an LLM or a simple chatbot; it is the **kernel** that manages the lifecycle, state transitions, and subsystem coordination of an autonomous cognitive agent. It satisfies the need for a formal, observable execution environment for local intelligence.

---

## 🏗️ Modular Topology

The system is designed with a strict modular hierarchy to ensure zero circular dependencies and clear separation of concerns.

```text
jarviis/
    core/           # Kernel orchestration & FSM
    reasoning/      # Decision logic (Rules + LLM)
    memory/         # Structured episodic recovery
    tools/          # External action interfaces
    config/         # Immutable system settings
    __init__.py     # Package initialization
```

---

## 🔧 Installation & Setup

### 1. Prerequisites
- **Python 3.10+** (Standard library only for core kernel)
- **Ollama** (Optional, for LLM-enhanced reasoning)

### 2. Dependency Management
Install the core kernel and optional intelligence modules:
```bash
# Core only
pip install .

# Core + LLM + Memory development
pip install -e ".[llm,memory,dev]"
```

---

## 🚀 Entrypoint

JARVIIS is natively designed to be invoked as a module. This ensures proper package resolution and a consistent runtime environment.

```bash
# Run the core demonstration
python jarviis\main

# Run in interactive mode
python start_jarviis.py --interactive mode
```
```
for test purpose : run these files jarviis\ 
python test_backend.py
python test_cognitive_import.py
python test_core.py
python test_governance_integration.py
python test_llm_integration.py
python test_memory.py
python test_phase2.py
```
---

## 📚 API & Documentation

The JARVIIS kernel is defined by formal interfaces. See [core/interfaces.py](jarviis/core/interfaces.py) for the full contract documentation.

### Core Orchestration
```python
from jarviis.core.orchestrator import Orchestrator

# Initialize with desired subsystems
orchestrator = Orchestrator(
    reasoner=CustomReasoner(),
    memory=CustomMemory()
)

# Single cognitive cycle
response = orchestrator.process_request("Analyze status.")
```

### State Machine Lifecycle
Every request follows a validated FSM path:
`IDLE` → `LISTENING` → `REASONING` → `EXECUTING` → `LEARNING` → `REFLECTING` → `IDLE`

---

## 🧪 Verification & Testing

JARVIIS includes a high-integrity test suite that validates FSM logic and subsystem contracts.

```bash
# Run the full suite using pytest
bash -c "PYTHONPATH=. pytest jarviis/"

# Or individual tests
python jarviis/test_core.py
python jarviis/test_memory.py
```

---

## 📄 License
MIT License. High-integrity code for local intelligence systems.

MIT License - Free for commercial and personal use.
