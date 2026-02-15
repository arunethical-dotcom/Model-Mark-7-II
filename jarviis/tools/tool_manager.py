"""
JARVIIS Tool Manager
Dispatcher pattern for tool execution.

Architecture Choice: Dispatcher Pattern
--------------------------------------
Evaluated:
- Command pattern → Too heavyweight
- Function registry → Not validatable
- Plugin systems → Overkill for Phase 2
- Dispatcher pattern → ✅ CHOSEN

Why Dispatcher?
- Simple registry of tool name → function
- Validates tool existence before execution
- Safe error handling
- Easy to add tools without refactoring
- No complex plugin loading

Design Principle:
- Tools are optional and isolated
- Failures never crash system
- Synchronous execution only
- No state mutation
"""

from typing import Dict, Any, Callable, List, Optional
import time


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    pass


class ToolManager:
    """
    Tool dispatcher and registry.
    
    Responsibilities:
    - Register tools by name
    - Validate tool calls
    - Execute tools synchronously
    - Return results or errors safely
    
    Does NOT:
    - Implement tool logic (tools do that)
    - Decide which tools to call (reasoner does that)
    - Handle async execution (Phase 3)
    - Maintain tool state (tools are stateless)
    
    Philosophy: Coordinate, don't implement.
    """
    
    def __init__(self):
        """Initialize tool manager."""
        self._tools: Dict[str, Callable] = {}
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}
        self._execution_count = 0
        
        # Register built-in demo tools
        self._register_builtin_tools()
    
    def register_tool(
        self,
        name: str,
        function: Callable,
        description: str = "",
        parameters: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Register a new tool.
        
        Args:
            name: Unique tool identifier
            function: Callable that implements the tool
            description: Human-readable description
            parameters: Expected parameter names and types
        """
        if name in self._tools:
            print(f"[TOOLS] Warning: Overwriting existing tool '{name}'")
        
        self._tools[name] = function
        self._tool_metadata[name] = {
            'description': description,
            'parameters': parameters or {},
            'registered_at': time.time()
        }
        
        print(f"[TOOLS] Registered tool: {name}")
    
    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a tool (implements ToolInterface).
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            
        Returns:
            Tool execution result
            
        Raises:
            ToolExecutionError: If tool fails
        """
        # Validate tool exists
        if not self.validate_tool(tool_name, parameters):
            raise ToolExecutionError(f"Tool '{tool_name}' not found or invalid")
        
        try:
            # Execute tool
            tool_func = self._tools[tool_name]
            result = tool_func(**parameters)
            
            self._execution_count += 1
            
            print(f"[TOOLS] Executed: {tool_name} → {str(result)[:50]}...")
            
            return result
            
        except Exception as e:
            # Log but don't crash
            print(f"[TOOLS] ERROR executing {tool_name}: {e}")
            raise ToolExecutionError(f"Tool '{tool_name}' failed: {e}")
    
    def validate_tool(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Validate tool exists and parameters are acceptable.
        
        Args:
            tool_name: Tool to validate
            parameters: Parameters to check
            
        Returns:
            True if valid
        """
        # Check tool exists
        if tool_name not in self._tools:
            return False
        
        # Basic validation (Phase 3: Add parameter type checking)
        if not isinstance(parameters, dict):
            return False
        
        return True
    
    def list_available_tools(self) -> List[str]:
        """
        List all registered tools.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a tool.
        
        Args:
            tool_name: Tool to query
            
        Returns:
            Tool metadata or None
        """
        return self._tool_metadata.get(tool_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tool manager statistics."""
        return {
            'registered_tools': len(self._tools),
            'execution_count': self._execution_count,
            'available_tools': self.list_available_tools()
        }
    
    # ========================================================================
    # Built-in Demo Tools (Phase 2 Infrastructure)
    # ========================================================================
    
    def _register_builtin_tools(self) -> None:
        """Register built-in demonstration tools."""
        
        # Echo tool
        self.register_tool(
            name='echo',
            function=self._tool_echo,
            description='Echo back the input text',
            parameters={'text': 'str'}
        )
        
        # Calculator tool
        self.register_tool(
            name='calculate',
            function=self._tool_calculate,
            description='Perform basic arithmetic',
            parameters={'expression': 'str'}
        )
        
        # Uppercase tool
        self.register_tool(
            name='uppercase',
            function=self._tool_uppercase,
            description='Convert text to uppercase',
            parameters={'text': 'str'}
        )
        
        # Time tool
        self.register_tool(
            name='current_time',
            function=self._tool_current_time,
            description='Get current time',
            parameters={}
        )
    
    def _tool_echo(self, text: str) -> str:
        """Echo tool implementation."""
        return f"Echo: {text}"
    
    def _tool_calculate(self, expression: str) -> str:
        """
        Safe calculator tool.
        
        Phase 3: Use proper expression parser.
        Phase 2: Limited to prevent code injection.
        """
        # Very basic calculator (safe)
        try:
            # Only allow numbers and basic operators
            allowed_chars = set('0123456789+-*/.()')
            if not all(c in allowed_chars or c.isspace() for c in expression):
                return "Error: Invalid characters in expression"
            
            # Evaluate safely
            result = eval(expression, {"__builtins__": {}}, {})
            return f"Result: {result}"
            
        except Exception as e:
            return f"Calculation error: {e}"
    
    def _tool_uppercase(self, text: str) -> str:
        """Uppercase tool implementation."""
        return text.upper()
    
    def _tool_current_time(self) -> str:
        """Current time tool implementation."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
