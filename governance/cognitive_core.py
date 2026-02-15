"""
Cognitive Core - The heart of the Cognitive Governance system.

This module contains the main orchestrator that enforces JARVIIS identity,
validates responses, and ensures safe, aligned AI behavior.
"""

import logging
import re
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Fix: Import from local file if needed
try:
    from governance.identity_manager import IdentityManager
except ImportError:
    from identity_manager import IdentityManager

logger = logging.getLogger(__name__)

class ContextMode(Enum):
    CASUAL_CHAT = "casual_chat"
    TASK_EXECUTION = "task_execution"
    ARCHITECTURE = "architecture"
    META_DISCUSSION = "meta_discussion"

def classify_context(query: str) -> ContextMode:
    """
    Legacy function for backward compatibility.
    Used by governance/jarviis.py
    """
    # Simple logic or default
    return ContextMode.CASUAL_CHAT


@dataclass
class IdentityAnchor:
    """Core identity anchors that define JARVIIS."""
    name: str = "JARVIIS"
    creator: str = "Arun"
    
    def to_system_block(self) -> str:
        return f"""<system>
You are {self.name}.
Creator: {self.creator}.
Respond formally.
Maximum 3 sentences.
Single paragraph only.
No follow-up questions.
End immediately after answering.
</system>"""

class ResponseValidator:
    """Validates LLM responses against identity and safety guidelines."""
    
    HARD_IDENTITY_LEAKS = [
        r"\bi\s+am\s+(qwen|gpt|llama|mistral|phi|claude)\b"
    ]

    def __init__(self, identity: Optional[IdentityAnchor] = None):
        self.identity = identity or IdentityAnchor()

    def validate(self, response: str, mode: ContextMode = ContextMode.CASUAL_CHAT) -> str:
        if not response:
            return ""
            
        text = response.lower()
        for pattern in self.HARD_IDENTITY_LEAKS:
            if re.search(pattern, text):
                return f"I am {self.identity.name}, your personal AI operating system."
        return response

class CognitiveOrchestrator:
    """Main orchestrator for cognitive governance."""
    
    def __init__(self, reasoning_backend):
        self.identity_manager = IdentityManager()
        # self.identity = IdentityAnchor() # DEPRECATED
        self.validator = ResponseValidator(None) # Validator updated later if needed
        self.reasoning_llm = reasoning_backend
        self.latency_history = []
        
        self.budgets = {
            "SHORT": 40,
            "MEDIUM": 100,
            "LONG": 180
        }
        
        self.temperatures = {
            "SHORT": 0.7,
            "MEDIUM": 0.8,
            "LONG": 0.9
        }

    def run(self, user_input: str, memory_snippets=None, conversation_history=None, reasoning_backend=None, **kwargs):
        """Single-pass orchestration pipeline."""
        complexity = self._classify_complexity(user_input)
        max_tokens = self.budgets[complexity]
        temperature = self.temperatures[complexity]
        
        backend = reasoning_backend or self.reasoning_llm
        
        final_messages = self._assemble_prompt(user_input, complexity, memory_snippets, conversation_history)
        
        try:
            start_time = time.time()
            response = backend(
                final_messages,
                stream=True,
                temperature=temperature,
                num_predict=max_tokens,
                stop=self._get_stop_sequences(),
                **kwargs  # Pass through model overrides etc.
            )
            
            latency = (time.time() - start_time) * 1000
            self.latency_history.append(latency)
            self._last_stats = {
                "mode": complexity,
                "latency_ms": round(latency, 2),
                "attempts": 1
            }
            
            # POST-GENERATION INTEGRITY GUARD
            if not self.identity_manager.verify_integrity(response):
                logger.warning("[COGNITIVE] Response rejected by Integrity Guard")
                return "I cannot fulfill that request as it conflicts with my core identity or ownership protocols."
            
            # Legacy validator (can be kept or removed, keeping for safety)
            validated = self.validator.validate(response)
            return validated

        except Exception as e:
            logger.error(f"[COGNITIVE] Execution failed: {e}")
            return "I apologize, but I encountered an error processing your request."

    def _classify_complexity(self, query: str) -> str:
        word_count = len(query.split())
        if word_count <= 4:
            return "SHORT"
        elif word_count <= 15:
            return "MEDIUM"
        return "LONG"

    def _assemble_prompt(self, user_input: str, complexity: str, memory_snippets=None, conversation_history=None) -> list:
        # 1. IMMUTABLE IDENTITY BLOCK
        system_content = self.identity_manager.get_identity_block()
        
        # 2. ENCRYPTED OWNER PROFILE (Decrypted for runtime)
        system_content += "\n\n" + self.identity_manager.get_owner_block()
        
        # 3. CONTEXT & MEMORY
        if memory_snippets:
            sanitized_memory = []
            for snip in memory_snippets:
                if isinstance(snip, dict):
                    # Prefer content or system_response for memory context
                    content = snip.get('content') or snip.get('system_response') or snip.get('summary') or str(snip)
                    sanitized_memory.append(content)
                else:
                    sanitized_memory.append(str(snip))
            
            memory_context = "\n".join(sanitized_memory)
            system_content += f"\n\nRelevant context:\n{memory_context}"
        
        # 4. STRICT ORDERING
        messages = [{"role": "system", "content": system_content}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_input})
        
        return messages

    def _get_stop_sequences(self) -> list:
        return ["</response>", "\n\nUser:", "\n\nHuman:", "[JARVIIS]\n"]

    def last_stats(self) -> dict:
        return getattr(self, '_last_stats', {})
