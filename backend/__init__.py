"""
OMNI Backend Package

A modular, agent-based AI development system with swappable components.
"""

__version__ = "0.1.0"
__author__ = "OMNI Team"

from backend.core import (
    LLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    VectorDBProvider,
    Document,
    SearchResult,
    AgentBase,
    AgentMessage,
    AgentContext,
    WorkflowBase,
    WorkflowContext,
    WorkflowStep,
)

from backend.adapters.llm.factory import LLMFactory
from backend.adapters.vectordb.factory import VectorDBFactory
from backend.agents import AgentLoader, AgentRegistry, AgentOrchestrator
from backend.config import get_settings, Settings, ConfigLoader
from backend.server import run_server

__all__ = [
    # Version
    "__version__",
    # Core Interfaces
    "LLMProvider",
    "LLMConfig",
    "LLMMessage",
    "LLMResponse",
    "VectorDBProvider",
    "VectorDBConfig",
    "Document",
    "SearchResult",
    "AgentBase",
    "AgentConfig",
    "AgentMessage",
    "AgentContext",
    "WorkflowBase",
    "WorkflowContext",
    "WorkflowStep",
    # Factories
    "LLMFactory",
    "VectorDBFactory",
    # Agents
    "AgentLoader",
    "AgentRegistry",
    "AgentOrchestrator",
    # Configuration
    "get_settings",
    "Settings",
    "ConfigLoader",
    # Server
    "run_server",
]
