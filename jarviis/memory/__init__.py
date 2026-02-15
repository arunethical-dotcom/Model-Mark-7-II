"""
JARVIIS Memory Subsystem
Structured episodic memory with importance-aware retrieval.

Components:
- MemoryRouter: Decision layer (importance scoring, routing)
- SQLiteStore: Storage layer (pure SQL operations)
- schema.sql: Database schema

Usage:
    from memory import MemoryRouter
    
    memory = MemoryRouter()
    memory.store({'user_input': 'Hello', 'system_response': 'Hi!'})
    memories = memory.retrieve('greeting', limit=5)
"""

from memory.memory_router import MemoryRouter
from memory.sqlite_store import SQLiteStore

__all__ = ['MemoryRouter', 'SQLiteStore']
