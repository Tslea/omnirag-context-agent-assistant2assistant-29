"""
Agent Plugin System

Dynamic loading and management of agent plugins.
"""

from backend.agents.loader import AgentLoader, AgentRegistry
from backend.agents.orchestrator import AgentOrchestrator
from backend.agents.base_agents import (
    AssistantAgent,
    CodeAgent,
    PlannerAgent,
)
from backend.agents.context_agent import ContextAgent, ContextAgentConfig
from backend.agents.rag_agent import RAGAgent, RAGAgentConfig

__all__ = [
    "AgentLoader",
    "AgentRegistry",
    "AgentOrchestrator",
    "AssistantAgent",
    "CodeAgent",
    "PlannerAgent",
    # New agents
    "ContextAgent",
    "ContextAgentConfig",
    "RAGAgent",
    "RAGAgentConfig",
]
