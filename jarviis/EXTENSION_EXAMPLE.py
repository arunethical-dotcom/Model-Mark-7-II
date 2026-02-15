"""
JARVIIS Extension Example
This file demonstrates how to implement real subsystems that plug into the core.

NOTE: This is an EXAMPLE only - not part of the core.
Save this as 'examples/example_extensions.py' when ready to extend JARVIIS.
"""

from typing import Dict, Any, List
from core.interfaces import MemoryInterface, ReasoningInterface, ToolInterface


# ============================================================================
# Example 1: Simple In-Memory Storage
# ============================================================================

class SimpleMemory(MemoryInterface):
    """
    Basic in-memory storage using Python lists.
    In production, replace with ChromaDB, FAISS, or Pinecone.
    """
    
    def __init__(self):
        self.storage: List[Dict[str, Any]] = []
    
    def store(self, data: Dict[str, Any]) -> None:
        """Store data in memory."""
        self.storage.append(data)
        print(f"✅ Stored: {data.get('user_input', 'data')[:50]}...")
    
    def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve most recent items (no semantic search yet).
        In production, use embeddings for similarity search.
        """
        return self.storage[-limit:] if self.storage else []
    
    def clear(self) -> None:
        """Clear all memory."""
        self.storage.clear()
        print("🗑️  Memory cleared")


# ============================================================================
# Example 2: Rule-Based Reasoner (Pre-LLM)
# ============================================================================

class RuleBasedReasoner(ReasoningInterface):
    """
    Simple pattern-matching reasoner.
    In production, replace with Ollama, llama.cpp, or API-based LLM.
    """
    
    def __init__(self):
        self.rules = {
            "hello": "Hello! I'm JARVIIS, your cognitive assistant.",
            "help": "I can help with information, tasks, and learning. What do you need?",
            "calculate": "I don't have a calculator tool yet, but I'm working on it!",
            "weather": "Weather tools are not implemented yet.",
            "time": "Time tools are not implemented yet.",
        }
    
    def reason(self, context: Dict[str, Any]) -> str:
        """
        Generate response based on keyword matching.
        In production, this would call an LLM.
        """
        user_input = context.get('user_input', '').lower()
        
        # Check for keyword matches
        for keyword, response in self.rules.items():
            if keyword in user_input:
                return response
        
        # Default response
        return (
            f"I understand you said: '{context['user_input']}'. "
            "However, I'm still learning. My reasoning engine needs an LLM upgrade!"
        )
    
    def is_available(self) -> bool:
        """Always ready (no model loading needed)."""
        return True


# ============================================================================
# Example 3: Basic Tool Executor
# ============================================================================

class BasicToolExecutor(ToolInterface):
    """
    Simple tool executor with a few hardcoded tools.
    In production, use LangChain, AutoGPT tools, or custom implementations.
    """
    
    def __init__(self):
        self.tools = {
            "echo": self._echo,
            "calculate": self._calculate,
            "uppercase": self._uppercase,
        }
    
    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool by name."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        return self.tools[tool_name](parameters)
    
    def list_available_tools(self) -> List[str]:
        """List all registered tools."""
        return list(self.tools.keys())
    
    def validate_tool(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Check if tool exists."""
        return tool_name in self.tools
    
    # Tool implementations
    
    def _echo(self, params: Dict[str, Any]) -> str:
        """Echo back the input."""
        return params.get("text", "")
    
    def _calculate(self, params: Dict[str, Any]) -> float:
        """Basic calculator."""
        operation = params.get("operation")
        a = params.get("a", 0)
        b = params.get("b", 0)
        
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            return a / b if b != 0 else float('inf')
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def _uppercase(self, params: Dict[str, Any]) -> str:
        """Convert text to uppercase."""
        return params.get("text", "").upper()


# ============================================================================
# Example Usage: Plugging Extensions into JARVIIS
# ============================================================================

def demonstrate_extensions():
    """Show how to use custom implementations with JARVIIS core."""
    from core import Orchestrator
    
    print("\n" + "="*60)
    print("🔌 JARVIIS WITH CUSTOM EXTENSIONS")
    print("="*60 + "\n")
    
    # Create custom implementations
    memory = SimpleMemory()
    reasoner = RuleBasedReasoner()
    tools = BasicToolExecutor()
    
    # Inject into orchestrator
    orchestrator = Orchestrator(
        memory=memory,
        reasoner=reasoner,
        tools=tools
    )
    
    # Test interactions
    test_cases = [
        "Hello JARVIIS",
        "Can you help me?",
        "What's the weather today?",
    ]
    
    for user_input in test_cases:
        print(f"\n{'─'*60}")
        print(f"You: {user_input}")
        print('─'*60)
        
        response = orchestrator.process_request(user_input)
        print(f"JARVIIS: {response}\n")
    
    # Show memory contents
    print("\n" + "="*60)
    print("📚 MEMORY CONTENTS")
    print("="*60)
    print(f"Stored interactions: {len(memory.storage)}")
    for i, item in enumerate(memory.storage, 1):
        print(f"\n{i}. User: {item.get('user_input', 'N/A')}")
        print(f"   Response: {item.get('system_response', 'N/A')[:80]}...")
    
    print("\n✅ Extension demonstration complete!\n")


# ============================================================================
# Next Steps for Real Intelligence
# ============================================================================

"""
PRODUCTION-READY IMPLEMENTATIONS:

1. ReasoningInterface → LLM Integration
   - Use Ollama for local inference: https://ollama.ai/
   - Or llama.cpp Python bindings
   - Or OpenAI/Anthropic APIs
   
   Example:
   ```python
   import ollama
   
   class OllamaReasoner(ReasoningInterface):
       def reason(self, context):
           response = ollama.chat(
               model='llama2',
               messages=[{'role': 'user', 'content': context['user_input']}]
           )
           return response['message']['content']
   ```

2. MemoryInterface → Vector Database
   - ChromaDB (easiest): pip install chromadb
   - FAISS (fastest): pip install faiss-cpu
   - Pinecone (cloud): pip install pinecone-client
   
   Example:
   ```python
   import chromadb
   
   class VectorMemory(MemoryInterface):
       def __init__(self):
           self.client = chromadb.Client()
           self.collection = self.client.create_collection("jarviis_memory")
       
       def store(self, data):
           self.collection.add(
               documents=[data['user_input']],
               metadatas=[data],
               ids=[str(hash(data['user_input']))]
           )
   ```

3. ToolInterface → Function Calling
   - LangChain Tools
   - OpenAI Function Calling
   - Custom API wrappers
   
4. Add async/await for concurrency:
   - Make orchestrator methods async
   - Use asyncio for parallel tool execution
   - Stream responses in real-time

5. Add configuration file loading:
   - YAML/JSON config files
   - Environment variables
   - Runtime settings UI
"""


if __name__ == "__main__":
    demonstrate_extensions()
