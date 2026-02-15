"""
JARVIIS Configuration Settings
Centralized configuration for the cognitive core.
"""

from dataclasses import dataclass
from enum import Enum


class LogLevel(Enum):
    """Logging verbosity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class CoreSettings:
    """
    Core system settings.
    
    Frozen dataclass ensures configuration immutability at runtime.
    All settings should be defined here to avoid magic values.
    """
    
    # System Identification
    system_name: str = "JARVIIS"
    version: str = "0.1.0"
    
    # State Machine Configuration
    enable_state_logging: bool = True
    strict_state_validation: bool = True  # Raise errors on invalid transitions
    
    # Logging
    log_level: LogLevel = LogLevel.INFO
    log_state_transitions: bool = True
    
    # Performance (Future Use)
    max_memory_mb: int = 512  # Memory budget for future subsystems
    max_reasoning_time_sec: int = 30  # Timeout for reasoning phase
    
    # Feature Flags (All disabled in core)
    enable_memory: bool = False
    enable_reasoning: bool = False
    enable_tools: bool = False
    enable_learning: bool = False
    enable_reflection: bool = False


# Global settings instance
settings = CoreSettings()


def get_settings() -> CoreSettings:
    """
    Retrieve global settings instance.
    
    Returns:
        CoreSettings: Immutable configuration object
    """
    return settings
